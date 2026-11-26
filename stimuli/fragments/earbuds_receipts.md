# Earbuds Stimulus Receipts

Source: V1 web appendix (`v2_revision/web_appendices/web_appendix.md`) lines 341-355 (BIN-7),
477-487 (SOT-7), 713-741 (MOT-7), 913-923 (FRQ-7), 1041-1051 (RNG-7), 1171-1181 (PHT-7),
1299-1309 (SYM-7). Published paper: Sharif, Webb, and Bhatia 2025, JCR,
doi:10.1093/jcr/ucaf061. (V1 cites as "forthcoming"; now published with Bhatia as third author.)
Cross-checks: the geometry rules (Web Appendix B) (geometry), §6 (validation), bluetooth_speakers.json (shape).

---

## BIN-7 (shared baseline - all values tier-1 published)

Source quote (web appendix line 341-354):
> **BIN-7: Earbuds** (Source: Sharif, Webb, and Bhatia forthcoming)
> Stem: "Imagine you are shopping for wireless earbuds. The number of reviews indicates how many
> customers have purchased and reviewed the product. You are considering the following options:"
> Option A | HF | $5.99 | 1,147
> Option B | HD | $19.99 | 11,076

- HF: reviews = 1,147; price = $5.99. EXACT PUBLISHED.
- HD: reviews = 11,076; price = $19.99. EXACT PUBLISHED.
- Stem: transcribed verbatim from BIN-7. Changed to first-person forced form per the stimulus design
  §3 advisor/deferral cut (original stem already in first-person "Imagine you are shopping...").
- HD strong attribute = reviews (11,076 >> 1,147 = ~9.7x more reviews). HD weak attribute = price
  ($19.99 > $5.99).
- No flags.

---

## FRQ-7 (attraction-frequency decoy - all values tier-1 published)

Source quote (web appendix lines 913-923):
> **FRQ-7: Earbuds** (Matched with BIN-7; Target: HD option)
> Option A | HF (Competitor) | $5.99 | 1,147
> Option B | HD (Target) | $19.99 | 11,076
> Option C | Decoy | $21.99 | 10,500

- Decoy: reviews = 10,500; price = $21.99. EXACT PUBLISHED.
- Dominance check: decoy dominated by HD on BOTH attributes (HD reviews 11,076 > 10,500;
  HD price $19.99 < $21.99). PASS.
- Non-dominance by HF check: HF reviews 1,147 < 10,500, so HF does NOT dominate decoy on
  reviews. PASS - asymmetric dominance geometry correct.
- No flags.

---

## RNG-7 (attraction-range decoy - all values tier-1 published)

Source quote (web appendix lines 1041-1051):
> **RNG-7: Earbuds** (Matched with BIN-7; Target: HD option)
> Option A | HF (Competitor) | $5.99 | 1,147
> Option B | HD (Target) | $19.99 | 11,076
> Option C | Range Decoy | $34.99 | 12,500

- Range decoy: reviews = 12,500; price = $34.99. EXACT PUBLISHED.
- Range extension: decoy extends reviews range beyond HD (12,500 > 11,076) and price range
  beyond HD ($34.99 > $19.99). HD price $19.99 now looks moderate vs $34.99.
- Non-dominance check: HD reviews 11,076 < decoy reviews 12,500, so HD cannot dominate decoy
  on reviews. PASS - decoy not dominated by HD; range geometry correct.
- No flags.

---

## PHT-7 (phantom - REBUILT; R1 violation in published values)

Source quote (web appendix lines 1171-1181):
> **PHT-7: Earbuds** (Matched with BIN-7; Target: HD option)
> Option A | HF (Competitor) | $5.99 | 1,147 | Yes
> Option B | HD (Target) | $19.99 | 11,076 | Yes
> Option C | Phantom | $17.99 | 12,000 | No

- Published phantom: reviews = 12,000; price = $17.99. Available = No.
- R1 VIOLATION: published phantom is superior to HD on BOTH attributes:
  - Price: $17.99 < $19.99 (phantom is cheaper = BETTER than HD on price).
  - Reviews: 12,000 > 11,076 (phantom has more reviews = BETTER than HD on reviews).
  - the geometry rules (Web Appendix B) PHT unified rule: phantom must be superior on EXACTLY ONE attribute.
  - the design notes on the phantom effect: "superior on exactly one attribute and equal on the other"
    (citing Pettibone and Wedell 2007 PR placement). The both-attributes geometry (PRF/PERF)
    is the weakest, least reliable phantom placement.

FLAG: PHT_rebuilt_R1.

