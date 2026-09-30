"""statlib.py: the statistics the registered analysis uses, in plain Python (standard library only).

Normal distribution functions; the difference of two proportions with a cluster-robust standard error
(participant = cluster) and its pooling across categories; confidence intervals; Holm's correction; the
Bayes factor with a half-normal prior that the human replication criterion uses; two one-sided tests for
equivalence; and weighted and ordinary least-squares slopes. Each function states what it computes and
its limits.
By design the model effects are population quantities over the enumerated conditions and carry no
standard error or test, so none of these functions is applied to a model effect.

Imported by analyze.py; not run on its own.
"""
import math

# --- the normal distribution, by hand (no scipy) ---------------------------------------------------
def norm_cdf(z):
    """Standard normal CDF via the error function (math.erf is stdlib)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def norm_sf(z):
    """Upper tail of the standard normal."""
    return 1.0 - norm_cdf(z)

def two_sided_p_from_z(z):
    """Two-sided p-value for a z statistic."""
    return 2.0 * norm_sf(abs(z))


# --- cluster-robust standard error for a difference in two proportions -----------------------------
def cluster_robust_diff_props(treat_rows, control_rows):
    """Estimate a difference in two proportions (target share in a treatment cell minus the share in
    its matched binary control) with a CLUSTER-ROBUST standard error, treating each participant as a
    cluster, using pure Python.

    Inputs are two lists of (participant_id, y) pairs where y is 0/1 (chose_target). The point
    estimate is the simple difference in means p_treat - p_control. The standard error follows the
    sandwich form for a difference of two independent group means where, WITHIN each group, a
    participant's observations are allowed to be correlated: the variance of a group mean is the
    cluster-robust variance of the mean,
        Var(p) = ( sum_c ( sum_{i in c} (y_i - p) ) ^ 2 ) / ( N ^ 2 ),
    which reduces to the usual binomial variance when every participant contributes one observation
    (the backbone design's first-trial-like case) and inflates it when a participant contributes
    several correlated choices (the within-person case). The two group variances add because the
    treatment and control cells contain different participants under the no-repeat-structure design.

    HONEST LIMIT (documented proxy at the rehearsal stage): the real confirmatory analysis fits a
    cluster-robust generalized linear model on the long table with participant as the clustering
    unit, which also pools across categories and carries the design's covariates. This closed-form
    sandwich is the same estimator for the simple two-cell contrast and is exact when each
    participant appears in one cell; it is the rehearsal's stand-in for the full model and is
    deliberately conservative. Returns (delta, se, n_treat_clusters, n_ctrl_clusters)."""
    def group(rows):
        by_c = {}
        n = 0
        s = 0
        for pid, y in rows:
            by_c.setdefault(pid, []).append(y)
            n += 1
            s += y
        p = s / n if n else 0.0
        # cluster-robust variance of the mean
        ss = 0.0
        for pid, ys in by_c.items():
            resid_sum = sum((y - p) for y in ys)
            ss += resid_sum * resid_sum
        var = ss / (n * n) if n else 0.0
        return p, var, len(by_c)
    pt, vt, ct = group(treat_rows)
    pc, vc, cc = group(control_rows)
    delta = pt - pc
    se = math.sqrt(vt + vc)
    return delta, se, ct, cc


def ci95(delta, se):
    """A 95 percent confidence interval from a point estimate and a standard error."""
    return (delta - 1.959964 * se, delta + 1.959964 * se)


# --- the Holm step-down correction -----------------------------------------------------------------
def holm(pvalues_by_key, alpha=0.05):
    """The Holm step-down multiple-comparison correction (Holm 1979), valid under arbitrary
    dependence, which is why the protocol uses it for the six effects that share one binary control.

    Input: a dict {key: raw_p}. Output: a dict {key: (raw_p, holm_adjusted_p, reject_at_alpha)}.
    The adjusted p for the i-th smallest raw p (1-indexed) is max over the first i of
    (m - j + 1) * p_(j), capped at 1 and made monotone non-decreasing; reject while the running
    adjusted p stays at or below alpha. This is the standard step-down form."""
    items = sorted(pvalues_by_key.items(), key=lambda kv: kv[1])
    m = len(items)
    out = {}
    running_max = 0.0
    still_rejecting = True
    for i, (key, p) in enumerate(items):  # i = 0..m-1
        adj = (m - i) * p
        adj = min(1.0, adj)
        adj = max(adj, running_max)        # enforce monotonicity
        running_max = adj
        if adj > alpha:
            still_rejecting = False
        reject = still_rejecting
        out[key] = (p, adj, reject)
    return out


# --- the stratified (matched-control) contrast with a cluster-robust standard error ----------------
def stratified_diff(strata):
    """The pooled registered contrast: within each stratum (one product category x memorization tier x
    format, and for similarity also the clone placement) the treatment cell is compared with ITS OWN
    matched control cell, and the stratum differences are averaged with weights proportional to the
    treatment count, so every contrast is against its matched control even when cell sizes differ
    (after exclusions, dropout, or a descriptive-only cell). With balanced cells this equals the old
    concatenated difference exactly.

    strata: list of (treat_rows, ctrl_rows), each a list of (participant_id, y) with y in {0, 1}.
    Strata with an empty arm are skipped (no matched contrast exists).

    Standard error: the cluster-robust (sandwich) variance with the participant as the cluster. Each
    observation's influence on the weighted estimate is w_k (y - mean_k) / n_k (plus for treatment,
    minus for control); influences are summed within participant, squared, and summed. This allows one
    person's several choices to be correlated, including a person who appears in a treatment cell of
    one category and a control cell of another, and a control row reused by two placements.
    Returns (delta, se, n_treat, n_ctrl, n_clusters)."""
    kept = [(t, c) for t, c in strata if t and c]
    if not kept:
        return 0.0, 0.0, 0, 0, 0
    n_t_total = sum(len(t) for t, _ in kept)
    delta = 0.0
    infl = {}
    n_ctrl = 0
    for t, c in kept:
        w = len(t) / n_t_total
        mt = sum(y for _, y in t) / len(t)
        mc = sum(y for _, y in c) / len(c)
        delta += w * (mt - mc)
        for pid, y in t:
            infl[pid] = infl.get(pid, 0.0) + w * (y - mt) / len(t)
        for pid, y in c:
            infl[pid] = infl.get(pid, 0.0) - w * (y - mc) / len(c)
        n_ctrl += len(c)
    var = sum(v * v for v in infl.values())
    return delta, math.sqrt(var), n_t_total, n_ctrl, len(infl)


def weighted_linear_contrast(terms):
    """A weighted sum of cell means with a cluster-robust (participant) standard error.

    terms: list of (coef, rows), rows a list of (cluster_id, y). The estimate is sum(coef * mean(rows)).
    Each observation's influence is coef * (y - mean) / n; influences are summed within cluster, squared,
    and summed, exactly as in stratified_diff (which is the special case of +w on a treatment cell and
    -w on its control). Terms with no rows are skipped. Returns (estimate, se, n_clusters)."""
    est = 0.0
    infl = {}
    for coef, rows in terms:
        if not rows or coef == 0:
            continue
        n = len(rows)
        m = sum(y for _, y in rows) / n
        est += coef * m
        for pid, y in rows:
            infl[pid] = infl.get(pid, 0.0) + coef * (y - m) / n
    var = sum(v * v for v in infl.values())
    return est, math.sqrt(var), len(infl)


def ci(delta, se, level=0.95):
    """A two-sided confidence interval at the stated level from an estimate and its standard error."""
    z = norm_ppf(0.5 + level / 2.0)
    return (delta - z * se, delta + z * se)


def norm_ppf(q):
    """Standard normal quantile by bisection on norm_cdf (accurate to about 1e-12, no scipy)."""
    lo, hi = -40.0, 40.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if norm_cdf(mid) < q:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# --- the registered Bayes factor: directional, half-normal prior, normal likelihood ----------------
def bf10_halfnormal(delta, se, prior_scale):
    """The Bayes factor for an effect in the registered (positive) direction against no effect.

    Model, stated plainly. The data are the pooled estimate `delta` and its cluster-robust standard
    error `se`, treated as a normal likelihood: delta ~ Normal(true effect, se^2). Under the null the
    true effect is exactly zero. Under the alternative the true effect is positive and follows a
    half-normal prior with scale `prior_scale` (the same units as delta), so effects near the scale are
    expected and effects far above twice the scale are unlikely. This is the half-normal Bayes factor
    of Dienes (2014, Frontiers in Psychology 5:781; Dienes and Mclatchie 2018), whose scale is set to
    the effect size the prior literature leads one to expect.

    Closed form. With a full Normal(0, s0^2) prior the marginal density of delta is
    Normal(delta; 0, se^2 + s0^2), and the posterior is Normal(m, v) with v = 1/(1/se^2 + 1/s0^2) and
    m = v * delta / se^2. Restricting the prior to the positive half doubles its density and keeps
    only the positive part of the posterior, so
        BF10 = 2 * Phi(m / sqrt(v)) * Normal(delta; 0, se^2 + s0^2) / Normal(delta; 0, se^2).
    A reversed estimate therefore gives BF10 below 1 (evidence for no effect over a positive one).
    Returns a float, capped at 1e12 so numbers.json stays finite (the criterion only asks for > 3)."""
    CAP = 1e12
    if prior_scale <= 0:
        raise ValueError("prior_scale must be positive")
    if se <= 0:
        return CAP if delta > 0 else 0.0
    s2, p2 = se * se, prior_scale * prior_scale
    v = 1.0 / (1.0 / s2 + 1.0 / p2)
    m = v * delta / s2
    # log of the density ratio, computed in logs so large z does not overflow.
    log_ratio = (-0.5 * math.log(s2 + p2) - 0.5 * delta * delta / (s2 + p2)) - \
                (-0.5 * math.log(s2) - 0.5 * delta * delta / s2)
    tail = norm_cdf(m / math.sqrt(v))
    if tail <= 0.0:
        return 0.0
    log_bf = math.log(2.0) + math.log(tail) + log_ratio
    if log_bf > math.log(CAP):
        return CAP
    return math.exp(log_bf)


# --- equivalence by two one-sided tests ------------------------------------------------------------
def tost_equivalence(delta, se, bound, alpha=0.05):
    """Two one-sided tests (Schuirmann 1987; Lakens 2017) that the true effect lies inside
    (-bound, +bound). Equivalent to asking whether the (1 - 2*alpha) confidence interval lies entirely
    inside the bounds, so at alpha = .05 the rule is: the 90 percent interval must sit strictly inside
    minus bound to plus bound. A point estimate inside the band with an interval that crosses a bound
    is NOT equivalent. Returns (lo, hi, equivalent, p_tost) where p_tost is the larger of the two
    one-sided p-values."""
    if se <= 0:
        return delta, delta, abs(delta) < bound, (0.0 if abs(delta) < bound else 1.0)
    z = norm_ppf(1.0 - alpha)
    lo, hi = delta - z * se, delta + z * se
    p_lower = norm_sf((delta + bound) / se)      # H0: effect <= -bound
    p_upper = norm_cdf((delta - bound) / se)     # H0: effect >= +bound
    equivalent = (lo > -bound) and (hi < bound)
    return lo, hi, equivalent, max(p_lower, p_upper)


# --- weighted least squares (small p, normal equations by Gauss-Jordan) ----------------------------
def wls(X, y, w):
    """Weighted least squares for a handful of predictors. X is a list of rows (each a list with the
    intercept column included), y the outcomes, w the non-negative weights. Returns the coefficient
    list, or None when the design is singular (too few distinct points)."""
    p = len(X[0])
    A = [[0.0] * p for _ in range(p)]
    b = [0.0] * p
    for xi, yi, wi in zip(X, y, w):
        for r in range(p):
            b[r] += wi * xi[r] * yi
            for c in range(p):
                A[r][c] += wi * xi[r] * xi[c]
    # Gauss-Jordan with partial pivoting.
    M = [A[r][:] + [b[r]] for r in range(p)]
    for col in range(p):
        piv = max(range(col, p), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            return None
        M[col], M[piv] = M[piv], M[col]
        f = M[col][col]
        M[col] = [v / f for v in M[col]]
        for r in range(p):
            if r != col:
                g = M[r][col]
                M[r] = [a - g * bcol for a, bcol in zip(M[r], M[col])]
    return [M[r][p] for r in range(p)]


# --- ordinary least squares slope through the origin-free line (calibration slope) -----------------
def ols_slope(xs, ys):
    """The calibration slope: regress the model effects (ys) on the human effects (xs) with an
    intercept, return the slope. A slope near 1 means the model expresses human effects at the right
    magnitude; below 1 means it under-expresses, above 1 means it over-expresses. Pure Python OLS."""
    n = len(xs)
    if n < 2:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    if sxx == 0:
        return float("nan")
    return sxy / sxx
