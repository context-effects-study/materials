# Receipts: Restaurants (category id: restaurants; V1 category number 6)

**Published source:** Sharif, Webb, and Bhatia 2025, *Journal of Consumer Research*, doi:10.1093/jcr/ucaf061.

**Note on citation:** V1 web appendix and the review of the first submission flag that "Sharif, Webb, and Bhatia" is cited as "forthcoming" in V1 but is now published with a DOI. All receipts below use the published citation.

---

## BIN - Binary Baseline

**Source:** V1 web appendix, BIN-6 (p. 9 of web_appendix.md, lines 327–339).

| Option | Role | Rating | Price |
|--------|------|--------|-------|
| A | HF | 65 | $7 |
| B | HD | 98 | $40 |

**Stem (verbatim from V1 web appendix BIN-6):**
> "Imagine you are choosing a restaurant for dinner. Overall rating is assigned by Consumer Reports based on food quality, ambiance, and service (0-100 scale, higher = better). Price reflects the average entrée cost. You are considering the following options:"

**Quote from source:**
> BIN-6: Restaurants (Source: Sharif, Webb, and Bhatia forthcoming)
> Option A | HF | $7 | 65
> Option B | HD | $40 | 98

**is_hd flags:** HF = false, HD = true.

---

## FRQ - Frequency Decoy

**Source:** V1 web appendix, FRQ-6 (lines 901–911).

| Option | Role | Rating | Price |
|--------|------|--------|-------|
| A | HF (Competitor) | 65 | $7 |
| B | HD (Target) | 98 | $40 |
| C | Decoy | 96 | $43 |

**Quote from source:**
> FRQ-6: Restaurants (Matched with BIN-6; Target: HD option)
> Option A | HF (Competitor) | $7 | 65
> Option B | HD (Target) | $40 | 98
> Option C | Decoy | $43 | 96

**Geometry check:** Decoy (96/$43) dominated by HD (98/$40): rating 98 > 96 (HD better on quality) AND price $40 < $43 (HD cheaper). Decoy NOT dominated by HF: HF has rating 65 < 96, so HF cannot dominate on quality. Asymmetric dominance confirmed.

---

## RNG - Range Decoy

**Source:** V1 web appendix, RNG-6 (lines 1029–1039).

| Option | Role | Rating | Price |
|--------|------|--------|-------|
| A | HF (Competitor) | 65 | $7 |
| B | HD (Target) | 98 | $40 |
| C | Range Decoy | 99 | $75 |

**Quote from source:**
> RNG-6: Restaurants (Matched with BIN-6; Target: HD option)
> Option A | HF (Competitor) | $7 | 65
> Option B | HD (Target) | $40 | 98
> Option C | Range Decoy | $75 | 99

**Geometry check:** Decoy (99/$75) extends price range well beyond HD ($75 vs $40), making HD appear moderate. Decoy rating 99 is marginally above HD rating 98, so decoy is NOT dominated by HD on quality (99 > 98). No accidental dominance. Range geometry satisfied.

---

## PHT - Phantom Decoy (REBUILT per R1 correction)

**Published values (V1 web appendix, PHT-6, lines 1159–1169):**

| Option | Role | Rating | Price | Available |
|--------|------|--------|-------|-----------|
| A | HF (Competitor) | 65 | $7 | Yes |
| B | HD (Target) | 98 | $40 | Yes |
| C | Phantom (PUBLISHED) | 99 | $35 | No |

**Quote from published source:**
> PHT-6: Restaurants (Matched with BIN-6; Target: HD option)
> Option A | HF (Competitor) | $7 | 65 | Yes
> Option B | HD (Target) | $40 | 98 | Yes
> Option C | Phantom | $35 | 99 | No

**R1 Violation Analysis:**
Published phantom ($35/99) vs. HD target ($40/98):
- Rating: 99 > 98 - phantom SUPERIOR on quality
- Price: $35 < $40 - phantom SUPERIOR on price

The published phantom is superior on BOTH attributes. This violates R1's requirement that the phantom be superior on EXACTLY ONE attribute. Per the geometry rules (Web Appendix B) UNIFIED RULE, this is a "PHT_rebuilt_R1" case.

**Rebuild decision:** Make phantom superior on EXACTLY the target's strong (quality/rating) attribute and equal on price.
- Rebuilt phantom: rating = 99 (superior on quality, same as published), price = $40 (equal to HD, changed from $35).

**Rebuilt stimulus used in JSON:**

