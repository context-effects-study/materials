# The service that assigns scripts

The words, pictures and price-free surveys each assign 2,100 to 2,800 pre-built scripts of three choices. Qualtrics
cannot import a randomizer with more than about 2,500 elements, so this small web service (a Cloudflare Worker)
assigns these scripts. At the start of the survey, the survey calls `GET /assign?arm=<price-free|words|pictures>`.
The service returns the script of that survey that has been assigned least often so far (ties are broken at
random). The survey stores the fields of the script in embedded data and shows the three choice pages from them. The
pre-registered design does not change: the scripts are the same pre-built scripts, each is presented equally often,
and the rules against repeats within a person are the same as with a randomizer. The service only assigns scripts,
and it never receives responses or personal data.

## Files

| File | What it is |
|---|---|
| `src/worker.js` | The service. Its addresses are `/assign?arm=`, `/health` and `/stats` |
| `build_worker_data.py` | Builds the data of the service from `../deal.py` and `../generate_survey.py`: `src/scripts_data.js`, which holds the tables of scripts, compressed, and `src/manifest.json`, which gives the number of scripts, the number of choices and the hash of the script set for each survey. We do not deposit either file, and this script rebuilds both |

## Rebuild the data of the service

```
python surveys/assign_worker/build_worker_data.py
```

The hashes of the script sets in the new `src/manifest.json` must equal the hashes in `../out/*_MAPPING.json`, and
`run_all.py` checks this. To set up the service, add the two files to a Cloudflare Worker project and bind one
key-value store under the name `CFX_ASSIGN`, which holds a count for each script.

## How even the assignment is

For each survey, the service keeps a count for each script and assigns the script with the lowest count, which
presents every script equally often. The service updates the counts without a strict lock, and the key-value store
can take a short time to show an update in every location. Two calls at the same moment can therefore sometimes
receive the same script, and the counts can briefly differ between locations. Across thousands of participants,
this gives the same variation of a few percent that the simulation of participants who stop partway covers. The
rule for recruiting more participants (`../../docs/HUMAN_PROTOCOL.md`, section 4) restores the exact balance, because
it counts the completed responses in the export, never the service's counts.
