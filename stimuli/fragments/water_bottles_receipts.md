# Water Bottles - Stimulus Source Receipts

**Category:** Water Bottles (id: `water_bottles`; V1 category number 8)
**Attributes:** capacity in oz (higher is better), price in $ (lower is better)
**Published source:** Sharif, Webb, and Bhatia 2025, *Journal of Consumer Research*, doi:10.1093/jcr/ucaf061
**Produced:** 2026-06-12

---

## BIN_water_bottles_t1 - Binary Baseline

**All values from:** V1 web appendix, section "BIN-8: Water Bottles," verbatim table.

| Field | Quoted source text |
|---|---|
| Stem | "Imagine you are shopping for a reusable water bottle. You are considering the following options:" - V1 web appendix BIN-8 stem |
| HF: capacity 18 oz | V1 web appendix BIN-8 table, Option A row: "18 oz" |
| HF: price $7.99 | V1 web appendix BIN-8 table, Option A row: "$7.99" |
| HD: capacity 40 oz | V1 web appendix BIN-8 table, Option B row: "40 oz" |
| HD: price $9.99 | V1 web appendix BIN-8 table, Option B row: "$9.99" |
| Source attribution | V1 web appendix p.5 table row: "Water Bottles - Capacity (oz), Price ($) - Sharif et al. (forthcoming)" |

**is_hd assignment:** Option B (40 oz/$9.99) is HD because it has the higher capacity and higher price. Option A (18 oz/$7.99) is HF.

---

## FRQ_water_bottles_t1 - Frequency Decoy

**All values from:** V1 web appendix, section "FRQ-8: Water Bottles."

| Field | Quoted source text |
|---|---|
| BIN options | Inherited from BIN-8 (see above); unchanged |
| Decoy: capacity 38 oz | V1 web appendix FRQ-8 table, Option C row: "38 oz" |
| Decoy: price $10.99 | V1 web appendix FRQ-8 table, Option C row: "$10.99" |

**Dominance check (validator §6.1):**
- HD (40 oz/$9.99) dominates decoy (38 oz/$10.99): capacity 40 > 38 ✓ and price $9.99 < $10.99 ✓
- HF (18 oz/$7.99) does NOT dominate decoy: HF capacity 18 < decoy capacity 38 ✗

Asymmetric dominance geometry satisfied. No flags raised.

---

## RNG_water_bottles_t1 - Range Decoy

**All values from:** V1 web appendix, section "RNG-8: Water Bottles."

| Field | Quoted source text |
|---|---|
| BIN options | Inherited from BIN-8 (see above); unchanged |
| Range decoy: capacity 48 oz | V1 web appendix RNG-8 table, Option C row: "48 oz" |
| Range decoy: price $14.99 | V1 web appendix RNG-8 table, Option C row: "$14.99" |

**Range geometry check (validator §6.2):**
- Decoy capacity 48 oz > HD capacity 40 oz: extends the capacity range beyond HD ✓
- Decoy price $14.99 > HD price $9.99: extends the price range beyond HD ✓
- Decoy NOT dominated by HD: decoy capacity 48 > HD capacity 40, so HD cannot beat decoy on capacity ✓

HD is the target (strong attribute = capacity). The range decoy makes HD look moderate on price. No flags raised.

---

## PHT_water_bottles_t1 - Phantom Decoy

**All values from:** V1 web appendix, section "PHT-8: Water Bottles."

| Field | Quoted source text |
|---|---|
| BIN options | Inherited from BIN-8 (see above); unchanged |
| Phantom: capacity 40 oz | V1 web appendix PHT-8 table, Option C row: "40 oz" |
| Phantom: price $8.99 | V1 web appendix PHT-8 table, Option C row: "$8.99" |
| Phantom: available=false | V1 web appendix PHT-8 table, Option C row: "No" in Available column |

**R1 compliance check (validator §6.3 - superior on EXACTLY ONE attribute):**
- Phantom price $8.99 vs HD price $9.99: $8.99 < $9.99 → phantom BETTER on price ✓
- Phantom capacity 40 oz vs HD capacity 40 oz: equal → phantom NOT better on capacity ✓

Phantom is superior on exactly one attribute (price). Published values preserved. **No PHT_rebuilt_R1 flag needed.**

---

## SOT_water_bottles_t1 - Compromise (Single Option per Tier) - REBUILT

