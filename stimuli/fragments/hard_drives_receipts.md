# Receipts: External Hard Drives (hard_drives_t1)

Generated: 2026-06-12
Source of truth: V1 web appendix (`v2_revision/web_appendices/web_appendix.md`)
Schema authority: `v2_revision/the Method section and Web Appendix B of the manuscript`

---

## BIN_hard_drives_t1 (Binary baseline)

**Source quote - V1 web appendix, section "BIN-1: External Hard Drives":**

> "Stem: 'Imagine you are shopping for an external hard drive. You are considering the following options:'
>
> Option A | HF | 2TB | $39.99
> Option B | HD | 4TB | $79.99
>
> (Source: Evangelidis, Levav, and Simonson 2023)"

All values confirmed exact. HF = 2TB/$39.99, HD = 4TB/$79.99. These are the published binary anchor values, fixed as tier-1, not subject to calibration adjustment (the tier rules of the design).

**Validation checks (the validator rules (stimuli/validate_stimuli.py)):**
- Two options: HF (lower storage, lower price) and HD (higher storage, higher price). Clean trade-off. PASS.
- is_hd flag set correctly: HF = false, HD = true. PASS.

---

## FRQ_hard_drives_t1 (Frequency decoy - DECOY REBUILT 2026-07-02)

**FLAG: DECOY REBUILT. The V1 decoy tied the target's strong attribute, contradicting the registered
worse-on-both frequency form.**

**V1 source quote - V1 web appendix, section "FRQ-1: External Hard Drives":**

> "Option A | HF (Competitor) | 2TB | $39.99
> Option B | HD (Target) | 4TB | $79.99
> Option C | Decoy | 4TB | $84.99
>
> 'Decoy C is dominated by B (same capacity, higher price) but not by A.'"

