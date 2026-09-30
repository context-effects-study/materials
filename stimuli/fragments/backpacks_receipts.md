# Source receipts: backpacks_t1 stimuli

**Category:** Backpacks (V1 category number 4)
**Published source:** Evangelidis, Levav, and Simonson 2023, *Journal of Consumer Research* 50(3), doi:10.1093/jcr/ucac059
**Memorization tier:** 1 (exact published values; not calibration-adjusted)

---

## BIN-4 (binary baseline)

**Source document:** V1 web appendix, section "BIN-4: Backpacks," line 299-311

Exact quote from the web appendix:

> **BIN-4: Backpacks** (Source: Evangelidis, Levav, and Simonson 2023)
>
> Stem: "Imagine you are shopping for a backpack. You are considering the following options:"
>
> | Option | Role | Capacity | Price |
> |--------|------|----------|-------|
> | A      | HF   | 30L      | $29.99 |
> | B      | HD   | 40L      | $39.99 |

**Values locked:** HF = 30L/$29.99; HD = 40L/$39.99

**Tradeoff geometry:** HD has 10L more capacity (+33% over HF) at $10 more (+33% over HF). The ratio is symmetric: both attributes step by exactly the same proportion. This is a clean but tight tradeoff (the stimulus design noted it leaves limited room for decoy geometry). No geometry constraint applies (capacity does not cap the way hotel stars do).

---

## FRQ-4 (frequency decoy)

**Source document:** V1 web appendix, section "FRQ-4: Backpacks," lines 877-887

Exact quote:

> **FRQ-4: Backpacks** (Matched with BIN-4; Target: HD option)
>
> | Option | Role             | Capacity | Price  |
> |--------|------------------|----------|--------|
> | A      | HF (Competitor)  | 30L      | $29.99 |
> | B      | HD (Target)      | 40L      | $39.99 |
> | C      | Decoy            | 38L      | $42.99 |

**Geometry check:** Decoy C dominated by HD target B: 40L > 38L on capacity AND $39.99 < $42.99 on price. Decoy C NOT dominated by HF competitor A: A has 30L < 38L, so A does not dominate C on capacity. Asymmetric dominance geometry confirmed.

---

## RNG-4 (range decoy)

**Source document:** V1 web appendix, section "RNG-4: Backpacks," lines 1005-1015

Exact quote:

> **RNG-4: Backpacks** (Matched with BIN-4; Target: HD option)
>
> | Option | Role             | Capacity | Price  |
> |--------|------------------|----------|--------|
> | A      | HF (Competitor)  | 30L      | $29.99 |
> | B      | HD (Target)      | 40L      | $39.99 |
> | C      | Range Decoy      | 45L      | $69.99 |

**Geometry check:** Range decoy C extends the capacity range beyond HD (45L > 40L). Its price is much higher ($69.99 vs $39.99 for HD), making HD look moderate on price. Decoy C is NOT dominated by HD: C has 45L > HD's 40L on capacity, so HD cannot dominate C on both attributes. Range geometry confirmed.

---

## PHT-4 (phantom decoy)

**Source document:** V1 web appendix, section "PHT-4: Backpacks," lines 1135-1145

Exact quote:

> **PHT-4: Backpacks** (Matched with BIN-4; Target: HD option)
>
> | Option | Role             | Capacity | Price  | Available |
> |--------|------------------|----------|--------|-----------|
> | A      | HF (Competitor)  | 30L      | $29.99 | Yes       |
> | B      | HD (Target)      | 40L      | $39.99 | Yes       |
> | C      | Phantom          | 40L      | $34.99 | No        |

**Geometry check:** Phantom C is superior to HD target B on EXACTLY ONE attribute: price ($34.99 < $39.99). Capacity is equal (40L = 40L). This satisfies R1's correction (phantom must be superior on exactly one attribute, never on all). available=false confirmed.

**Engine-regeneration flag:** build_stimuli will regenerate the phantom to canonical PR placement (superior on capacity only, unavailable). The V1 value here (superior on price, equal on capacity) already satisfies the one-attribute rule; the regenerated version may differ.

---

## SOT-4 (compromise - REBUILT)

**Source document (original V1 geometry):** V1 web appendix, section "SOT-4: Backpacks," lines 441-451

Original V1 quote:

> **SOT-4: Backpacks** (Matched with BIN-4)
>
> | Option | Role   | Capacity | Price  |
> |--------|--------|----------|--------|
> | A      | HF     | 30L      | $29.99 |
> | B      | Middle | 35L      | $34.99 |
> | C      | HD     | 40L      | $39.99 |