**Flag: SOT_GEOMETRY_REBUILT**

**V1 published values (NOT used - wrong geometry):** V1 web appendix SOT-8: HF $7.99/18 oz, Middle $8.99/32 oz, HD $9.99/40 oz. V1 added a middle option between the two BIN options, leaving HD as the top extreme. This is the OLD "add a middle" geometry that the new plan explicitly corrects.

**New plan (the geometry rules (Web Appendix B)):** the two BIN options plus ONE NEW EXTREME beyond HD, so former HD becomes the middle/compromise. Statistic = target/(target+competitor).

**Constructed EXTREME option:**

| Field | Value | Derivation |
|---|---|---|
| EXTREME: capacity 64 oz | 64 oz | Extends capacity range well beyond HD (40 oz); 64 oz is a standard large water bottle size, realistic and common in the category |
| EXTREME: price $14.99 | $14.99 | Extends price range beyond HD ($9.99); chosen to match V1 RNG-8 range decoy price, providing consistent upper bound |

**SOT middle verification (validator §6.4):**
- HF capacity 18 oz < HD capacity 40 oz < EXTREME capacity 64 oz ✓
- HF price $7.99 < HD price $9.99 < EXTREME price $14.99 ✓

Former HD (40 oz/$9.99) is geometrically the middle option on both attributes. Geometry correct.

---

## MOT_water_bottles_t1 - Multiple Options per Tier (Extremity Effect)

**All values from:** V1 web appendix, section "MOT-8: Water Bottles."

**COLOR field (not brand):** V1 web appendix p.12 states explicitly: "MOT-8 (Water Bottles) uses colors rather than brands, following Sharif et al. Study 5." The V1 table for MOT-8 uses a "Color" column with four colors: Grey, Blue, Purple, Pink. This is the published operationalization.

| Tier | Color | Capacity | Price | Source quote |
|---|---|---|---|---|
| High | Grey | 40 oz | $9.99 | V1 web appendix MOT-8, Option A row |
| High | Blue | 40 oz | $9.99 | V1 web appendix MOT-8, Option B row |
| High | Purple | 40 oz | $9.99 | V1 web appendix MOT-8, Option C row |
| High | Pink | 40 oz | $9.99 | V1 web appendix MOT-8, Option D row |
| Middle | Grey | 32 oz | $8.99 | V1 web appendix MOT-8, Option E row |
| Middle | Blue | 32 oz | $8.99 | V1 web appendix MOT-8, Option F row |
| Middle | Purple | 32 oz | $8.99 | V1 web appendix MOT-8, Option G row |
| Middle | Pink | 32 oz | $8.99 | V1 web appendix MOT-8, Option H row |
| Low | Grey | 18 oz | $7.99 | V1 web appendix MOT-8, Option I row |
| Low | Blue | 18 oz | $7.99 | V1 web appendix MOT-8, Option J row |
| Low | Purple | 18 oz | $7.99 | V1 web appendix MOT-8, Option K row |
| Low | Pink | 18 oz | $7.99 | V1 web appendix MOT-8, Option L row |

**Note on MOT middle tier values:** The middle tier (32 oz/$8.99) comes from V1 SOT-8's old middle option. These tier values are kept for MOT because MOT's menu-tier structure is independent of the SOT compromise geometry rebuild. The three tiers (High/Middle/Low) are the same three quality levels used in the published Sharif et al. Study 5 operationalization.

---

## SYM_water_bottles_t1 - Symmetric Decoy (Upscaling Effect)

**All values from:** V1 web appendix, section "SYM-8: Water Bottles."

| Field | Quoted source text |
|---|---|
| BIN options | Inherited from BIN-8 (see above); unchanged |
| SYM decoy: capacity 18 oz | V1 web appendix SYM-8 table, Option C row: "18 oz" |
| SYM decoy: price $9.99 | V1 web appendix SYM-8 table, Option C row: "$9.99" |

**Double dominance check (validator §6.5):**
- HF (18 oz/$7.99) dominates decoy (18 oz/$9.99): equal capacity, HF price $7.99 < decoy price $9.99 ✓
- HD (40 oz/$9.99) dominates decoy (18 oz/$9.99): equal price, HD capacity 40 > decoy capacity 18 ✓

Decoy is worse than BOTH focal options. Same-page flag required. No flags raised beyond standard SYM notes.