| Option | Role | Rating | Price | Available |
|--------|------|--------|-------|-----------|
| A | HF (Competitor) | 65 | $7 | Yes |
| B | HD (Target) | 98 | $40 | Yes |
| C | Phantom (REBUILT) | 99 | $40 | No |

**Flag:** `PHT_rebuilt_R1`

**Geometry check (rebuilt):** Phantom (99/$40) vs. HD (98/$40): rating 99 > 98 (superior on quality); price $40 = $40 (equal). Superior on EXACTLY ONE attribute. R1 requirement satisfied.

---

## SOT - Compromise (REBUILT per new geometry)

**Published V1 values (V1 web appendix, SOT-6, lines 465–475):**

| Option | Role | Rating | Price |
|--------|------|--------|-------|
| A | HF | 65 | $7 |
| B | Middle | 82 | $25 |
| C | HD | 98 | $40 |

**V1 geometry problem:** V1 SOT-6 added a MIDDLE option ($25/82) between HF and HD, keeping HD as the top extreme. This is the old "add a free middle" geometry. The new plan (the geometry rules (Web Appendix B)) requires the two BIN options PLUS one NEW EXTREME beyond HD so that former HD becomes the middle.

**Rebuild decision:**
- Keep BIN options: HF (65/$7), HD (98/$40)
- Add new EXTREME beyond HD on both attributes. Rating caps at 100, so extend via price. EXTREME = rating 100 / $65.
- Former HD (98/$40) is now geometrically middle between HF (65/$7) and EXTREME (100/$65).

**Rebuilt stimulus used in JSON:**

| Option | Role | Rating | Price |
|--------|------|--------|-------|
| A | HF | 65 | $7 |
| B | HD (now middle) | 98 | $40 |
| C | EXTREME | 100 | $65 |

**Middle verified:** HD (98/$40) strictly between HF (65/$7) and EXTREME (100/$65) on both attributes: 65 < 98 < 100 (rating); $7 < $40 < $65 (price). Confirmed.

**Flag:** `SOT_GEOMETRY_REBUILT`, `RATING_CAP_APPLIED`

**V1 middle preserved for MOT:** The V1 middle tier (82/$25) from Sharif et al. Study 3 is retained as the MOT middle tier, which is independent of the SOT rebuild.

---

## MOT - Multiple Options per Tier

**Source:** V1 web appendix, MOT-6 (lines 683–711), with annotation: "restaurant names follow Sharif et al. Study 3 MOT condition exactly."

| Option | Restaurant | Rating | Price | Tier |
|--------|-----------|--------|-------|------|
| A | The Capital Grille | 98 | $40 | High |
| B | Fleming's Prime | 98 | $40 | High |
| C | Morton's | 98 | $40 | High |
| D | Ruth's Chris | 98 | $40 | High |
| E | Bonefish Grill | 82 | $25 | Middle |
| F | Carrabba's | 82 | $25 | Middle |
| G | Maggiano's | 82 | $25 | Middle |
| H | BJ's Restaurant | 82 | $25 | Middle |
| I | Applebee's | 65 | $7 | Low |
| J | Chili's | 65 | $7 | Low |
| K | TGI Friday's | 65 | $7 | Low |
| L | Buffalo Wild Wings | 65 | $7 | Low |

**Quote from source:**
> MOT-6: Restaurants (Matched with SOT-6; restaurant names follow Sharif et al. Study 3 MOT condition exactly)
> A | The Capital Grille | $40 | 98 | High
> B | Fleming's Prime | $40 | 98 | High
> C | Morton's | $40 | 98 | High
> D | Ruth's Chris | $40 | 98 | High
> E | Bonefish Grill | $25 | 82 | Middle
> F | Carrabba's | $25 | 82 | Middle
> G | Maggiano's | $25 | 82 | Middle
> H | BJ's Restaurant | $25 | 82 | Middle
> I | Applebee's | $7 | 65 | Low
> J | Chili's | $7 | 65 | Low
> K | TGI Friday's | $7 | 65 | Low
> L | Buffalo Wild Wings | $7 | 65 | Low

**Flag:** `MOT_SHARIF_NAMES_PRESERVED` - names are from the published Sharif et al. source, not generic "Brand A/B/..." labels, per the task instruction and the V1 web appendix annotation ("preserve original restaurant names from Sharif Study 3").

**Note on MOT middle tier:** Middle tier (82/$25) is from V1 SOT-6's middle option (Sharif et al. Study 3), retained independently of the SOT geometry rebuild. MOT tier structure does not affect the SOT compromise test geometry.

---

## SYM - Symmetric Decoy

**Source:** V1 web appendix, SYM-6 (lines 1287–1297).