The V1 decoy (4TB/$84.99) TIED the target on storage and was worse only on price. That is the
tie-on-strong/worse-on-weak shape the registered design assigns to the RANGE decoy, and it contradicts
the registered frequency form (manuscript: the decoy is "worse than the target on every attribute and
dominated by a clear margin on each one"; the geometry rules (Web Appendix B): "DOMINATED by the target on both attributes
(clearly worse)"). Source check (2026-07-02): the V1 web appendix attributes only the BIN
focal values to Evangelidis, Levav, and Simonson 2023; the FRQ-1 decoy carries no external source and is
V1's own December-2025 construction, so no published-value fidelity conflict blocks the rebuild - the
same class as the range-decoy (M1), phantom, and compromise rebuilds, under the authors' authorized
fixed-value exception. The other 19 FRQ cells already carried the worse-on-both form; this was the only
deviant.

**Rebuilt decoy: 3TB/$84.99** (storage one integer step below the target, price $5.00 above it - the
same shape as the tier-2 hard-drives FRQ decoy, 5TB/$107.99 against 6TB/$99.99; storage is
integer-coarse, so one step is the smallest clear margin available, the coarse-integer bind the SIM
clone rule documents).

**Validation checks (the validator rules (stimuli/validate_stimuli.py) - Dominance, strict worse-on-both):**
- Decoy (3TB/$84.99) vs HD/target (4TB/$79.99): storage strictly worse (3TB < 4TB), price strictly worse
  ($84.99 > $79.99). HD dominates the decoy with a strict margin on BOTH attributes. PASS.
- Decoy (3TB/$84.99) vs HF/competitor (2TB/$39.99): decoy has more storage (3TB > 2TB), HF has lower
  price. Neither dominates. Decoy is NOT dominated by the competitor. PASS.
- Distinct from the RNG range decoy (4TB/$135.98: ties storage, stretches price) and inside the focal
  storage range [2TB, 4TB]. FRQ-vs-RNG distinction holds. PASS.
- Asymmetric dominance geometry confirmed. PASS.

---

## RNG_hard_drives_t1 (Range decoy)

**Source quote - V1 web appendix, section "RNG-1: External Hard Drives":**

> "Option A | HF (Competitor) | 2TB | $39.99
> Option B | HD (Target) | 4TB | $79.99
> Option C | Range Decoy | 5TB | $129.99
>
> 'Decoy C extends the price range, making B appear more moderate.'"

All values confirmed exact. Decoy = 5TB/$129.99.

**Validation checks (the validator rules (stimuli/validate_stimuli.py) - Range):**
- Decoy (5TB/$129.99) strictly extends the target's strong-attribute range beyond HD: storage 5TB > 4TB. PASS.
- No accidental dominance: decoy is NOT dominated by HD (5TB > 4TB; decoy has more storage). PASS.
- Decoy is not dominated by HF (5TB >> 2TB). PASS.
- Price range extended: $39.99, $79.99, $129.99. HD at $79.99 looks moderate. PASS.

---

## PHT_hard_drives_t1 (Phantom decoy)

**Source quote - V1 web appendix, section "PHT-1: External Hard Drives":**

> "Option A | HF (Competitor) | 2TB | $39.99 | Available: Yes
> Option B | HD (Target) | 4TB | $79.99 | Available: Yes
> Option C | Phantom | 4TB | $69.99 | Available: No"

All values confirmed exact. Phantom = 4TB/$69.99, available=false.

**Validation checks (the validator rules (stimuli/validate_stimuli.py) - Phantom):**
- Phantom (4TB/$69.99) vs HD/target (4TB/$79.99): storage equal (4TB = 4TB), phantom price lower ($69.99 < $79.99 - lower price is BETTER). Phantom is superior to HD on EXACTLY ONE attribute (price). PASS (R1 correction: not superior on all attributes).
- Phantom (4TB/$69.99) vs HF/competitor (2TB/$39.99): phantom has more storage (4TB > 2TB, better); phantom has higher price ($69.99 > $39.99, worse). Neither dominates. Phantom does not dominate HF. The phantom is in a trade-off relation with HF, not dominating it. PASS.
- available=false on the phantom option. PASS.
- Geometry: phantom is the "phantom range" (PR) placement per Pettibone and Wedell (2007): equal on storage (target's weak attribute relative to... wait - in this two-attribute set with storage=higher_better and price=lower_better, HD's "strong" attribute is storage (4TB vs 2TB) and "weak" attribute is price ($79.99 vs $39.99, HD is more expensive). Phantom at 4TB/$69.99 is equal to HD on storage (the strong attribute) and better on price (the weak attribute). This is the PF placement in Pettibone and Wedell's terminology (equal on strong, better on weak). This differs from the canonical PR placement (equal on weak, better on strong). Both are one-attribute superiority geometries; both are published in Pettibone & Wedell 2007. The PR placement (better on the target's strong attribute) is the stronger/more canonical effect. Note for calibration.

**Flag:** Phantom is better than HD on the PRICE attribute (the weak/cost attribute), not on storage. This is the PF geometry (better on target's weak attribute). The canonical PR geometry would have the phantom at, e.g., 5TB/$79.99 (better on storage, same price). The V1 published values use the PF geometry ($69.99 < $79.99, same 4TB). Tier-1 values are fixed verbatim; this note is recorded for calibration awareness. Published values retained exactly as in V1.

---

## SOT_hard_drives_t1 (Compromise - REBUILT)

**FLAG: REBUILT SOT. V1 geometry was wrong.**

**V1 source quote - V1 web appendix, section "SOT-1: External Hard Drives":**

> "Option A | HF | 2TB | $39.99
> Option B | Middle | 3TB | $59.99
> Option C | HD | 4TB | $79.99"

V1's geometry added a MIDDLE option (3TB/$59.99) between HF and HD, making HD the highest extreme. This is the standard compromise-effect test where the MIDDLE option is the target and HD is the upper extreme. However, the new plan (the geometry rules (Web Appendix B), SOT rule) requires the OPPOSITE geometry: "the SAME two BIN options PLUS one NEW EXTREME beyond the HD option, so the former HD becomes the middle/compromise." This means HD (4TB/$79.99) must become the middle, and HF (2TB/$39.99) stays as the lower extreme.

**Rebuilt geometry:**
- HF (lower extreme): 2TB/$39.99 (unchanged from BIN)
- HD (middle/target): 4TB/$79.99 (unchanged from BIN, now the compromise)
- New extreme (upper): 6TB/$119.99 (constructed)

**Construction rationale for the new extreme (6TB/$119.99):**
- Storage: 6TB is the next natural step above 4TB (equal 2TB increments: 2, 4, 6).
- Price: $119.99 maintains approximately equal price spacing ($39.99, $79.99, $119.99; gaps of $40).
- The extreme is beyond HD on BOTH attributes: more storage (6 > 4 TB) AND higher price ($119.99 > $79.99). HD is geometrically the middle on both dimensions. PASS.
- The extreme does not dominate HD (it is more expensive). HD does not dominate the extreme (less storage). Neither focal option dominates the extreme. PASS.

**Statistic:** HD/(HD+HF) relative share in the SOT set, compared against the matched BIN. The new extreme's choosers are excluded from the denominator (following the standard relative-share test, Simonson 1989; AE correction; the design notes on the compromise effect).

**Validation checks (the validator rules (stimuli/validate_stimuli.py) - Compromise):**
- Exactly the two BIN options plus one new extreme beyond HD. PASS.
- Former HD is geometrically the middle (between HF and the extreme on both attributes). PASS.
- No free middle added (the new extreme is BEYOND HD, not between HF and HD). PASS.
- Statistic is relative share, not absolute share. PASS.

---

## MOT_hard_drives_t1 (Multiple options per tier)

**Source quote - V1 web appendix, section "MOT-1: External Hard Drives":**

> "Options A-D | Brand A-D | 4TB | $79.99 | High tier
> Options E-H | Brand E-H | 3TB | $59.99 | Middle tier
> Options I-L | Brand I-L | 2TB | $39.99 | Low tier
>
> '(Matched with SOT-1; uses generic brand names)'"

All values confirmed exact. 12 options, 4 per tier.

**Validation checks (the validator rules (stimuli/validate_stimuli.py) - MOT tier identity):**
- 12 options across 3 distinct tiers (High: 4TB/$79.99; Middle: 3TB/$59.99; Low: 2TB/$39.99). PASS.
- Within-tier options are near-equivalent (same attribute values, different generic brand names only). PASS.
- Tiers are distinct on both attributes: High > Middle > Low on storage; High > Middle > Low on price (worse). PASS.

---

## SYM_hard_drives_t1 (Symmetric decoy)

**Source quote - V1 web appendix, section "SYM-1: External Hard Drives":**

> "Option A | HF | 2TB | $39.99
> Option B | HD | 4TB | $79.99
> Option C | Symmetric Decoy | 2TB | $79.99
>
> 'Decoy C is dominated by A (same capacity, higher price) AND by B (same price, less capacity).'"

All values confirmed exact. Decoy = 2TB/$79.99.

**Validation checks (the validator rules (stimuli/validate_stimuli.py) - Symmetric):**
- Decoy (2TB/$79.99) vs HF (2TB/$39.99): same storage, HF has lower price. HF dominates decoy. PASS.
- Decoy (2TB/$79.99) vs HD (4TB/$79.99): same price, HD has more storage. HD dominates decoy. PASS.
- Decoy is dominated by BOTH focal options. PASS.
- Same-page flag required (Evangelidis et al. 2023 shows effect attenuates on separate pages). Noted for survey design.
- Statistic: Delta-pi_HD = HD_share(trinary) - HD_share(binary). PASS.

---

## SIM_hard_drives_t1 (Similarity - NEW, no published analog)

**FLAG: NO_PUBLISHED_ANALOG. SIM is a new structure added in V2; no published hard-drive similarity stimulus exists.**

**Construction from BIN anchor:**
- HF: 2TB/$39.99 (unchanged)
- HD: 4TB/$79.99 (unchanged)
- Clone: 4.5TB/$84.99 (constructed)

**Non-dominance verification (the validator rules (stimuli/validate_stimuli.py)):**
- Clone (4.5TB/$84.99) vs HD (4TB/$79.99): clone has more storage (4.5 > 4 TB, better); clone has higher price ($84.99 > $79.99, worse). HD does NOT dominate clone (HD has less storage). Clone does NOT dominate HD (clone has higher price). PASS - neither dominates the other.
- Clone (4.5TB/$84.99) vs HF (2TB/$39.99): clone has far more storage (4.5 >> 2 TB, better); clone has much higher price ($84.99 >> $39.99, worse). HF does NOT dominate clone. Clone does NOT dominate HF. PASS - trade-off relation.
- Clone is not a pure frequency decoy (it is not dominated by either focal option). PASS.

**Minimal distance:** Clone differs from HD by +0.5TB storage and +$5.00 price. This is the smallest non-dominated distance available in a two-attribute space with these attribute scales and the need to keep the clone recognizably close to HD.

**Why not 4TB/$84.99 (same storage, higher price)?** A clone with 4TB/$84.99 would be strictly dominated by HD (4TB/$79.99 - same storage, lower price, lower is better). The validator rule (the validator rules (stimuli/validate_stimuli.py)) prohibits a clone that silently becomes a decoy (Berkowitsch's rounding accident). Storage must differ by at least a detectable amount to avoid HD-domination.

**Statistic:** Relative share of competitor (HF) in SIM vs matched BIN. The similarity effect predicts the clone steals disproportionately from HD (the option it resembles), so HF gains relative share. Equivalently: HF/(HD+HF) rises from BIN to SIM.

**No published analog note:** This value set has no counterpart in Evangelidis et al. 2023 or any published context-effects paper for external hard drives. The clone values (4.5TB/$84.99) were constructed minimally from the BIN anchor following the geometry rules (Web Appendix B) SIM geometry rules. They are flagged for calibration review at the final calibration lock.

---

## Flags Summary

| Structure | Flag | Detail |
|---|---|---|
| SOT | rebuilt_sot = true | V1 SOT-1 used "add a middle" geometry (wrong); rebuilt to "add an extreme beyond HD" so HD becomes the compromise. New extreme: 6TB/$119.99. |
| SIM | no_published_analog = true | SIM is a new V2 structure; no published hard-drive similarity stimulus. Clone (4.5TB/$84.99) constructed minimally from BIN anchor; non-dominance verified. |
| PHT | geometry_note | Published PHT-1 uses PF geometry (phantom better on price/weak attribute, equal on storage/strong attribute). Canonical PR geometry would differ. fixed verbatim as tier-1. |
| FRQ | decoy_rebuilt (2026-07-02) | V1's decoy (4TB/$84.99) tied the target's storage - the range shape, not the registered worse-on-both frequency form. Rebuilt to 3TB/$84.99 (strictly worse on both attributes). V1 value preserved above; V1's own construction, no external source (F1 fix). |

---

## Self-check against the validator rules (stimuli/validate_stimuli.py)

| Check | Structure | Result |
|---|---|---|
| 1. Dominance (FRQ) | FRQ | PASS (after 2026-07-02 decoy rebuild): decoy strictly worse than the target on both attributes, not dominated by the competitor |
| 2. Range (RNG) | RNG | PASS: decoy extends target's storage range; no accidental dominance |
| 3. Phantom one-attribute (PHT) | PHT | PASS: phantom superior on EXACTLY ONE attribute (price); available=false |
| 4. Compromise SOT geometry | SOT | PASS (after rebuild): extreme beyond HD; HD is middle; no free middle |
| 5. Symmetric (SYM) | SYM | PASS: decoy dominated by BOTH focal options |
| 6. MOT tier identity | MOT | PASS: 3 distinct tiers, 4 near-equivalent options each |
| 7. SIM non-dominance | SIM | PASS: clone (4.5TB/$84.99) not dominated by HD or HF; not a pure decoy |
| 8. Cross-category geometry | all | PASS: same relational rules applied as other categories |
| 9. No duplicates | all | PASS: no two options within a set are identical |
| 10. Tier-1 fidelity | BIN, RNG, PHT, MOT, SYM | PASS: focal values match V1 web appendix exactly (RNG decoy engine-rebuilt to the registered dominated form, 2026-07-01 M1; V1 value preserved above) |
| 10. Tier-1 fidelity | FRQ | FLAG: decoy rebuilt 2026-07-02 (V1's tie-on-storage decoy contradicted the registered worse-on-both form); focal pair unchanged, V1 value preserved above |
| 10. Tier-1 fidelity | SOT | FLAG: SOT rebuilt (V1 geometry wrong per new plan); values for extreme constructed, not published |
| 10. Tier-1 fidelity | SIM | FLAG: no published analog; values constructed |
| 11. Single-source integrity | all | PASS: all values sourced from V1 web appendix or flagged as constructed |