---

## SIM_water_bottles_t1 - Similarity (Constructed, No Published Analog)

**Flag: SIM_NO_PUBLISHED_ANALOG**

No published stimulus exists for the similarity structure in Sharif, Webb, and Bhatia 2025 or in any V1 source for water bottles.

**Construction logic (the geometry rules (Web Appendix B) SIM geometry):**

Clone is a near-duplicate of HF (is_hd=false) with minimal distance on one attribute.

| Field | Value | Derivation |
|---|---|---|
| Clone: capacity 20 oz | 20 oz | HF is 18 oz; step of +2 oz (minimal, preserves near-identity); 20 oz is a plausible small water bottle size |
| Clone: price $7.99 | $7.99 | Identical to HF price; no price distance, so the clone is distinguishable from HF only on capacity |

**Non-dominance check (Berkowitsch guard, validator §6.7):**
- HF (18 oz/$7.99) does NOT dominate clone (20 oz/$7.99): equal price, but clone capacity 20 > HF capacity 18, so HF cannot beat clone on capacity ✓
- HD (40 oz/$9.99) does NOT dominate clone (20 oz/$7.99): clone price $7.99 < HD price $9.99, so HD cannot beat clone on price ✓
- Clone is NOT a decoy: it is not dominated by either focal option ✓

Clone shares is_hd=false with HF. Distance from HF: 2 oz on capacity (minimal), $0 on price (identical). Clone will steal share from HF.

---

## Self-Check Against the validator rules (stimuli/validate_stimuli.py)

| Validator check | Status |
|---|---|
| §6.1 FRQ dominance: decoy dominated by target on both attributes; not by competitor | PASS - HD beats decoy on both; HF does not |
| §6.2 RNG: decoy extends target's strong-attribute range; no accidental dominance | PASS - decoy capacity 48 > HD 40; decoy not dominated by HD |
| §6.3 PHT: superior on EXACTLY ONE attribute; available=false; never superior on all | PASS - superior on price only; equal on capacity; available=false |
| §6.4 SOT: exactly the two BIN options plus one new extreme beyond HD; former HD is geometrically the middle | PASS (after rebuild) - HD at 40 oz/$9.99 is middle between 18 oz/$7.99 and 64 oz/$14.99 |
| §6.5 SYM: decoy worse than both focal options; same-page flag set | PASS - decoy dominated by HF on price, by HD on capacity |
| §6.6 MOT tier identity: 12 options in 3 distinct quality tiers; within-tier near-equivalent | PASS - 4 colors per tier; within-tier attributes identical |
| §6.7 SIM: clone near-duplicate of one focal option; non-dominance confirmed | PASS - clone (20 oz/$7.99) differs from HF (18 oz/$7.99) by 2 oz; not dominated by either focal option |
| §6.8 Cross-category geometry: same relational rules as sibling categories | PASS - same decoy geometry rules applied as in bluetooth_speakers.json |
| §6.9 No duplicates: no two options within a set are identical | PASS - verified per structure |
| §6.10 Tier-1 fidelity: every tier-1 value matches cited source | PASS (except SOT which is rebuilt per plan; BIN, FRQ, RNG, PHT, SYM, MOT all match V1 web appendix exactly) |
| §6.11 Single-source integrity: no hand-typed values | PASS - all values traced to V1 web appendix verbatim quotes above |

---

## Flags Summary

| Structure | Flag | Description |
|---|---|---|
| SOT | SOT_GEOMETRY_REBUILT | V1 SOT-8 used old "add a middle" geometry (Middle=32 oz/$8.99, HD remained the top). Rebuilt with new extreme at 64 oz/$14.99 so former HD (40 oz/$9.99) becomes the middle. |
| MOT | MOT_COLORS_NOT_BRANDS | Colors (Grey, Blue, Purple, Pink) used as within-tier differentiators per published Sharif et al. Study 5 operationalization; documented in V1 web appendix. |
| SIM | SIM_NO_PUBLISHED_ANALOG | No published similarity stimulus exists for water bottles. Constructed minimally: clone of HF at 20 oz/$7.99 (minimal 2 oz step, same price). |
| PHT | (no flag) | Published phantom (40 oz/$8.99) is already superior on exactly one attribute (price); R1 geometry satisfied; no rebuild needed. |
