"""call_bootstrap.py: the descriptive interval printed beside every model effect.

At the provider's default temperature each model call is one draw from the model's distribution of answers,
so every neutral prompt is sent several times (10 times for text prompts, 60 for picture prompts). A model
effect is the mean over the enumerated conditions and their repeated draws. Beside it the analysis reports
the number of calls and a percentile bootstrap interval: the calls are resampled with replacement within each
condition (the conditions stay fixed and only the draws vary), 2,000 times with a fixed seed, and the effect
is recomputed each time with the same weights. The interval describes the spread of the draws; no test,
standard error or power is attached to a model effect. Standard library only.

Imported by analyze.py; not run on its own.
"""
import bisect
import math
import random
import zlib
from collections import defaultdict

# The coordinates that identify ONE grid point of the enumerated design. A repeated draw of the same
# grid point shares all of them and differs only in draw_index and record_id, which are never read here.
GRID_FIELDS = ("stimulus_id", "category", "structure", "tier", "format", "position_order", "paraphrase_id",
               "persona_id", "sim_placement", "placement", "session_id", "seq_index", "arm", "prompting_mode",
               "reasoning_mode", "temperature_requested")


def _hashable(v):
    if isinstance(v, list):
        return tuple(_hashable(x) for x in v)
    if isinstance(v, dict):
        return tuple(sorted((k, _hashable(x)) for k, x in v.items()))
    return v


def grid_key(rec):
    """The grid point a model record belongs to (everything but the draw)."""
    return tuple(_hashable(rec.get(f)) for f in GRID_FIELDS)


def stable_seed(*parts):
    return zlib.crc32(repr(parts).encode("utf-8"))


def combine(items, B):
    """Replicates of a weighted pooled contrast: items is a list of (weight, treatment_arm, control_arm), arms
    as CallBootstrap.arm returns them; the result is [sum_k w_k (T_kb - C_kb) / sum_k w_k for b in 0..B-1].
    An arm that does not vary contributes its mean to every replicate. None when items is empty."""
    if not items:
        return None
    W = float(sum(w for w, _, _ in items))
    out = [0.0] * B
    for w, t, c in items:
        f = w / W
        tr = t[1] if t[1] is not None else [t[0]] * B
        cr = c[1] if c[1] is not None else [c[0]] * B
        out = [o + f * (a - b) for o, a, b in zip(out, tr, cr)]
    return out


def interval(reps, level):
    """The central percentile interval of a list of replicates, conservative about undefined replicates (a
    replicate is None where its statistic is undefined, e.g. a group whose resampled human effects sum to zero
    or less): each undefined replicate counts as minus infinity for the lower end and plus infinity for the
    upper end, so undefined replicates can only widen the interval. (None, None) when reps is None or empty."""
    if not reps:
        return None, None
    vals = sorted(v for v in reps if v is not None)
    k = len(reps) - len(vals)
    a = (1.0 - level) / 2.0
    lo = _pct_inf([-math.inf] * k + vals, a)
    hi = _pct_inf(vals + [math.inf] * k, 1.0 - a)
    return lo, hi


def _pct_inf(sorted_vals, q):
    """percentile() that returns an infinite end when an infinite value brackets the position."""
    n = len(sorted_vals)
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    a, b = sorted_vals[lo], sorted_vals[hi]
    frac = pos - lo
    if frac == 0 or a == b:
        return a
    if math.isinf(a):
        return a
    if math.isinf(b):
        return b
    return a + frac * (b - a)


def percentile(sorted_vals, q):
    """Linear-interpolation percentile of an already sorted list (q in [0, 1])."""
    n = len(sorted_vals)
    if n == 0:
        return None
    pos = q * (n - 1)
    lo = int(math.floor(pos))
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] + frac * (sorted_vals[hi] - sorted_vals[lo])


