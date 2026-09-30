# Televisions stimulus receipts - tier-1 source audit

Category: Televisions (id: televisions; V1 category number 5)
Published source: Sharif, Webb, and Bhatia (2025), JCR, doi:10.1093/jcr/ucaf061
Date written: 2026-06-12


---

## BIN_televisions_t1

**Exact source:** V1 web appendix, section "BIN-5: Televisions", lines 313-325.

Verbatim from web appendix:

> **BIN-5: Televisions** (Source: Sharif, Webb, and Bhatia forthcoming)
>
> Stem: "Imagine you are shopping for a 40-inch television. Picture quality is rated on a 100-point scale by a panel of experts at Consumer Reports (1 = worst, 100 = best). You are considering the following options:"
>
> | Option | Role | Price | Picture Quality |
> |--------|------|-------|-----------------|
> | A | HF | $109.99 | 65 |
> | B | HD | $505.99 | 98 |

Values locked at tier 1. HF = picture_quality 65, price $109.99. HD = picture_quality 98, price $505.99. No change.

Note: V1 web appendix cites as "forthcoming"; paper is now published (doi:10.1093/jcr/ucaf061). Citation must be updated in the manuscript (a known error of the first submission).

---

## FRQ_televisions_t1

**Exact source:** V1 web appendix, section "FRQ-5: Televisions", lines 889-899.

Verbatim from web appendix:

> **FRQ-5: Televisions** (Matched with BIN-5; Target: HD option)
>
> | Option | Role | Price | Picture Quality |
> |--------|------|-------|-----------------|
> | A | HF (Competitor) | $109.99 | 65 |
> | B | HD (Target) | $505.99 | 98 |
> | C | Decoy | $529.99 | 96 |

Decoy C is dominated by HD (B): quality 96 < 98 AND price $529.99 > $505.99. HD strictly dominates decoy on both attributes. Decoy is not dominated by HF (quality 96 >> 65). Geometry correct.

Values: HF and HD unchanged from BIN. Decoy: picture_quality 96, price $529.99. Transcribed verbatim from V1.

---

## RNG_televisions_t1

**Exact source:** V1 web appendix, section "RNG-5: Televisions", lines 1017-1027.

Verbatim from web appendix:

> **RNG-5: Televisions** (Matched with BIN-5; Target: HD option)
>
> | Option | Role | Price | Picture Quality |
> |--------|------|-------|-----------------|
> | A | HF (Competitor) | $109.99 | 65 |
> | B | HD (Target) | $505.99 | 98 |
> | C | Range Decoy | $899.99 | 99 |

**Geometry analysis:** Picture quality caps at 100. The range decoy at quality 99 extends the quality range by only 1 point above HD's 98. The primary range extension is via price: $899.99 >> $505.99 (a $394 extension). This matches the hotels-case precedent documented in V1 web appendix (RNG-3 note: "Because hotel star ratings cannot exceed 5-star, we extend the price range rather than quality range for this category"). The ceiling constraint means quality cannot be extended by more than 2 points; price carries the range signal.

Decoy is NOT dominated: it has better quality (99 > 98) than HD, so HD does not dominate it. HF also does not dominate (decoy quality 99 >> 65).

Values: Decoy picture_quality 99, price $899.99. Transcribed verbatim from V1.

---

## PHT_televisions_t1

**Source:** REBUILT for V2. V1 phantom was geometrically incorrect.

**V1 PHT-5 verbatim (lines 1147-1157):**

> **PHT-5: Televisions** (Matched with BIN-5; Target: HD option)
>
> | Option | Role | Price | Picture Quality | Available |
> |--------|------|-------|-----------------|-----------|
> | A | HF (Competitor) | $109.99 | 65 | Yes |
> | B | HD (Target) | $505.99 | 98 | Yes |
> | C | Phantom | $479.99 | 99 | No |

**Why V1 is wrong:** V1 phantom ($479.99/99) is superior to HD on BOTH attributes: cheaper ($479.99 < $505.99) AND better quality (99 > 98). This violates the standard phantom geometry.

**Evidence for the error:** the validator rules (stimuli/validate_stimuli.py) states: "Phantom (PHT): the phantom is superior on EXACTLY ONE attribute and is marked unavailable; never superior on all (R1)." the design notes on the phantom effect documents R1's catch verbatim: "the phantom is typically superior on only one dimension, not all attributes as described in H4 of the report." Pettibone and Wedell (2007) identify PRF/PERF placements (superior on both attributes) as the weakest, least reliable phantom geometry.

