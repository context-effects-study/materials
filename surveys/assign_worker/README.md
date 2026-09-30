# The survey-assignment service

The words, pictures and price-free surveys each deal 2,100 to 2,800 pre-built scripts of three choices. A
Qualtrics survey cannot import a randomizer with more than about 2,500 elements, so these scripts are dealt
by this small service (a Cloudflare Worker) instead. At the start of the survey the survey calls
`GET /assign?arm=<price-free|words|pictures>`; the service returns the least-used script of that survey
(ties broken at random), and the survey stores its fields in embedded data and renders the three choice pages
from them. The registered design does not change: the same pre-built scripts, the same even presentation,
the same within-person no-repeat rule. The service assigns scripts only; it never receives responses or
personal data.

## Files

| File | What it is |
|---|---|
| `src/worker.js` | The service. Endpoints: `/assign?arm=`, `/health`, `/stats` |
| `build_worker_data.py` | Builds the service's data bundle (`src/scripts_data.js`, the script tables, compressed) and `src/manifest.json` (scripts, choices and deal hash per survey) from `../deal.py` and `../generate_survey.py`. Neither output is deposited; both are rebuilt by this script |

## Rebuild the data bundle

```
python surveys/assign_worker/build_worker_data.py
```

The deal hashes in the new `src/manifest.json` must equal the ones recorded in `../out/*_MAPPING.json`
(`run_all.py` checks this). To deploy the service, add the two files to a Cloudflare Worker project with one
key-value namespace bound as `CFX_ASSIGN`, which holds a count per script.

## Balance, and its limit

Per survey the service keeps a count per script and assigns the least-used one, which is even presentation
stated directly. The counts are updated without a hard lock and the key-value store is eventually
consistent, so two calls at the same instant can occasionally receive the same script, and counts can lag
briefly between locations. Across thousands of participants this gives the same few-percent variation the
design's dropout simulation covers, and exact balance is restored by the top-up rule
(`../../docs/HUMAN_PROTOCOL.md`, section 4), which counts completed responses in the export, never the
service's counts.