class CallBootstrap:
    """Percentile bootstrap over one model's calls, resampled within grid points."""

    def __init__(self, recs, model_key, resamples, seed, level, within="grid"):
        """within="grid": model calls, resampled within each grid point (the default). within="cell": human
        choices, resampled within each cell."""
        self.B = int(resamples)
        self.seed = seed
        self.level = level
        self.model_key = model_key
        self.within = within
        self.grid = {} if within == "cell" else {r.get("record_id"): grid_key(r) for r in recs}
        if within != "cell" and len(self.grid) != len(recs):
            # contract B requires unique record ids; a duplicate would silently attach calls to the
            # wrong grid point, so the bootstrap refuses instead.
            raise ValueError(f"model {model_key}: {len(recs) - len(self.grid)} duplicate record_id values; "
                             "the call bootstrap needs one id per call")
        self._arms = {}
        self._sigs = {}
        self._cdfs = {}

    def _cdf(self, n, k):
        """Cumulative Binomial(n, k/n) probabilities for 0..n (computed in logs, exact to rounding)."""
        hit = self._cdfs.get((n, k))
        if hit is not None:
            return hit
        p = k / n
        lp, lq = math.log(p), math.log(1.0 - p)
        acc, out = 0.0, []
        for i in range(n + 1):
            acc += math.exp(math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * lp + (n - i) * lq)
            out.append(acc)
        out[-1] = 1.0
        self._cdfs[(n, k)] = out
        return out

    def arm(self, arm_key, rows):
        """Replicate means of one arm. rows: list of (record_id, y) with y in {0, 1}, the calls that enter
        the statistic. Returns (mean, replicate_means or None when every grid point is constant, n_calls,
        largest number of calls in one grid point)."""
        sig = (len(rows), sum(y for _, y in rows), hash(tuple(rid for rid, _ in rows)))
        hit = self._arms.get(arm_key)
        if hit is not None:
            if self._sigs.get(arm_key) != sig:
                # an arm key names one set of calls; reusing it for different rows (another count, other ids or
                # other outcomes) would attach the wrong replicates to an estimate, so the bootstrap refuses
                #.
                raise ValueError(f"arm {arm_key!r} requested with rows other than the ones it was resampled from")
            return hit
        groups = defaultdict(lambda: [0, 0])
        cell = self.within == "cell"
        if cell and len({rid for rid, _ in rows}) != len(rows):
            # resampling a cell's choices resamples its participants only when each participant makes one choice
            # in the cell (the registered design); a repeat would need a clustered resample, so refuse.
            raise ValueError(f"cell {arm_key!r}: a participant makes more than one choice in the cell")
        for rid, y in rows:
            g = groups["cell"] if cell else groups[self.grid.get(rid, ("record", rid))]
            g[0] += 1
            g[1] += y
        n_tot = len(rows)
        base = 0
        variable = []
        # grid points in a fixed order (by key), so the replicates do not depend on the order of the log
        for _, (n, k) in sorted(groups.items(), key=lambda kv: repr(kv[0])):
            if k == 0 or k == n:
                base += k
            else:
                variable.append(self._cdf(n, k))
        mean = (sum(k for _, k in groups.values()) / n_tot) if n_tot else 0.0
        max_draws = max((n for n, _ in groups.values()), default=0)
        if not variable or n_tot == 0:
            out = (mean, None, n_tot, max_draws)
        else:
            rng = random.Random(stable_seed(self.seed, self.model_key, arm_key))
            rr = rng.random
            bis = bisect.bisect_right
            reps = [(base + sum(bis(c, rr()) for c in variable)) / n_tot for _ in range(self.B)]
            out = (mean, reps, n_tot, max_draws)
        self._arms[arm_key] = out
        self._sigs[arm_key] = sig
        return out

    @staticmethod
    def flipped(arm):
        """The same arm coded against the OTHER option (share 1 - y): the mean and every replicate flip, so a
        control shared by two codings (the two similarity placements target opposite options) is resampled
        once and the two codings stay perfectly (negatively) dependent, as the calls are."""
        mean, reps, n, max_draws = arm
        return (1.0 - mean, ([1.0 - r for r in reps] if reps is not None else None), n, max_draws)

    def interval(self, parts):
        """The percentile interval of a weighted combination of arm means.
        parts: list of (weight, treat_arm, control_arm) where each arm is the tuple arm() returns; the
        point is sum(weight * (treat_mean - control_mean)). Returns (lo, hi); equal to the point when no
        arm varies under resampling."""
        point = sum(w * (t[0] - c[0]) for w, t, c in parts)
        if all(t[1] is None and c[1] is None for _, t, c in parts):
            return point, point
        reps = []
        for b in range(self.B):
            s = 0.0
            for w, t, c in parts:
                tm = t[1][b] if t[1] is not None else t[0]
                cm = c[1][b] if c[1] is not None else c[0]
                s += w * (tm - cm)
            reps.append(s)
        reps.sort()
        a = (1.0 - self.level) / 2.0
        return percentile(reps, a), percentile(reps, 1.0 - a)

    def difference_interval(self, parts_a, parts_b):
        """The percentile interval of (combination a) minus (combination b), resampled jointly (the arms
        two combinations share are drawn once), e.g. a model's format effect minus its numbers effect."""
        pa = sum(w * (t[0] - c[0]) for w, t, c in parts_a)
        pb = sum(w * (t[0] - c[0]) for w, t, c in parts_b)
        allp = list(parts_a) + list(parts_b)
        if all(t[1] is None and c[1] is None for _, t, c in allp):
            return pa - pb, pa - pb
        reps = []
        for b in range(self.B):
            s = 0.0
            for sign, parts in ((1.0, parts_a), (-1.0, parts_b)):
                for w, t, c in parts:
                    tm = t[1][b] if t[1] is not None else t[0]
                    cm = c[1][b] if c[1] is not None else c[0]
                    s += sign * w * (tm - cm)
            reps.append(s)
        reps.sort()
        a = (1.0 - self.level) / 2.0
        return percentile(reps, a), percentile(reps, 1.0 - a)