REBUILD decision:
- Keep published reviews value 12,000 (superior on target's strong attribute = reviews).
- Set price to $19.99 (equal to HD price; not superior on price).
- Rebuilt phantom: reviews = 12,000 (kept from published), price = $19.99 (new, not published).
- This matches the Pettibone-Wedell PR placement exactly (equal on weak attribute, better on
  strong attribute). One attribute superior, one attribute equal. R1 geometry satisfied.

Values in output:
- PHANTOM reviews = 12,000 (published value, KEPT)
- PHANTOM price = $19.99 (rebuilt; published $17.99 DISCARDED as R1 violation)
- phantom_superior_on = "reviews"

---

## SOT-7 (compromise - REBUILT; V1 used old "add a middle" geometry)

Source quote (web appendix lines 477-487):
> **SOT-7: Earbuds** (Matched with BIN-7)
> Option A | HF | $5.99 | 1,147
> Option B | Middle | $12.99 | 5,500
> Option C | HD | $19.99 | 11,076

- Published SOT-7 adds a MIDDLE option ($12.99 / 5,500 reviews) and keeps HD as the top extreme.
- This is the old "add a middle" geometry where HD remains the top; HD does NOT become the
  compromise option between two extremes.
- the geometry rules (Web Appendix B) SOT (corrected compromise): "SAME two BIN options PLUS one NEW EXTREME
  beyond HD, so former HD becomes the middle." V1's SOT-7 used the wrong geometry.

FLAG: SOT_GEOMETRY_REBUILT.

REBUILD decision:
- Keep HF ($5.99 / 1,147) and HD ($19.99 / 11,076) unchanged (same BIN options).
- Add EXTREME beyond HD: 20,000 reviews / $34.99.
  - Reviews: 20,000 > 11,076. HD reviews now middle: 1,147 < 11,076 < 20,000. PASS.
  - Price: $34.99 > $19.99. HD price now middle: $5.99 < $19.99 < $34.99. PASS.
  - Price matches RNG range decoy for within-category consistency.
  - Reviews value 20,000 is a clean round number approximately doubling the HD-to-HF gap
    extended beyond HD.
- Discard published V1 middle option ($12.99 / 5,500 reviews) from SOT structure.
  (Middle tier values are preserved in MOT.)

Values in output:
- HF: $5.99 / 1,147 (unchanged, published)
- HD: $19.99 / 11,076 (unchanged, published)
- EXTREME: $34.99 / 20,000 (rebuilt; no published SOT-7 analog)

---

## MOT-7 (multiple options per tier - all values tier-1 published)

Source quote (web appendix lines 713-741):
> **MOT-7: Earbuds** (Matched with SOT-7; uses generic brand names)
> Brand A-D | $19.99 | 11,076 | High
> Brand E-H | $12.99 | 5,500 | Middle
> Brand I-L | $5.99 | 1,147 | Low

- High tier: reviews = 11,076; price = $19.99. EXACT PUBLISHED. 4 brands.
- Middle tier: reviews = 5,500; price = $12.99. 4 brands. **SUPERSEDED 2026-07-01 - see the
  correction note below; this V1 value was NOT the published middle.**
- Low tier: reviews = 1,147; price = $5.99. EXACT PUBLISHED. 4 brands.
- Total: 12 options across 3 distinct quality tiers. Tier structure correct.
- Note: Middle tier values ($12.99 / 5,500) come from V1's SOT-7 middle option; they remain
  the MOT middle tier even though SOT-7 geometry has been rebuilt. MOT tier structure is
  independent of the SOT compromise rebuild. **(Superseded by the correction below.)**

**CORRECTION (2026-07-01, decided by the authors tier-1 fidelity fix).** Reading the published
full text (`_archive_presubmission/old md files/ucaf061.pdf`, Study 6 method) surfaced that
V1's MOT-7 middle tier ($12.99 / 5,500 reviews) was V1's own construction (inherited from
V1 SOT-7's add-a-middle option), not a published value. Sharif, Webb, and Bhatia 2025
Study 6's published middle option is **$15.49 / 6,544 reviews** ("the median price-median
number of reviews headphones (Price: $15.49, Reviews: 6,544)"; the same values appear in the
MOT-condition listing; the results section twice prints 6,554, an internal inconsistency
with the method section's stimulus listing, so 6,544 is the value of record). The fragment's
MOT_earbuds_t1 middle tier is corrected to $15.49 / 6,544; High/Low tiers were already the
published extremes. The matched EXC control re-derives from the corrected tiers at build
(`exc_from_mot`). This is the third stimulus-value correction under the
reality-contradicts-registered-claim rule (after the RNG geometry rebuild and the M2 anchor
restoration, both 2026-07-01).

---

## SYM-7 (upscaling / symmetric decoy - all values tier-1 published)

Source quote (web appendix lines 1299-1309):
> **SYM-7: Earbuds** (Matched with BIN-7)
> Option A | HF | $5.99 | 1,147
> Option B | HD | $19.99 | 11,076
> Option C | Symmetric Decoy | $19.99 | 1,147

- Symmetric decoy: reviews = 1,147; price = $19.99. EXACT PUBLISHED.
- Double dominance check:
  - HF ($5.99 / 1,147) vs decoy ($19.99 / 1,147): same reviews, HF cheaper → HF dominates
    decoy on price. PASS.
  - HD ($19.99 / 11,076) vs decoy ($19.99 / 1,147): same price, HD has far more reviews →
    HD dominates decoy on reviews. PASS.
  - Decoy is dominated by BOTH focal options. SYM geometry correct.
- Same-page flag required per Evangelidis et al. 2023.
- No flags.

---

## SIM (similarity - CONSTRUCTED; no published analog)

No published SIM-7 scenario exists in Sharif et al. 2025 or in the V1 web appendix. This
structure was added to V2 per the new plan (the geometry rules (Web Appendix B) SIM). Constructed minimally.

FLAG: SIM_NO_PUBLISHED_ANALOG = true.

Construction logic:
- Clone of HD (is_hd=true) to test similarity stealing from HD.
- HD = $19.99 / 11,076 reviews.
- Clone = $19.99 / 11,500 reviews.
  - Same price as HD ($19.99). Minimal distance.
  - Reviews 11,500 > 11,076: ~4% more reviews. Minimal upward step.
  - Non-dominance check: clone reviews 11,500 > HD reviews 11,076, so HD cannot dominate
    clone on reviews; equal price, so neither dominates on price. PASS - clone is NOT a decoy.
    Berkowitsch rounding accident guard satisfied.
  - Clone shares is_hd=true with HD (same tier).
  - Similarity effect: clone steals share from HD (the option it resembles).
- target in output = "HF" (the remaining focal option after clone takes HD's share), competitor
  = "HD".

Values in output:
- CLONE: reviews = 11,500; price = $19.99 (constructed; no published analog)

---

## Self-check against the validator rules (stimuli/validate_stimuli.py)

1. FRQ dominance: decoy (10,500 / $21.99) dominated by HD (11,076 / $19.99) on both; not
   dominated by HF (1,147 reviews). PASS.
2. RNG range: decoy (12,500) extends beyond HD (11,076); decoy not dominated by HD (decoy
   reviews higher). PASS.
3. PHT one attribute: rebuilt phantom (12,000 / $19.99) superior on reviews only; equal on
   price. available=false. PASS. (Published PHT-7 FAILED this check; rebuild applied.)
4. SOT compromise: two BIN options + EXTREME beyond HD; HD strictly between HF and EXTREME on
   both attributes. No free middle added. PASS. (V1 SOT-7 FAILED; rebuild applied.)
5. SYM double dominance: decoy (1,147 / $19.99) dominated by HF on price and by HD on
   reviews. PASS.
6. MOT tier identity: 3 distinct tiers; 4 near-identical brands per tier. PASS.
7. SIM non-dominance: clone (11,500 / $19.99) not dominated by HD (11,076 / $19.99) because
   clone reviews > HD reviews. PASS.
8. Cross-category geometry: all structures built by same relational rules as bluetooth_speakers.
   PASS.
9. No duplicates within any set. PASS.
10. Tier-1 fidelity: BIN, FRQ, RNG, MOT, SYM all use exact published V1 values. PHT reviews
    kept; PHT price rebuilt. SOT extreme is constructed (published SOT used wrong geometry).
    Tier-1 fidelity for published structures: PASS where possible; rebuilds flagged.
11. Single-source rule: this fragment is the source; no values hand-typed elsewhere.

---

## Rebuild summary

| Structure | Status | Note |
|-----------|--------|------|
| BIN | Exact published | All values from V1 web appendix BIN-7 |
| FRQ | Exact published | All values from V1 web appendix FRQ-7 |
| RNG | Exact published | All values from V1 web appendix RNG-7 |
| PHT | REBUILT (R1 violation) | Published phantom superior on BOTH attributes; rebuilt to reviews only superior; price $17.99 → $19.99 |
| SOT | REBUILT (old geometry) | V1 added middle; new plan requires extreme beyond HD; V1 middle discarded from SOT |
| MOT | Exact published | All values from V1 web appendix MOT-7 |
| SYM | Exact published | All values from V1 web appendix SYM-7 |
| SIM | Constructed | No published analog; minimal clone of HD |
