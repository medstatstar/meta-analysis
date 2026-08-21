# Dedup Search Workflow（去重检索流程）

> Grounding: PROSPERO (NIHR), Cochrane Library, PubMed/MEDLINE;
> PRISMA-S (Rethlefsen ML et al., 2021) search reporting guidance.
> ⚠️ **Network note**: this skill never auto-searches literature databases.
> Searches below are executed ONLY when the user opts in (and provides network
> confirmation) — otherwise deliver search-query templates for the user to run
> in their own browser, then backfill results into the report JSON.

## Purpose

Verify novelty (dimension 4 of topic-selection) and avoid the #1 reviewer
rejection reason: "duplicate / no increment". Run in **Stage 4** of the Full
assessment (and in Dedup re-review path).

## Three-layer dedup（三层去重）

Layer order is deliberate — registered protocols first, then ongoing, then
published.

| Layer | Database | What to check | Time window |
|---|---|---|---|
| 1 | **PROSPERO** (NIHR register) | Registered/recently completed systematic reviews on the same question | active + completed ≤24 months |
| 2 | **Cochrane Library** (CDSR) | Cochrane Reviews / protocols on the same question | any (Cochrane has priority) |
| 3 | **PubMed / MEDLINE** | Published meta-analyses / systematic reviews on the same question | last 5 years (extend if the field is slow-moving) |

**Non-English scope extension** (user opt-in; required when the population or
literature is partly non-English — e.g. Chinese herbal medicine, regional
reimbursement questions): CNKI / 万方 / 维普 / SinoMed.

## Search-query templates

Deliver these to the user (or execute on opt-in). Replace placeholders from
the PICO block (`pico-guide.md`):

```
# PubMed (E-utilities URL, opt-in only)
https://pubmed.ncbi.nlm.nih.gov/?term=(<P>)+AND+(<I>)+AND+(<C>)+AND+(meta-analysis[pt] OR systematic-review[pt])+AND+("2021/01/01"[dp]:"2026/12/31"[dp])

# PROSPERO (browser)
https://www.crd.york.ac.uk/prospero/#searchadvanced
  Query: <P> AND <I> AND <C>, filter = systematic review / meta-analysis, status = all

# Cochrane Library (browser)
https://www.cochranelibrary.com/search
  Query: <P> AND <I> AND <C>, content type = Cochrane Review, trials
```

## Near-duplicate judgment matrix（近似重复判断矩阵）

Not every same-question review is a duplicate. Classify each hit:

| Situation | Verdict | Reason |
|---|---|---|
| Same PICO, same type, similar time window | **Exact duplicate** → block | No increment; reviewer will reject |
| Same PICO, but substantially newer data / larger evidence base | **Near-duplicate, conditional** | Allowed only with documented increment (new trials, updated search, added subgroup) |
| Same population, different intervention (or vice versa) | **Class-substitution** → usually NOT duplicate | Different clinical question; say so explicitly in report |
| Same question, different meta type (pairwise → NMA / IPD) | **Not duplicate if type adds evidence** | Type upgrade can be an increment |
| Same question, only database/time window changed | **Usually duplicate** | Cosmetic change is not an increment |

## Increment assessment（创新增量判断）

For any existing review, assess **increment type** and **sufficiency**:

| Increment type | Sufficient? |
|---|---|
| New RCTs / IPD since last search (≥2 meaningful trials or major trial) | ✅ usually |
| Added outcome / subgroup / NMA / dose-response not in prior review | ✅ if clinically meaningful |
| Updated methods (e.g. 2015 review → PRISMA 2020 + RoB 2) | ⚠️ weak alone |
| Only re-run of same search | ❌ no |

**Increment statement** (mandatory in report): one paragraph saying what exists
and what THIS review adds — reviewers require this verbatim.

## Report fields (into JSON `dedup`)

```json
"dedup": {
  "prospero": "2 registered reviews found (CRD4202xxxxxx): same PICO — exact-dup risk",
  "cochrane": "1 Cochrane review in progress on PD-1 2nd-line NSCLC",
  "pubmed": "4 meta-analyses 2021-2026; 3 use older drug set, 1 includes all PD-1s (2024, 18 trials)",
  "non_english": "not applicable (English-language trial literature)",
  "near_duplicate": "near-dup vs 2024 meta (18 trials); increment = 3 new trials + PD-L1 subgroup not in prior review",
  "increment": "Adds 3 post-2024 trials and PD-L1 TPS subgroup analysis absent from the 2024 review"
}
```

## When dedup re-review is requested（被拒重复后复审）

Run **Stage 4 only**: re-run dedup layers, re-judge near/exact duplicate,
produce increment statement + verdict on whether re-submission is defensible.
Output = short re-review report (not the full 11 sections).
