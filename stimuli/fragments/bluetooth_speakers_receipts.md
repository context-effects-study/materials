# Source receipts: bluetooth_speakers tier-1 stimuli

Generated: 2026-06-12. Category 2 (V1 numbering), Bluetooth speakers.
Source primary: Evangelidis, Levav, and Simonson 2023, JCR 50(3), doi:10.1093/jcr/ucac059.
Stimulus-plan authority: the stimulus design.

---

## BIN (binary baseline)

| Value | Exact source quote / location |
|---|---|
| HF rating: 3.6 stars | V1 web appendix, BIN-2 table: "A / HF / 3.6 out of 5 stars / $39.99" |
| HF price: $39.99 | Same row |
| HD rating: 4.5 stars | V1 web appendix, BIN-2 table: "B / HD / 4.5 out of 5 stars / $69.99" |
| HD price: $69.99 | Same row |
| Stem | V1 web appendix BIN-2: "Imagine you are shopping for a Bluetooth speaker. You are considering the following options:" |
| Category source attribution | V1 web appendix §Design Overview table, row 2: "Bluetooth Speakers / Amazon rating (stars), Price ($) / Evangelidis et al. (2023)" |

Cross-check: the category table of the design: "Bluetooth speakers / Amazon rating (stars), price ($) / Evangelidis et al. 2023 / 3.6 stars/$39.99 vs 4.5 stars/$69.99" - exact match.

---

## FRQ (frequency decoy)

| Value | Exact source quote / location |
|---|---|
| HF and HD | Inherited from BIN-2 (see above) |
| Decoy rating: 4.3 stars | V1 web appendix, FRQ-2 table: "C / Decoy / 4.3 out of 5 stars / $74.99" |
| Decoy price: $74.99 | Same row |
| Target: HD | V1 web appendix FRQ-2 header: "Target: HD option" |
| Dominance check | Decoy (4.3/$74.99) vs HD (4.5/$69.99): HD wins on both attributes (4.5 > 4.3; $69.99 < $74.99). Decoy dominated by target only. HF (3.6/$39.99) does not dominate decoy (HF rating 3.6 < decoy 4.3). Geometry confirmed. |

---

## RNG (range decoy)

| Value | Exact source quote / location |
|---|---|
| HF and HD | Inherited from BIN-2 |
| Decoy rating: 4.6 stars | V1 web appendix, RNG-2 table: "C / Range Decoy / 4.6 out of 5 stars / $119.99" |
| Decoy price: $119.99 | Same row |
| Target: HD | V1 web appendix RNG-2 header: "Target: HD option" |
| Range geometry check | Decoy price $119.99 extends price range well beyond HD $69.99 (delta = $50). Decoy rating 4.6 is marginally above HD 4.5, making decoy slightly better on quality - NOT dominated by HD. This satisfies range geometry: the range on the target's weak attribute (price) is extended, making the target's price look moderate. V1 web appendix RNG-2 note: "Decoy C extends the price range, making B appear more moderate." |
| No-dominance flag | Decoy (4.6 stars/$119.99): HD (4.5/$69.99) does NOT dominate decoy because decoy rating 4.6 > HD rating 4.5. Validator check §6.2 passes. |

---

## PHT (phantom decoy)

| Value | Exact source quote / location |
|---|---|
| HF and HD | Inherited from BIN-2 |
| Phantom rating: 4.5 stars | V1 web appendix, PHT-2 table: "C / Phantom / 4.5 out of 5 stars / $59.99 / No" |
| Phantom price: $59.99 | Same row |
| Phantom available: false | Same row (column "Available": "No") |
| Target: HD | V1 web appendix PHT-2 header: "Target: HD option" |
| One-attribute superiority check | Phantom (4.5/$59.99) vs HD (4.5/$69.99): phantom superior on price only ($59.99 < $69.99); equal on rating (4.5 = 4.5). Exactly ONE attribute superior. R1 correction satisfied: phantom is NOT superior on all attributes. Validator check §6.3 passes. |

---

## SOT (compromise - REBUILT)

**FLAG: V1 SOT-2 geometry was incorrect for the new plan. Rebuilt.**