| Option | Role | Rating | Price |
|--------|------|--------|-------|
| A | HF | 65 | $7 |
| B | HD | 98 | $40 |
| C | Symmetric Decoy | 65 | $40 |

**Quote from source:**
> SYM-6: Restaurants (Matched with BIN-6)
> Option A | HF | $7 | 65
> Option B | HD | $40 | 98
> Option C | Symmetric Decoy | $40 | 65

**Geometry check:**
- Decoy (65/$40) vs. HF (65/$7): same rating (65 = 65), price $40 > $7 - HF dominates decoy on price at equal quality.
- Decoy (65/$40) vs. HD (98/$40): same price ($40 = $40), rating 65 < 98 - HD dominates decoy on quality at equal price.
- Decoy is dominated by BOTH focal options. Double dominance confirmed.

**Same-page flag:** Required per Evangelidis et al. 2023; effect dies on separate pages.

---

## SIM - Similarity (CONSTRUCTED; no published analog)

**No published source.** Constructed minimally per the geometry rules (Web Appendix B) SIM geometry.

**Clone target:** HD (is_hd=true; rating 98, price $40).

**Clone:** rating 99, price $40. Same is_hd=true as HD. Minimal distance on rating (1 point). Same price.

| Option | Role | Rating | Price |
|--------|------|--------|-------|
| A | HF | 65 | $7 |
| B | HD | 98 | $40 |
| C | CLONE | 99 | $40 |

**Non-dominance check:**
- Clone (99/$40) vs. HD (98/$40): rating 99 > 98, price equal - HD does NOT dominate clone (HD is worse on rating).
- Clone (99/$40) vs. HF (65/$7): HF has lower price ($7 < $40) but much lower rating (65 < 99) - HF does not dominate clone on quality. No full dominance either direction.
- Clone is not dominated by any option. Berkowitsch rounding accident guard: clone (99/$40) has rating strictly above HD (98/$40), so it is never accidentally a dominated decoy for HD.

**Flag:** `SIM_NO_PUBLISHED_ANALOG`: true

---

## Self-Check against the validator rules (stimuli/validate_stimuli.py)

1. **Dominance (FRQ):** Decoy (96/$43) dominated by HD (98/$40) on BOTH attributes. Not dominated by HF (rating 65 < 96). PASS.
2. **Range (RNG):** Decoy (99/$75) strictly extends price range beyond HD ($75 > $40); no accidental dominance (decoy rating 99 > HD rating 98). PASS.
3. **Phantom (PHT):** Rebuilt phantom superior on EXACTLY ONE attribute (rating 99 > 98); equal on price ($40 = $40). available=false. Never superior on all (R1). PASS (after rebuild).
4. **Compromise (SOT):** Exactly two BIN options plus one new EXTREME (100/$65) beyond HD; former HD (98/$40) is geometrically the middle on both attributes. No free middle added. PASS (after rebuild).
5. **Symmetric (SYM):** Decoy (65/$40) worse than both focal options. Same-page flag set. PASS.
6. **MOT tier identity:** 12 options form three distinct quality tiers (High: 98/$40, Middle: 82/$25, Low: 65/$7); within-tier options near-equivalent (identical attributes, differ only by restaurant name). PASS.
7. **Similarity (SIM):** Clone (99/$40) near-duplicate of HD (rating delta = 1, price delta = 0). Non-dominance confirmed (clone rating 99 > HD rating 98). PASS.
8. **No duplicates:** All options within each set are distinct. No cross-tier collisions. PASS.
9. **Tier-1 fidelity:** BIN, FRQ, RNG, SYM, MOT values match V1 web appendix (Sharif et al. source) exactly. PHT values deviate from published (rebuild documented with flag and published values recorded). SOT values deviate from published (rebuild documented with flag). PASS with flags.

---

## Summary of Flags

| Structure | Flag | Explanation |
|-----------|------|-------------|
| PHT | PHT_rebuilt_R1 | Published phantom ($35/99) superior on BOTH attributes vs. HD. Rebuilt to (99/$40): superior on rating only. Published values recorded in receipts. |
| SOT | SOT_GEOMETRY_REBUILT | V1 used old "add a middle" geometry. Rebuilt with new extreme (100/$65) beyond HD so HD becomes middle. |
| SOT | RATING_CAP_APPLIED | Rating caps at 100; extreme extended via higher price ($65), following geometry_constraints. |
| SIM | SIM_NO_PUBLISHED_ANALOG | No published SIM stimulus for restaurants. Constructed minimally. |