**Rebuilt V2 phantom:** picture_quality 99, price $505.99. Same price as HD ($505.99 = $505.99, equal). Better quality (99 > 98, superior on one attribute). This is the PR placement (Pettibone and Wedell 2007: better on target's strong attribute, equal on the weak attribute). Strongest reliable phantom geometry per the literature.

**Reconstruction rationale:** Only one attribute is changed from V1 (price adjusted from $479.99 to $505.99 to remove the two-attribute superiority). Quality kept at 99. Phantom is still clearly unavailable. Target is HD.

---

## SOT_televisions_t1

**Source:** REBUILT for V2. V1 SOT-5 used the wrong geometry.

**V1 SOT-5 verbatim (lines 453-463):**

> **SOT-5: Televisions** (Matched with BIN-5; follows Sharif et al. Study 2)
>
> | Option | Role | Price | Picture Quality |
> |--------|------|-------|-----------------|
> | A | HF | $109.99 | 65 |
> | B | Middle | $325.99 | 83 |
> | C | HD | $505.99 | 98 |

**Why V1 is wrong for V2:** V1 adds a middle option BETWEEN HF and HD. the geometry rules (Web Appendix B) defines SOT as: "the two BIN options + ONE NEW EXTREME beyond the HD option, so the former HD becomes the middle/compromise. NEVER 'add a free middle.'" The V1 geometry tests a different effect (compromise via middle vs the corrected compromise via the HD-becomes-middle mechanism).

**V2 geometry:** BIN options unchanged (HF $109.99/65, HD $505.99/98). New EXTREME added beyond HD: picture_quality 100, price $799.99. HD ($505.99/98) is now the middle on both dimensions: quality 98 is between 65 and 100; price $505.99 is between $109.99 and $799.99.

**Extreme values rationale:** Quality 100 is the maximum on the 0-100 Consumer Reports scale (makes the extreme maximally extreme on quality). Price $799.99 is approximately 58% above HD's price ($505.99), a clear price extreme. Both values are plausible for a premium 40-inch television.

**Note on V1 middle-tier values ($325.99/83):** These appear in MOT-5 as the middle tier and are stated to follow Sharif et al. Study 2. They are valid tier-1 values for MOT. They are NOT used in V2's SOT because SOT now uses the extreme-beyond-HD geometry.

---

## MOT_televisions_t1

**Exact source:** V1 web appendix, section "MOT-5: Televisions", lines 653-681.

V1 explicitly states: "brand names follow Sharif et al. Study 2 MOT condition exactly."

Verbatim from web appendix:

> **MOT-5: Televisions** (Matched with SOT-5; brand names follow Sharif et al. Study 2 MOT condition exactly)
>
> | Option | Brand | Price | Picture Quality | Tier |
> |--------|-------|-------|-----------------|------|
> | A | Zenith | $505.99 | 98 | High |
> | B | Vizio | $505.99 | 98 | High |
> | C | Hisense | $505.99 | 98 | High |
> | D | TCL | $505.99 | 98 | High |
> | E | Insignia | $325.99 | 83 | Middle |
> | F | Element | $325.99 | 83 | Middle |
> | G | Westinghouse | $325.99 | 83 | Middle |
> | H | Sceptre | $325.99 | 83 | Middle |
> | I | Onn | $109.99 | 65 | Low |
> | J | Sanyo | $109.99 | 65 | Low |
> | K | RCA | $109.99 | 65 | Low |
> | L | Sharp | $109.99 | 65 | Low |

All 12 brand names and attribute values transcribed verbatim from V1 MOT-5.

**High tier brands:** Zenith, Vizio, Hisense, TCL - all picture_quality 98, price $505.99. These map to the HD binary anchor.

**Middle tier brands:** Insignia, Element, Westinghouse, Sceptre - all picture_quality 83, price $325.99.

**Low tier brands:** Onn, Sanyo, RCA, Sharp - all picture_quality 65, price $109.99. These map to the HF binary anchor.

**Key note (from the design notes on the extremity effect and web appendix lines 526-529):** The V1 web appendix design section states: "Two exceptions preserve validated stimuli from Sharif et al.: MOT-5 (Televisions) uses original TV brand names from Sharif et al. Study 2." Brand names are exactly as published in the source paper. This is the most critical stimulus to get right because (1) the extremity effect is Sharif et al.'s own finding on this exact category, and (2) the TV brands are the published-paper-specific values that define tier-1 fidelity for MOT.

---

## SYM_televisions_t1

**Exact source:** V1 web appendix, section "SYM-5: Televisions", lines 1275-1285.

Verbatim from web appendix:

> **SYM-5: Televisions** (Matched with BIN-5)
>
> | Option | Role | Price | Picture Quality |
> |--------|------|-------|-----------------|
> | A | HF | $109.99 | 65 |
> | B | HD | $505.99 | 98 |
> | C | Symmetric Decoy | $505.99 | 65 |

Decoy C: picture_quality 65 (same as HF), price $505.99 (same as HD). Dominated by HF (same quality at $505.99 vs $109.99, so HF is cheaper for equal quality). Dominated by HD (same price at quality 65 vs 98, so HD is better quality for equal price). Decoy is dominated by BOTH focal options. Geometry confirmed correct.

Values transcribed verbatim from V1.

---

## SIM_televisions_t1

**Source:** CONSTRUCTED - no published analog.

SIM (similarity) is a new structure in V2, not present in V1. There is no published Sharif et al. or Evangelidis et al. television similarity stimulus.

**Clone construction rationale:**
- Clone target: HD ($505.99/98), which is is_hd = true.
- Clone values: picture_quality 97, price $499.99.
- Clone is_hd: true (same tier as the focal option it resembles).
- Distance: quality 97 vs 98 = 1 point (1.0% of 0-100 scale); price $499.99 vs $505.99 = $6.00 (1.2% of $505.99).
- Non-domination check: HD (98, $505.99) vs clone (97, $499.99): HD is better on quality (98 > 97) but worse on price ($505.99 > $499.99). Neither dominates. Berkowitsch guard satisfied (clone is not silently a decoy).
- Clone does not resemble HF: quality distance 97 - 65 = 32 points, price distance $499.99 - $109.99 = $390. Clone is unambiguously in the HD neighborhood.

**Flag:** no_published_analog = true. Values subject to calibration pre-test (clone must read as similar to but not identical to HD, and must not be perceived as dominated by HD).

---

## SELF-CHECK against the validator rules (stimuli/validate_stimuli.py)

| Check | Structure | Status | Notes |
|---|---|---|---|
| 1. Dominance (FRQ): decoy dominated by target on both; not by competitor | FRQ | PASS | HD(98/$505.99) beats decoy(96/$529.99) on both. HF doesn't dominate (quality 65 < 96). |
| 2. Range (RNG): decoy extends target's strong-attribute range; no accidental dominance | RNG | PASS | Quality range extended (99 > 98). Price range extended ($899.99 >> $505.99). Decoy not dominated (quality 99 > HD 98). |
| 3. Phantom (PHT): superior on EXACTLY ONE attribute; unavailable; never all | PHT | PASS (rebuilt) | V1 was wrong (superior on both). Rebuilt: quality 99 > 98 (superior), price $505.99 = $505.99 (equal). One attribute only. |
| 4. Compromise (SOT): exactly BIN options + one new extreme BEYOND HD; HD is now middle; no free middle | SOT | PASS (rebuilt) | V1 added a middle (wrong). Rebuilt: EXTREME at $799.99/100. HD($505.99/98) is middle on both dimensions. |
| 5. Symmetric (SYM): decoy worse than BOTH focal options; same-page | SYM | PASS | Decoy $505.99/65 dominated by both HF and HD. |
| 6. MOT tier identity: 12 options, 3 distinct tiers; within-tier near-equivalent | MOT | PASS | 4 brands per tier, identical attributes within tier, all different brands. |
| 7. Similarity (SIM): clone near-duplicate of one focal option; non-domination assertion | SIM | PASS | Clone of HD: distance 1pt quality, $6 price. Neither dominates. |
| 8. Cross-category geometry consistency | All | PASS | Same relational rules applied as other categories. |
| 9. No duplicates within a set | All | PASS | Each set verified unique. |
| 10. Tier-1 fidelity | BIN, FRQ, RNG, SYM, MOT | PASS | All values transcribed verbatim from V1 web appendix. |
| 11. Single-source integrity | All | DEFERRED | Stimuli.json is the source; web appendix generation from it is a build-step, not a check on this file alone. |

**Checks not fully satisfiable from this file alone:**
- Check 8 (cross-category consistency): cannot verify against other category files that do not yet exist. Flagged for the validator once all fragments are built.
- Check 11 (single-source integrity): requires the build pipeline to generate the web appendix from stimuli.json. Cannot be self-checked here.

**Unresolved flag on SOT extreme values:** The SOT EXTREME option ($799.99/100) is constructed, not published. Calibration pre-test must confirm HD reads as the middle/compromise tier, not as the premium option. The calibration_locked flag is set to false for this stimulus.