V1 SOT-2 (old geometry, DO NOT USE as source of values):
- A=HF: 3.6/$39.99, B=Middle: 4.0/$54.99, C=HD: 4.5/$69.99
- Problem: V1 added a middle option between HF and HD. HD remained the top extreme. This tests whether the middle is chosen, not whether HD gains from becoming the compromise.

New geometry (the geometry rules (Web Appendix B), SOT row): "the two BIN options + ONE NEW EXTREME beyond the HD option, so the former HD becomes the middle/compromise. Statistic = relative share target/(target+competitor). NEVER 'add a free middle.'"

| Value | Derivation |
|---|---|
| HF: 3.6 stars/$39.99 | Unchanged from BIN-2 |
| HD (now middle): 4.5 stars/$69.99 | Unchanged from BIN-2; now geometrically the middle option |
| Extreme rating: 5.0 stars | Rating cap applied. Next step above HD (4.5) must exceed 4.5 but cannot exceed 5.0; 5.0 is the maximum. |
| Extreme price: $99.99 | Rating cap reached at 5.0; extended via higher price per geometry_constraints. Price step from HD: $99.99 - $69.99 = $30.00, comparable to HF-to-HD step of $30.00. Constructed minimally to be clearly beyond HD. |
| Rating cap authority | V1 web appendix Hotels note (RNG-3): "Because hotel star ratings cannot exceed 5-star, we extend the price range rather than quality range for this category." Applied by analogy to Bluetooth speakers (star rating also caps at 5.0). the category table of the design geometry_constraints for Hotels: recorded for the validator. Same constraint documented here for bluetooth_speakers. |
| Middle geometry verification | HD (4.5/$69.99) is strictly between HF (3.6/$39.99) and EXTREME (5.0/$99.99) on both dimensions: rating 3.6 < 4.5 < 5.0 (confirmed); price $39.99 < $69.99 < $99.99 (confirmed). Validator check §6.4 passes. |
| Statistic | target/(target+competitor) per the geometry rules (Web Appendix B): "Statistic = relative share target/(target+competitor)" |

---

## MOT (multiple options per tier)

| Value | Exact source quote / location |
|---|---|
| High tier: 4.5 stars/$69.99 (×4 brands) | V1 web appendix MOT-2 table, rows A-D: "Brand A/B/C/D / 4.5 out of 5 stars / $69.99 / High" |
| Middle tier: 4.0 stars/$54.99 (×4 brands) | V1 web appendix MOT-2 table, rows E-H: "Brand E/F/G/H / 4.0 out of 5 stars / $54.99 / Middle" |
| Low tier: 3.6 stars/$39.99 (×4 brands) | V1 web appendix MOT-2 table, rows I-L: "Brand I/J/K/L / 3.6 out of 5 stars / $39.99 / Low" |
| Brand labels | V1 web appendix MOT-2 header: "uses generic brand names"; V1 web appendix §Design Overview brand note: "most MOT scenarios use generic brand labels (Brand A, Brand B, etc.) to isolate the tier effect from brand equity confounds" |
| Note on middle tier | MOT middle tier (4.0/$54.99) uses the same values as V1's SOT-2 middle option. This is preserved in MOT because MOT's three tiers are independent of the SOT compromise-effect geometry. The MOT structure is not a compromise test; it is an extremity test. Middle tier values are therefore inheritable from V1 without conflict. |

---

## SYM (symmetric decoy)

| Value | Exact source quote / location |
|---|---|
| HF and HD | Inherited from BIN-2 |
| Decoy rating: 3.6 stars | V1 web appendix, SYM-2 table: "C / Symmetric Decoy / 3.6 out of 5 stars / $69.99" |
| Decoy price: $69.99 | Same row |
| Double-dominance check | Decoy (3.6/$69.99): dominated by HF (3.6/$39.99) because same rating, higher price ($69.99 > $39.99). Dominated by HD (4.5/$69.99) because lower rating (3.6 < 4.5), same price. Both focal options dominate the decoy. Validator check §6.5 passes. |
| Same-page flag | Required per the geometry rules (Web Appendix B) "Same-page mandatory (effect dies on separate pages)" and Evangelidis et al. 2023 moderator: "Moderators Attenuating Effect: decoy on separate page (-)". |
| Statistic | delta_hd_minus_delta_hf_vs_binary: upscaling predicts delta-HD > delta-HF when symmetric decoy is added. |

---