**Why rebuilt:** V1 SOT-4 used the "add a middle" geometry (35L/$34.99 between HF and HD), leaving HD as the top extreme. The new the geometry rules (Web Appendix B) requires the two BIN options plus a NEW EXTREME BEYOND HD, so the former HD becomes geometrically the middle/compromise. This matches the AE's SOT correction applied to all categories.

**Rebuilt values (placeholder; engine will confirm at calibration):**
- HF: 30L/$29.99 (unchanged from BIN)
- HD (now middle): 40L/$39.99 (unchanged from BIN)
- EXTREME (new): 50L/$49.99

**Middle verification:** 40L is strictly between 30L and 50L on capacity; $39.99 is strictly between $29.99 and $49.99 on price. Former HD is geometrically middle on both attributes.

---

## MOT-4 (multiple options per tier)

**Source document:** V1 web appendix, section "MOT-4: Backpacks," lines 623-651

Exact quote:

> **MOT-4: Backpacks** (Matched with SOT-4; uses generic brand names)
>
> | Option | Brand   | Capacity | Price  | Tier   |
> |--------|---------|----------|--------|--------|
> | A      | Brand A | 40L      | $39.99 | High   |
> | B      | Brand B | 40L      | $39.99 | High   |
> | C      | Brand C | 40L      | $39.99 | High   |
> | D      | Brand D | 40L      | $39.99 | High   |
> | E      | Brand E | 35L      | $34.99 | Middle |
> | F      | Brand F | 35L      | $34.99 | Middle |
> | G      | Brand G | 35L      | $34.99 | Middle |
> | H      | Brand H | 35L      | $34.99 | Middle |
> | I      | Brand I | 30L      | $29.99 | Low    |
> | J      | Brand J | 30L      | $29.99 | Low    |
> | K      | Brand K | 30L      | $29.99 | Low    |
> | L      | Brand L | 30L      | $29.99 | Low    |

**Design note:** Middle tier uses 35L/$34.99, inherited from V1 SOT-4's middle option. Three distinct tiers confirmed. Generic brand names (Brand A through L) isolate tier effects from brand equity, following MOT design note in V1 web appendix.

---

## SYM-4 (symmetric decoy)

**Source document:** V1 web appendix, section "SYM-4: Backpacks," lines 1263-1273

Exact quote:

> **SYM-4: Backpacks** (Matched with BIN-4)
>
> | Option | Role             | Capacity | Price  |
> |--------|------------------|----------|--------|
> | A      | HF               | 30L      | $29.99 |
> | B      | HD               | 40L      | $39.99 |
> | C      | Symmetric Decoy  | 30L      | $39.99 |

**Geometry check:** Decoy C (30L/$39.99) is dominated by BOTH focal options:
- Dominated by HF: same capacity (30L = 30L), higher price ($39.99 > $29.99). HF beats decoy on price at equal capacity.
- Dominated by HD: lower capacity (30L < 40L), same price ($39.99 = $39.99). HD beats decoy on capacity at equal price.
Double dominance confirmed. Same-page presentation mandatory.

---

## SIM-4 (similarity - CONSTRUCTED, no published analog)

**Source document:** None. No Evangelidis et al. 2023 stimulus exists for the similarity structure. Constructed per the geometry rules (Web Appendix B) SIM geometry.

**Construction logic:** Clone of HD (the is_hd=true option). Same capacity (40L), price stepped up minimally by $2.00 to $41.99. Clone shares is_hd=true with HD. Clone is NOT dominated by HD (HD beats clone on price, but both have equal capacity; no strict dominance on both attributes). Clone is not dominated by HF (clone has 40L > HF's 30L on capacity).

**Engine-regeneration flag:** build_stimuli engine will regenerate SIM to ensure the non-dominance guard (Berkowitsch rounding accident prevention per the geometry rules (Web Appendix B)).

---

## Summary flags

| Structure | Values source       | All values from V1 web appendix? | Geometry verified? | Engine regen? |
|-----------|---------------------|----------------------------------|--------------------|---------------|
| BIN       | Published exact     | YES                              | N/A (baseline)     | No            |
| FRQ       | Published exact     | YES                              | YES                | No            |
| RNG       | Published exact     | YES                              | YES                | No            |
| PHT       | Published exact     | YES                              | YES (one-attr)     | YES (PR placement) |
| SOT       | V1 geometry OLD; REBUILT | Partial (BIN values kept) | YES (new extreme)  | YES (extreme value) |
| MOT       | Published exact     | YES                              | YES (3 tiers)      | No            |
| SYM       | Published exact     | YES                              | YES (double dom.)  | No            |
| SIM       | CONSTRUCTED         | NO (no published analog)         | YES (non-dom.)     | YES (non-dom. guard) |