## SIM (similarity - NEW, no published analog)

| Value | Derivation / authority |
|---|---|
| HF and HD | Inherited from BIN-2 |
| Clone rating: 3.7 stars | Constructed. HF rating is 3.6; clone steps up by 0.1 stars (minimal distance on a 5-point scale with 0.1 resolution, matching the resolution used throughout this category). Step chosen to be as small as practically distinguishable while remaining above HF. |
| Clone price: $39.99 | Identical to HF price; minimal distance on price dimension ($0 difference). |
| Clone is_hd | false, same as HF. Clone is a near-duplicate of HF, the HF option. |
| Non-dominance check | Clone (3.7/$39.99): HF (3.6/$39.99) does NOT dominate clone because HF rating 3.6 < clone rating 3.7 (HF is worse on quality). HD (4.5/$69.99) does not dominate clone on both attributes simultaneously: clone is cheaper ($39.99 < $69.99). Clone is therefore not dominated by any option. Berkowitsch guard satisfied. Validator check §6.7 passes. |
| Published analog | None. No SIM structure exists in Evangelidis et al. 2023 or V1 web appendix. no_published_analog=true. |
| Authority for structure | the geometry rules (Web Appendix B) SIM row: "BIN + a near-CLONE of one focal option (same is_hd, minimal distance, not dominated)." |

---

## Self-check against the validator rules (stimuli/validate_stimuli.py)

| Check | Status |
|---|---|
| §6.1 Dominance (FRQ): decoy dominated by target on both attributes; asymmetric only | PASS: decoy (4.3/$74.99) dominated by HD (4.5/$69.99) on both; HF does not dominate decoy on quality. |
| §6.2 Range (RNG): decoy strictly extends range; no accidental dominance | PASS: decoy (4.6/$119.99) extends price range; not dominated by HD (decoy rating 4.6 > HD 4.5). |
| §6.3 Phantom (PHT): superior on EXACTLY ONE attribute; available=false | PASS: phantom superior on price only; equal on rating; available=false. |
| §6.4 Compromise (SOT): exactly two BIN options + one new extreme beyond HD; former HD is geometrically the middle | PASS (after rebuild): extreme (5.0/$99.99) is beyond HD (4.5/$69.99); HD is strictly between HF and EXTREME on both attributes. |
| §6.5 Symmetric (SYM): decoy worse than both; same-page flag | PASS: decoy (3.6/$69.99) dominated by both HF and HD; same-page flag set in flags. |
| §6.6 MOT tier identity: 12 options; distinct quality tiers; within-tier near-equivalent | PASS: 4 brands × 3 tiers = 12; High (4.5/$69.99), Middle (4.0/$54.99), Low (3.6/$39.99); within-tier options identical on attrs. |
| §6.7 Similarity (SIM): clone near-duplicate; non-dominance assertion | PASS: clone (3.7/$39.99) differs from HF by 0.1 stars/same price; not dominated by HF or HD. |
| §6.8 Cross-category geometry consistency | CANNOT FULLY VERIFY here (requires checking all 7 categories); within this category all structures use the same relational rules. Flag for cross-category validation pass. |
| §6.9 No duplicates | PASS: no two options within any set are identical; no cross-stimulus collisions within this category. |
| §6.10 Tier-1 fidelity | PASS for BIN, FRQ, RNG, PHT, SYM, MOT (all values match V1 web appendix verbatim). EXCEPTION: SOT extreme (5.0/$99.99) is a constructed value not in V1, flagged explicitly. SIM clone is also constructed, flagged. |
| §6.11 Single-source integrity | NOT APPLICABLE at this stage (applies to the web-appendix generation from stimuli.json at build time). |

**Checks that could not be fully satisfied:**
- §6.8 cross-category geometry consistency requires the full 7-category set to verify; cannot be confirmed from this single-category fragment alone.
- §6.11 single-source integrity is a build-time check (generate web appendix from stimuli.json); not checkable from a fragment file.
- SOT tier-1 fidelity: the new extreme (5.0/$99.99) has NO published-source precedent (the old SOT-2 middle 4.0/$54.99 is the only V1 value, and it is now inapplicable). This value is a minimal construction; it is NOT a tier-1 published value and should be labeled accordingly in stimuli.json (calibration_locked=false, available for tier-2 calibration adjustments).
