"""run.py: the model runner. It sends the choice sets to the language models and logs every call.

For each call in the plan (models/build_manifest.py) it builds the prompt from stimuli/stimuli.json with
the same option text the human surveys show (render_shared.py, enrich.py), in the registered position
order (order_plan.py), paraphrase, format and prompting mode, sends it to the model's provider, parses the
chosen letter, decodes it with the codebook of its kind of choice set that the human data also use, and writes one record
per call (the fields are listed in analysis/DATA_DICTIONARY.md, part B): the full prompt, the raw reply,
the model id requested and the id the provider returned, the reasoning setting and the exact parameters sent for
it, the sampling settings actually applied, whether a choice could be read from the reply, any exclusion reason,
latency, cost and a timestamp. Every call is recorded, including refusals and unparseable replies. Each call has a
deterministic record id, so an interrupted run resumes where it stopped, and a cost cap stops the run cleanly.

The models, with exact model ids, routes, the parameters of each reasoning setting and the conditions each model
runs, are in models/model_registry.json, which this program reads, and in models/README.md. The models with open
weights run on a vLLM server at a pinned revision of their weights (the vllm route), and every one of their calls
records the revision the server loaded.

Modes:
  python models/run.py                        dry run (default): the whole loop on synthetic replies, no
                                              network; writes model_log.jsonl and SAMPLE_CALLS.jsonl
  python models/run.py --selftest             checks the registry and every request the runner would
                                              send, without network
  python models/run.py --live --max-calls N   real calls, capped
  --arm primary|crossed|ladder|temp_0|temp_1|persona|sequential|recognition
                                              which part of the plan to run (default primary); crossed and
                                              ladder run one reasoning setting at a time (--setting)
  --out-dir DIR                               dry run only: where to write the log

API keys are read from the environment only (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY or GEMINI_API_KEY,
XAI_API_KEY, MISTRAL_API_KEY, OPENROUTER_API_KEY; the vllm route reads VLLM_BASE_URL); none is stored in this
repository.
Manuscript: Method ("Language Models and Prompts").
"""
import json, os, sys, hashlib, re, time, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
# Layout: root = the nearest ancestor holding stimuli/
# (working repository: two levels up from models/; public deposit: one level up from models/).
def _find_root(start):
    d = start
    for _ in range(4):
        d = os.path.dirname(d)
        if os.path.isdir(os.path.join(d, "stimuli")):
            return d
    return os.path.abspath(os.path.join(start, "..", ".."))
_ROOT = _find_root(HERE)
STIM = os.path.join(_ROOT, "stimuli", "stimuli.json")
LOG_PATH = os.path.join(HERE, "model_log.jsonl")
SAMPLE_PATH = os.path.join(HERE, "SAMPLE_CALLS.jsonl")
sys.path.insert(0, os.path.dirname(HERE))        # working repository/engines on path
sys.path.insert(0, os.path.join(_ROOT, "stimuli"))  # enrich (final calibration lock; render_shared in the deposit)
from render_shared import render_value            # QSF-1: human + model share ONE option-text renderer
from order_plan import orders_for                 # ONE canonical order rule, shared with build_manifest.py
import enrich                                     # final calibration lock: the ONE enrichment resolution rule (QSF-1 parity)
LETTERS = "ABCDEFGHIJKL"

_ENRICHMENT_CACHE = None

def enrichment_block():
    """The canonical enrichment block from stimuli.json (final calibration lock, 2026-07-02). Lazy-loaded once;
    the SAME entries the human cards render, resolved by the SAME rule (enrich.entry_for)."""
    global _ENRICHMENT_CACHE
    if _ENRICHMENT_CACHE is None:
        _ENRICHMENT_CACHE = json.load(open(STIM, encoding="utf-8")).get("enrichment") or {}
    return _ENRICHMENT_CACHE
# Dry-run uses a FIXED timestamp so two dry-runs produce a byte-identical model_log.jsonl. Live runs
# pass timestamp=None and get the real wall clock; this constant is dry-run only.
DRY_RUN_TIMESTAMP = "1970-01-01T00:00:00Z"

# ===================================================================================================
# REGISTERED PROMPT MATERIALS. This constant is the
# canonical copy; prompt_materials.json beside this file is the published copy the runner READS, and the
# runner refuses to start if the two differ in any character (so neither can drift alone). Regenerate the
# JSON only from this constant: python run.py --write-materials
# ===================================================================================================
REGISTERED_PROMPT_MATERIALS = {
    "registered_on": "2026-09-29",
    # 3 registered paraphrase FRAMES (the registered variation plan). {product} = the category's product phrase WITH its
    # article, taken from the participants' own question wording (product_phrases below). Amended 2026-09-29 by
    # the authors: the June frames hard-coded "a {noun}", which produced "a earbud", "a electric kettle"
    # and "a external hard drive".
    "paraphrase_frames": {
        "1": "Imagine you are {verb} {product}.{explanation} You are considering the following options:",
        "2": "You are choosing {product} {purpose}.{explanation} The available options are:",
        "3": "Choose {product} from these options:{explanation}",
    },
    # {explanation}: the explanatory text the participants' question carries
    # for six categories (earbuds, restaurants, televisions and the three price-free variants), read at build
    # time from the stimulus's own registered survey stem (the text between the product sentence and "You are
    # considering the following options"), so the two cannot drift; empty for the other seven. Joined as
    # below: in frames 1 and 2 it follows the product sentence and precedes the sentence introducing the
    # options, exactly where the participants read it; frame 3's single sentence both names the product and
    # introduces the options, so the explanation follows it on its own line, just before the options (placed
    # before it, the price-free sentences' "Each is rated ..." would come before the product is named).
    "explanation_joiners": {"1": " ", "2": " ", "3": "\n"},
    # the ten product phrases, each copied from the human survey stem of that category (the stems in
    # stimuli.json that the surveys show); a price-free variant uses its base category's phrase
    "product_phrases": {
        "backpacks": "a backpack",
        "bluetooth_speakers": "a Bluetooth speaker",
        "earbuds": "wireless earbuds",
        "electric_kettles": "an electric kettle",
        "hard_drives": "an external hard drive",
        "restaurants": "a restaurant",
        "robot_vacuums": "a robot vacuum",
        "standing_desks": "a standing desk",
        "televisions": "a 40-inch television",
        "water_bottles": "a reusable water bottle",
    },
    # frame 1's verb, as the participants' question has it: restaurants read
    # "choosing a restaurant", every other category "shopping for ..."
    "frame_verbs": {"default": "shopping for", "restaurants": "choosing"},
    # frame 2's purpose phrase: "to eat at" for restaurants, "to purchase"
    # otherwise; frames 2 and 3 of the other nine categories were read and left unchanged
    "frame_2_purposes": {"default": "to purchase", "restaurants": "to eat at"},
    "response_instruction": "Reply with ONLY the letter of your choice.",
    # persona sentence + one space + the frame, in the same (first) line of the single user message
    "personas": {
        "P01": "You are a 22-year-old university student from Manchester shopping on a tight budget.",
        "P02": "You are a 27-year-old nurse from Texas shopping on a moderate budget.",
        "P03": "You are a 31-year-old software developer from California shopping on a comfortable budget.",
        "P04": "You are a 45-year-old office manager from Leeds shopping on a moderate budget.",
        "P05": "You are a 58-year-old retired police officer from Florida shopping on a moderate budget.",
        "P06": "You are a 39-year-old stay-at-home parent from Georgia shopping on a tight budget.",
        "P07": "You are a 34-year-old teacher from Ohio shopping on a moderate budget.",
        "P08": "You are a 63-year-old retired accountant from Bristol shopping on a comfortable budget.",
        "P09": "You are a 25-year-old barista from Oregon shopping on a tight budget.",
        "P10": "You are a 50-year-old truck driver from Missouri shopping on a moderate budget.",
        "P11": "You are a 29-year-old marketing assistant from London shopping on a moderate budget.",
        "P12": "You are a 42-year-old electrician from Pennsylvania shopping on a moderate budget.",
        "P13": "You are a 36-year-old pharmacist from Illinois shopping on a comfortable budget.",
        "P14": "You are a 70-year-old retired schoolteacher from Glasgow shopping on a tight budget.",
        "P15": "You are a 19-year-old part-time retail worker from Arizona shopping on a tight budget.",
        "P16": "You are a 47-year-old small-business owner from New York shopping on a comfortable budget.",
        "P17": "You are a 33-year-old warehouse supervisor from Birmingham shopping on a moderate budget.",
        "P18": "You are a 55-year-old administrative assistant from North Carolina shopping on a moderate budget.",
        "P19": "You are a 38-year-old civil engineer from Washington State shopping on a comfortable budget.",
        "P20": "You are a 66-year-old retired factory worker from Cardiff shopping on a tight budget.",
    },
    # three calls per stimulus; [option lines] = the behavioral prompt's option lines (numbers format), one per
    # line, exactly as the behavioral prompt shows them; call k shows them in registered order k (k = 1, 2, 3;
    # a two-option set has two orders, so its third call repeats order 1). authors rule 2026-09-29.
    "recognition_probe": (
        "Here is a set of product options a shopper is choosing from:\n"
        "[option lines]\n"
        "Question 1: Is anything about this set of options strategically constructed to influence which "
        "option a shopper chooses? Answer YES or NO.\n"
        "Question 2: If you answered YES, which option was added mainly to make another option look better "
        "or worse? Answer with its letter, or NONE.\n"
        "Reply in exactly this format: 1: YES or NO; 2: a letter or NONE"),
    # first user message = this sentence + a blank line + the first neutral prompt; each later decision is
    # the next neutral prompt as a new user message in the same conversation, earlier answers left in place
    "sequential_opening": ("You will make seven separate shopping decisions, one at a time. For each one, "
                           "choose the option you would buy."),
    "sequential_opening_separator": "\n\n",
    # the picture each image-capable model receives = the PNG the participants see (byte-identical to the
    # survey host's copy, checked 2026-09-29), a 2x render of the registered SVG; recorded by SHA-256
    "picture_files": {
        "BIN_bluetooth_speakers_t2.svg": ["BIN_bluetooth_speakers_t2.png", "8924fb4c8f8416758481c12a9a1f544081cfb72153841291aa756d2a9dd1cabf"],
        "BIN_televisions_t2.svg": ["BIN_televisions_t2.png", "4fee3af21409aef37595ae4d07e1e2102726bda7530c99679b0306170ce8a8d4"],
        "BIN_water_bottles_t2.svg": ["BIN_water_bottles_t2.png", "2c3b62f4205451b558231beb1c9da8ac83b388587f85fef57568befb128a6d0e"],
        "FRQ_bluetooth_speakers_t2.svg": ["FRQ_bluetooth_speakers_t2.png", "e5a58a60bdc13e678d7edfa01bfbc001965850f9a68257ae5702b3faef318009"],
        "FRQ_televisions_t2.svg": ["FRQ_televisions_t2.png", "854e9f7b8fb68b4fe039cae3610f4d88a58be2334eb63ca011a7422d62653f31"],
        "FRQ_water_bottles_t2.svg": ["FRQ_water_bottles_t2.png", "883c0d8c724e7a6dc8c4ddbe2c76620d96146e7ff842cbf34c8a3e5f85db89ef"],
        "SOT_bluetooth_speakers_t2.svg": ["SOT_bluetooth_speakers_t2.png", "4fb137d7412f51e8567bcd73ef1351a226ecd682059f22a9e0758736d4ecf5ad"],
        "SOT_televisions_t2.svg": ["SOT_televisions_t2.png", "608b710506c6b9c93335b78a09fdb75df46d98e5e2e9ccfcdfa980124f0957d6"],
        "SOT_water_bottles_t2.svg": ["SOT_water_bottles_t2.png", "fd722a4591efa474eb8b8458961b2f8ba6eac93d9c2b2e641d6d3d2f4fadba91"],
    },
}
MATERIALS_PATH = os.path.join(HERE, "prompt_materials.json")

def load_prompt_materials(path=MATERIALS_PATH):
    """Read the published materials file and refuse on ANY difference from the registered constant."""
    if not os.path.exists(path):
        sys.exit(f"[run] {os.path.basename(path)} is missing; regenerate it with: python run.py --write-materials")
    got = json.load(open(path, encoding="utf-8"))
    if got != REGISTERED_PROMPT_MATERIALS:
        diff = sorted(k for k in set(got) | set(REGISTERED_PROMPT_MATERIALS)
                      if got.get(k) != REGISTERED_PROMPT_MATERIALS.get(k))
        sys.exit(f"[run] REFUSING: {os.path.basename(path)} differs from the registered materials in {diff}. "
                 "The registered text lives in run.py; regenerate the file with --write-materials.")
    return got

def write_prompt_materials(path=MATERIALS_PATH):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(REGISTERED_PROMPT_MATERIALS, f, ensure_ascii=False, indent=1)
        f.write("\n")

_M = REGISTERED_PROMPT_MATERIALS
PARAPHRASES = {int(k): v for k, v in _M["paraphrase_frames"].items()}
PRODUCT_PHRASES = dict(_M["product_phrases"])
FRAME_VERBS = dict(_M["frame_verbs"])
FRAME_2_PURPOSES = dict(_M["frame_2_purposes"])
EXPLANATION_JOINERS = dict(_M["explanation_joiners"])
RESP = _M["response_instruction"]
PERSONAS = dict(_M["personas"])
PROBE_TEMPLATE = _M["recognition_probe"]
SEQUENTIAL_OPENING = _M["sequential_opening"]
SEQUENTIAL_SEPARATOR = _M["sequential_opening_separator"]
PICTURE_FILES = {k: tuple(v) for k, v in _M["picture_files"].items()}

def _first_existing(*cands):
    for c in cands:
        if os.path.exists(c):
            return c
    return cands[0]
# working repository layout: surveys/...; public deposit layout: surveys/...
_HQ = _first_existing(os.path.join(_ROOT, "engines", "human_qualtrics"), os.path.join(_ROOT, "surveys"))
PNG_DIR = os.path.join(_HQ, "png")
SCRIPTSET_PATH = os.path.join(_HQ, "scriptset_180.csv")
BACKBONE_MAPPING_PATH = os.path.join(_HQ, "out", "backbone_MAPPING.json")

# ===================================================================================================
# MODEL REGISTRY (the roster of 2026-11-24: 106 models in three groups). The registry is DATA:
# model_registry.json beside this file, written by the authors' registry builder from the roster files and the cost plan (the only
# statement of the rules), so this runner never restates a count or a draw. One entry per model; the key is the
# roster's key. The fields:
#   slot, developer, model_name, group ("closed_current" | "closed_previous" | "open"), tier (flagship, mid, small,
#       large), price_tier (premium, standard, budget; cost_plan.price_tier), family (the developer) and generation
#       ("new" | "old") for the comparison of older and newer models, generation_label, release.
#   route         openai | anthropic | google | xai | mistral (the developers' own APIs, with batch) | openrouter
#                 (pinned to the developer's own host: provider_pin, require_parameters, no fallback) | vllm (the open
#                 models on a university supercomputer, at hf_revision). api_id is the developer's id; model_id is the id sent on the
#                 route. Keys come from the environment only (ROUTE_KEYS).
#   levels, settings  the common settings the model offers (OFF, LOW, DEFAULT, HIGH, MAX) and, for each, the exact
#                 request parameters ({} sends nothing, so the provider's default runs).
#   max_tokens    the output ceiling of each setting (hidden reasoning counts toward it on every route).
#   plan          the conditions the model runs: primary (its setting and draws), crossed and ladder (each setting
#                 with its draws), persona and temperature (True or False). cost_plan.py's conditions().
#   accepts_temperature / rejects_temperature, temperature (None: the provider's default in every arm but the two
#                 temperature arms).
#   unconfirmed   the values that the web search or an earlier proven run did not confirm: the checks for the pre-test
#                 calls before data collection.
#   substitute    the registered substitute (GLM-5.3 for GLM-5.4 while GLM-5.4 has no public API).
#
# REGISTERED SUBSTITUTION RULE (by role; Web Appendix D states it in full). Each model is defined by its role:
# developer, group, tier, reasoning controls, image input and, for an open model, its weights at the pinned revision.
# The rule is applied ONCE, when Stage 2 collection starts and before any data are seen. If a closed model is retired,
# cannot be reached on its registered route, or is served only under an alias that its developer documents as moving,
# its place is filled by the first candidate in this order that meets the whole role: (1) the same model under a dated
# snapshot id; (2) the same model on OpenRouter, pinned to the developer's own host; (3) the replacement that the
# developer names in its deprecation notice; (4) the same developer's model in the same line whose release date is
# closest (ties go to the older); (5) else the model runs empty and is reported as empty. An open model is never
# substituted: its weights at the pinned revision stay available. The substitute's entry gets
# substituted_from=(planned id, reason, date), which every call row carries.
# ===================================================================================================
REGISTRY_PATH = os.path.join(HERE, "model_registry.json")
SETTINGS = ("OFF", "LOW", "DEFAULT", "HIGH", "MAX")


def load_registry(path=REGISTRY_PATH):
    """The registry from model_registry.json: lists become tuples where the runner compares them."""
    doc = json.load(open(path, encoding="utf-8"))
    reg = {}
    for k, m in doc["models"].items():
        m = dict(m)
        m["hf_revision"] = tuple(m["hf_revision"]) if m.get("hf_revision") else None
        m["price_per_1m"] = tuple(m["price_per_1m"])
        m["echo_ids"] = tuple(m.get("echo_ids") or ())
        if m.get("substituted_from"):
            m["substituted_from"] = tuple(m["substituted_from"])
        reg[k] = m
    return reg, doc.get("roster_date", "")


MODEL_REGISTRY, IDS_VERIFIED_ON = load_registry()
PRIMARY_LINEUP = list(MODEL_REGISTRY.keys())

# The arms. primary, crossed and ladder run the neutral grid at one setting each; persona, the two temperature arms,
# sequential and recognition run at the model's primary setting. A crossed or ladder arm runs ONE setting at a time
# (--setting), and the setting is part of its record_id and of its log file's name.
ARMS = ("primary", "crossed", "ladder", "temp_0", "temp_1", "persona", "sequential", "recognition")
SETTING_ARMS = ("crossed", "ladder")
ARM_TEMPERATURE = {"temp_0": 0.0, "temp_1": 1.0}
# prompting_mode per arm (CONTRACTS B enum). The neutral arms re-run the neutral grid; analyze.py keeps only the
# primary arm's neutral rows in the confirmatory estimates (split_arms), and each arm writes its own log file.
ARM_MODE = {"primary": "neutral", "crossed": "neutral", "ladder": "neutral", "temp_0": "neutral", "temp_1": "neutral",
            "persona": "persona", "sequential": "sequential", "recognition": "recognition"}
SEQ_SESSIONS, SEQ_LEN = 1000, 7          # build_manifest SEQ_SESSIONS; seven decisions per session
NEUTRAL_ARMS = ("primary", "crossed", "ladder", "temp_0", "temp_1")   # the arms that re-run the neutral grid

# ===================================================================================================
# REPEATED DRAWS. At the provider's default temperature each call is one random draw from the model's answers, so a
# grid point of the primary, crossed and ladder arms is called more than once: the number for each model and setting
# is in its registry plan (cost_plan.py's DRAWS by price tier: budget 10, 5 and 2; standard and premium 10 and 1),
# and a picture prompt is called six times as often, so a pictures cell (1 order x 3 frames) carries as many calls as
# a three-option numbers cell (6 orders x 3 frames). Persona, temperature, sequential and recognition call every grid
# point once. Each draw is a separate API call with no conversation history. The draw is part of the record_id (draw
# 0 keeps the form without it), so a resume never treats draw k as done because draw 0 is. The plan is DRAW-MAJOR
# within each model: the whole grid at draw 0, then the whole grid at draw 1, and so on (picture prompts continue
# alone after the text draws), so a capped or interrupted run always holds complete grids of its earlier draws.
# ===================================================================================================
def arm_settings(model_key, arm):
    """The settings one model runs in one arm, in its plan's order ([] when the model does not run the arm)."""
    p = MODEL_REGISTRY[model_key]["plan"]
    if arm in SETTING_ARMS:
        return [c["setting"] for c in p[arm]]
    if arm == "persona" and not p["persona"]:
        return []
    if arm in ARM_TEMPERATURE and not p["temperature"]:
        return []
    return [p["primary"]["setting"]]


def setting_for(model_key, arm, setting=None):
    """The one setting a call of this arm runs at. A crossed or ladder arm needs its setting named."""
    allowed = arm_settings(model_key, arm)
    if arm in SETTING_ARMS:
        if setting not in allowed:
            raise ValueError(f"{model_key} does not run {arm} at {setting!r}; it runs {allowed}")
        return setting
    if not allowed:
        raise ValueError(f"{model_key} is not registered for the {arm} arm")
    if setting not in (None, allowed[0]):
        raise ValueError(f"{model_key}: the {arm} arm runs at the primary setting {allowed[0]}, not {setting!r}")
    return allowed[0]


def draws_for(arm, fmt, model_key, setting=None):
    """Registered calls per grid point for one model, arm, setting and delivery format (1 in the arms that do not
    repeat)."""
    p = MODEL_REGISTRY[model_key]["plan"]
    pic = fmt.split(":")[0] == "pictures"
    if arm == "primary":
        c = p["primary"]
    elif arm in SETTING_ARMS:
        c = next(x for x in p[arm] if x["setting"] == setting_for(model_key, arm, setting))
    else:
        return 1
    return c["picture_draws"] if pic else c["draws"]


def models_for_arm(arm, setting=None):
    """The registry keys an arm runs on (with setting, a crossed or ladder arm's models at that setting)."""
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}; valid: {ARMS}")
    keys = [k for k in PRIMARY_LINEUP if arm_settings(k, arm)]
    if setting is not None and arm in SETTING_ARMS:
        keys = [k for k in keys if setting in arm_settings(k, arm)]
    return keys

def product_phrase(cat):
    """The category's product phrase with its article, from the registered table (copied from the human survey
    stems). A price-free variant uses its base category's phrase. Replaces the June noun_for(), whose
    'a {noun}' frames produced 'a earbud' (2026-09-29)."""
    return PRODUCT_PHRASES[cat.get("price_free_variant_of") or cat["id"]]

def frame_verb(cat):
    """Frame 1's verb for the category: 'choosing' for restaurants, 'shopping for' otherwise (registered)."""
    return FRAME_VERBS.get(cat.get("price_free_variant_of") or cat["id"], FRAME_VERBS["default"])

def frame_purpose(cat):
    """Frame 2's purpose phrase: 'to eat at' for restaurants, 'to purchase' otherwise (registered)."""
    return FRAME_2_PURPOSES.get(cat.get("price_free_variant_of") or cat["id"], FRAME_2_PURPOSES["default"])

_STEM_EXPLANATION = re.compile(
    r"^Imagine you are (?:shopping for|choosing) [^.]*\.\s+(?P<expl>.*?)\s*You are considering the following options[.:]")

def stem_explanation(stim):
    """The explanatory text of the participants' question for this stimulus, verbatim from its registered
    survey stem (stimuli.json 'stem'): everything between the product sentence and 'You are considering the
    following options'. Empty when the stem has none. Refuses a stem not in the registered form."""
    m = _STEM_EXPLANATION.match(stim.get("stem") or "")
    if not m:
        raise ValueError(f"{stim.get('id')}: stem is not in the registered form: {stim.get('stem')!r}")
    return m.group("expl").strip()

def frame_head(pid, cat, stim=None):
    """The rendered frame for one category (frame 1 takes the verb, frame 2 the purpose) and, given the
    stimulus, the participants' explanatory text in its registered place (a second line in frame 3)."""
    expl = stem_explanation(stim) if stim is not None else ""
    joined = (EXPLANATION_JOINERS[str(pid)] + expl) if expl else ""
    return PARAPHRASES[pid].format(product=product_phrase(cat), verb=frame_verb(cat), purpose=frame_purpose(cat),
                                   explanation=joined)

OPTION_LINE = re.compile(r"^\s+[A-L]\. ")

def split_head(prompt):
    """(head, rest) of a choice prompt: head = every line before the first option line (the frame, and its
    explanation line in frame 3), rest = the option lines and the response instruction."""
    lines = prompt.split("\n")
    k = next(i for i, l in enumerate(lines) if OPTION_LINE.match(l))
    return "\n".join(lines[:k]), "\n".join(lines[k:])

def option_line(letter, opt, attrs_meta, fmt, words=None, entry=None):
    """Render one option. numbers: 'A. 40 L capacity, $39.99'; words: spelled out; pictures: image ref.
    final calibration lock (2026-07-02): when `entry` carries the option's enrichment (adjustable tiers, the calibrated
    structure family), the line is the ENRICHED blurb - the model name, then each attribute's canonical
    value string followed by its qualifier in parentheses - the same names, values (render_value,
    verbatim), and qualifiers the human card shows (QSF-1 parity). Pictures lines stay an image pointer
    (the enriched image itself carries the names and qualifiers)."""
    if fmt == "pictures":
        return f"  {letter}. (see image: bars show each attribute's magnitude)"
    parts = []
    for a in attrs_meta:
        n = a["name"]; v = opt["attrs"].get(n)
        if v is None:
            continue
        val = (words.get(n, str(v)) if (fmt == "words" and words)
               else render_value(n, a.get("unit", ""), v))
        if entry is not None:
            val = f"{val} ({entry['qualifiers'][n]})"
        parts.append(val)
    tag = " (currently unavailable)" if not opt.get("available", True) else ""
    name = f"{entry['name']} - " if entry is not None else ""
    return f"  {letter}. " + name + ", ".join(parts) + tag

def build_prompt(stim, cat, order, paraphrase_id, fmt, opts, words_map=None, persona_prefix=""):
    """Assemble the full prompt text for one call. `order` is a tuple of option indices.
    Returns (prompt_text, shown_codes) where shown_codes[k] is the option code at displayed letter k."""
    head = frame_head(paraphrase_id, cat, stim)
    shown = [opts[i] for i in order]
    lines = [persona_prefix + head]
    enr = enrichment_block()
    for k, o in enumerate(shown):
        w = (words_map or {}).get(o.get("code")) if fmt == "words" else None
        entry = enrich.entry_for(enr, stim, o) if fmt != "pictures" else None
        lines.append(option_line(LETTERS[k], o, cat["attributes"], fmt, w, entry=entry))
    lines.append(RESP)
    return "\n".join(lines), [o.get("code") for o in shown]

def deliveries(stim):
    """Yield (format_label, options, words_map, image) delivery forms for a stimulus.
    format_label may carry a SIM placement suffix ('numbers:clone_HD'); the bare format is label.split(':')[0].
    final calibration lock (2026-07-02): the pictures delivery uses the variant's OWN `options` when present (the two
    per-format-locked pictures cells carry different values than the numbers row; the exited
    hard-drives pictures variant is absent from stimuli.json, so no pictures delivery exists there)."""
    yield ("numbers", stim["options"], None, None)
    fv = stim.get("format_variants") or {}
    if "words" in fv:
        wmap = {w["code"]: w["words"] for w in fv["words"]}
        yield ("words", stim["options"], wmap, None)
    if "pictures" in fv:
        yield ("pictures", fv["pictures"].get("options") or stim["options"], None, fv["pictures"])
    for pname, pv in (stim.get("placement_variants") or {}).items():
        yield (f"numbers:{pname}", pv["options"], None, None)

# ===================================================================================================
# CODEBOOK DECODER (mirrors human_qualtrics/ingest.py decode(); DATA_DICTIONARY.md A ).
# The model replies with a LETTER. We map the letter to the option CODE it stands for (via shown_codes),
# then map that code to the contract-B parsed_choice the analysis engine reads. analyze.model_derive_target
# expects: TARGET/COMP for BIN; TARGET/COMP/<decoy> for FRQ/RNG/PHT/SIM/SOT; HD/HF/DECOY for SYM; the
# menu-tier slot code Tn Sk for MOT; EXC_H/EXC_M/EXC_L for EXC. SOT's new extreme is labelled "EXT"
# (analyze excludes parsed_choice=="EXT" from the relative-share denominator). PHANTOM is invalid-by-design
# (unavailable) - if ever decoded it is routed to exclusions, never a choice.
# ===================================================================================================
DECOY_CODES = {"FRQ": "DECOY", "RNG": "RANGE_DECOY", "PHT": "PHANTOM", "SYM": "SYM_DECOY",
               "SIM": "CLONE", "SOT": "EXTREME"}
MOT_TIER = {"High": 1, "Middle": 2, "Low": 3}   # menu-quality tier -> Tn index for the slot code

def cat_target_focal_map(stimuli):
    """BIN has no target field; the BIN target focal is the category's decoy-target code, shared with its
    decoy cells (ingest.load_stimuli does the identical thing)."""
    m = {}
    for s in stimuli:
        if s["structure"] != "BIN" and s.get("target"):
            m.setdefault(s["category"], s["target"])
    return m

def _mot_slot_codes(opts):
    """Stable Tn Sk label per MOT option code, by walking the menu and numbering slots within each tier."""
    counters = {1: 0, 2: 0, 3: 0}
    out = {}
    for o in opts:
        ti = MOT_TIER.get(o.get("tier", ""), 2)
        counters[ti] += 1
        out[o["code"]] = f"T{ti}S{counters[ti]}"
    return out

def sim_placement_of(stim, fmt):
    """The similarity clone placement of one delivery: the placement named in the delivery label
    ('numbers:clone_HD'), else the base stimulus's own placement (stimuli.json sim_placement, clone_HF).
    None for every other structure. Written on every similarity record as sim_placement (analyze.py reads it)."""
    if stim.get("structure") != "SIM":
        return None
    return fmt.split(":", 1)[1] if ":" in fmt else stim.get("sim_placement", "clone_HF")

def decode_choice(structure, code, stim, opts, cat_target_focal, placement=None):
    """Map a chosen option CODE to (parsed_choice, valid). valid=False -> exclusion (phantom/impossible).
    `opts` is the placement-resolved option list actually shown for this delivery. Mirrors ingest.decode()
    but emits the MODEL codebook analyze.model_derive_target reads (SOT extreme -> 'EXT', MOT -> Tn Sk).
    FIX 2026-09-29: a similarity delivery is
    decoded against ITS OWN placement's target and competitor. The clone_HD placement swaps them (target HF,
    competitor HD against the base clone_HF's target HD, competitor HF); decoding it with the base pair, as
    this function did before, coded half the model similarity records against the wrong option, so the
    model similarity effect cancelled toward zero. Mirrors ingest.option_set()."""
    by_code = {o["code"]: o for o in opts}
    if code not in by_code:
        return ("INVALID", False)
    if structure == "BIN":
        tf = cat_target_focal.get(stim["category"])
        return ("TARGET" if code == tf else "COMP", True)
    if structure == "MOT":
        return (_mot_slot_codes(opts).get(code, "T2S1"), True)
    if structure == "EXC":
        return (code, True)                                # EXC_H / EXC_M / EXC_L
    if structure == "PHT" and code == DECOY_CODES["PHT"]:
        return ("PHANTOM", False)                          # unavailable-by-design -> exclusion accounting
    if structure == "SYM":
        # SYM is scored on the HD share (the upscaling statistic), NOT TARGET/COMP. The codebook values
        # are HD / HF / DECOY (CONTRACTS A), and analyze.model_derive_target reads parsed_choice=="HD".
        # The decoy code is SYM_DECOY -> the codebook 'DECOY'.
        if code == "HD":
            return ("HD", True)
        if code == "HF":
            return ("HF", True)
        return ("DECOY", True)
    target, competitor = stim.get("target"), stim.get("competitor")
    if structure == "SIM" and placement:
        pv = (stim.get("placement_variants") or {}).get(placement)
        if pv is not None:                                 # the placement's own pair (clone_HD swaps them)
            target, competitor = pv["target"], pv["competitor"]
    if code == target:
        return ("TARGET", True)
    if code == competitor:
        return ("COMP", True)
    if structure == "SOT" and code == "EXTREME":
        return ("EXT", True)                               # the NEW extreme; analyze drops EXT from the denom
    if structure == "SIM" and code == "CLONE":
        return ("CLONE", True)
    return (DECOY_CODES.get(structure, "DECOY"), True)

def parse_letter(raw, n_shown):
    """Parse the chosen letter from a model reply. Returns (letter or None, parse_method).
    parse_method: 'exact' (clean single-letter), 'fallback_regex' (letter found in noisier text),
    'failed' (no letter / refusal). A refusal is a parse failure flagged separately upstream."""
    if not raw or not raw.strip():
        return None, "failed"
    up = raw.strip().upper()
    rng = "A-" + LETTERS[n_shown - 1]
    # exact: the reply IS a single valid letter (optionally with trailing punctuation)
    if re.fullmatch(rf"[{rng}][.). ]*", up):
        return up[0], "exact"
    # fallback: a valid letter appears as a standalone token somewhere in the text
    m = re.search(rf"\b([{rng}])\b", up)
    if m:
        return m.group(1), "fallback_regex"
    return None, "failed"

REFUSAL_MARKERS = ("cannot", "can't", "as an ai", "i don't", "i do not", "unable to",
                   "i'm sorry", "i am sorry", "it depends")

def looks_like_refusal(raw):
    return bool(raw) and any(mk in raw.lower() for mk in REFUSAL_MARKERS)

# ---------------------------------------------------------------------------------------------------
# RECOGNITION PROBE: parser and score. The registered reply format is "1: YES or NO; 2: a letter or NONE".
# parse_probe returns (q1, q2, parse_method): q1 in {"YES","NO"}, q2 a shown letter or "NONE".
#   exact           the whole reply is the format (case-insensitive; spaces, a trailing period, and a
#                   newline in place of the semicolon tolerated)
#   fallback_regex  both answers found as "1: ..." and "2: ..." inside a longer reply
#   failed          either answer missing, not in its allowed set, or a letter outside the shown options
# ---------------------------------------------------------------------------------------------------
_PROBE_EXACT = re.compile(r"\s*1\s*:\s*(YES|NO)\s*[;,\n]\s*2\s*:\s*([A-Z]|NONE)\s*\.?\s*", re.I)
_PROBE_Q1 = re.compile(r"(?:^|[^0-9A-Za-z])1\s*[:.)]\s*(YES|NO)\b", re.I)
_PROBE_Q2 = re.compile(r"(?:^|[^0-9A-Za-z])2\s*[:.)]\s*(NONE|[A-Z])\b", re.I)

def parse_probe(raw, n_shown):
    if not raw or not raw.strip():
        return None, None, "failed"
    valid = set(LETTERS[:n_shown]) | {"NONE"}
    m = _PROBE_EXACT.fullmatch(raw)
    if m:
        q1, q2 = m.group(1).upper(), m.group(2).upper()
        return (q1, q2, "exact") if q2 in valid else (None, None, "failed")
    m1, m2 = _PROBE_Q1.search(raw), _PROBE_Q2.search(raw)
    if m1 and m2:
        q1, q2 = m1.group(1).upper(), m2.group(1).upper()
        return (q1, q2, "fallback_regex") if q2 in valid else (None, None, "failed")
    return None, None, "failed"

# The added option each structure is built with (the registered recognition rule, see score_probe). MOT, BIN
# and EXC have no single added option: question 1 = YES suffices there.
PROBE_SINGLE_ADDED = {"FRQ": "DECOY", "RNG": "RANGE_DECOY", "PHT": "PHANTOM", "SYM": "SYM_DECOY",
                      "SIM": "CLONE", "SOT": "EXTREME"}

def recognition_rate(rows, stimulus_id):
    """A stimulus's recognition rate under the registered rule: the share of its non-excluded probe calls
    (prompting_mode recognition) with recognition == 1. None when it has no scoreable probe call."""
    scored = [r["recognition"] for r in rows if r.get("prompting_mode") == "recognition"
              and r.get("stimulus_id") == stimulus_id and r.get("recognition") is not None]
    return (sum(scored) / len(scored)) if scored else None

def score_probe(structure, q1, q2, shown_codes):
    """The logged probe fields for one parsed reply, under THE REGISTERED RECOGNITION RULE:

      A probe call RECOGNIZES the manipulation (recognition = 1) when question 1 is YES and question 2 names
      the added option of that structure: the decoy for attraction (FRQ, code DECOY) and range (RNG, code
      RANGE_DECOY), the phantom for PHT (PHANTOM), the new extreme for compromise (SOT, EXTREME), the
      symmetric decoy for upscaling (SYM, SYM_DECOY), the clone for similarity (SIM, CLONE). For the
      extremity menu (MOT), which has no single added option, question 1 = YES suffices. Otherwise
      recognition = 0; an unparseable or refused probe gets recognition = None and is an exclusion.
      A stimulus's RECOGNITION RATE is the share of its (non-excluded) probe calls that recognize: three
      calls per stimulus, one per registered order. The "knows it" CUTOFF is the one in the analysis
      constants (analysis/registered_constants.py, RECOGNITION_CUTOFF; 0.50 when this was written),
      applied to that rate. Not used by the T2 test: the binary control (BIN) and the extremity control (EXC)
      also score YES alone, and are logged only for completeness.

    The two parts are logged separately (probe_q1_yes, probe_named_added_option) beside recognition.
    probe_inconsistent marks NO together with a letter (scored 0)."""
    q2_code = shown_codes[LETTERS.index(q2)] if (q2 and q2 != "NONE") else None
    added = PROBE_SINGLE_ADDED.get(structure)
    named = (q2_code == added) if added else None
    yes = (q1 == "YES")
    recognition = int(yes and (named if added else True))
    return {"probe_q1": q1, "probe_q2": q2, "probe_q2_code": q2_code, "probe_q1_yes": yes,
            "probe_added_option_code": added, "probe_named_added_option": named,
            "probe_inconsistent": (q1 == "NO" and q2 not in (None, "NONE")), "recognition": recognition}

def record_id(run_id, model_key, stim_id, fmt, order, pid, mode, persona, arm="primary", session=None,
              draw_index=0, setting=None):
    # The primary arm keeps the original hash input; every other arm appends its name, and a crossed or ladder arm
    # also its setting, so no two arms or settings collide on resume. A sequential call also appends its session and
    # position (the same cell can recur across sessions). A repeated draw appends its draw index; draw 0 keeps the
    # input without it.
    raw = f"{run_id}|{model_key}|{stim_id}|{fmt}|{order}|{pid}|{mode}|{persona}"
    if arm != "primary":
        raw += f"|{arm}"
    if arm in SETTING_ARMS:
        if setting not in SETTINGS:
            raise ValueError(f"a {arm} call needs its setting in its record_id (got {setting!r})")
        raw += f"|{setting}"
    if session:
        raw += f"|S{session['session']}|T{session['seq_index']}"
    if draw_index:
        raw += f"|D{draw_index}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16]

def spec_record_id(run_id, spec):
    return record_id(run_id, spec["model_key"], spec["stim"]["id"], spec["fmt"], spec["order"], spec["pid"],
                     spec["mode"], spec["persona"], spec["arm"], spec.get("session"), spec["draw_index"],
                     spec.get("setting"))

def has_reasoning(reg):
    """False only for a model with no reasoning mode at all (an open model that offers OFF alone)."""
    return not (reg["levels"] == ["OFF"] and reg["group"] == "open")

def needs_exact_reply(reg):
    """True for an open model that reasons and has no vLLM reasoning parser: only a reply that the exact pattern reads
    counts."""
    return reg["route"] == "vllm" and has_reasoning(reg) and not reg.get("reasoning_parser")

def reasoning_mode_for(reg, arm, setting=None):
    """Contract-B reasoning_mode for one call: off (reasoning switched off), lowest (the model cannot switch
    reasoning off and its lowest level ran), on (a crossed or ladder setting), always_on (a model that reasons at one
    setting it cannot change), not_applicable (no reasoning mode). The setting itself is on every row too."""
    if not has_reasoning(reg):
        return "not_applicable"
    s = setting or reg["plan"]["primary"]["setting"]
    if s == "OFF":
        return "off"
    if len(reg["levels"]) == 1:
        return "always_on"
    if arm in SETTING_ARMS:
        return "on"
    return "lowest"

def contract_b_row(run_id, model_key, stim, cat, fmt, order, codes, pid, mode, persona, prompt, image,
                   provider=None, api_flavor=None, model_id_requested=None, model_id_echoed=None,
                   temperature_requested=None, sampling_params_effective=None,
                   raw_response=None, parsed=None, parse_method="dry_run",
                   exclusion_flag=False, exclusion_reason="", latency_ms=None, cost_usd=0.0, timestamp=None,
                   arm="primary", reasoning_requested=None, reasoning_effective=None, session=None, probe=None,
                   draw_index=None, setting=None, served=None):
    """One contract-B record (analysis/DATA_DICTIONARY.md B). Every field the analysis engine and the cost_so_far
    record read is populated; condition coordinates match contract A so the two arms share scoring code.
    Picture calls record the PNG actually sent (image_ref, image_sha256) and the registered SVG it renders
    (image_source_svg_sha256). Sequential calls record session_id, script_id and seq_index. Recognition
    probes record the parsed answers and the recognition score (probe fields; see score_probe). Every record
    carries draw_index (which registered repeat of its grid point it is; 0 in the arms that do not repeat);
    a call without one is refused here, so no record can leave it out."""
    if not isinstance(draw_index, int) or draw_index < 0:
        raise ValueError(f"every call record carries draw_index (got {draw_index!r})")
    reg = MODEL_REGISTRY[model_key]
    setting = setting_for(model_key, arm, setting)
    png_name = png_sha = svg_sha = None
    if isinstance(image, dict) and image.get("image_ref"):
        png_name, png_sha = PICTURE_FILES[os.path.basename(image["image_ref"])]
        svg_sha = image.get("image_sha256")
    row = {
        "record_id": record_id(run_id, model_key, stim["id"], fmt, order, pid, mode, persona, arm, session,
                               draw_index, setting),
        "run_id": run_id, "model_key": model_key,
        "model_id_requested": model_id_requested, "model_id_echoed": model_id_echoed,
        "provider": provider, "api_flavor": api_flavor,
        "prompting_mode": mode, "persona_id": persona, "paraphrase_id": pid,
        "draw_index": draw_index,
        "arm": arm,
        "setting": setting,
        "reasoning_mode": reasoning_mode_for(reg, arm, setting),
        "reasoning_requested": reasoning_requested,
        "reasoning_effective": reasoning_effective,
        "temperature_requested": temperature_requested,
        "sampling_params_effective": sampling_params_effective,
        "image_ref": png_name, "image_sha256": png_sha, "image_source_svg_sha256": svg_sha,
        "cell_id": stim["id"], "category": stim["category"], "structure": stim["structure"],
        "tier": stim.get("memorization_tier"), "format": fmt.split(":")[0],
        # the similarity clone placement (clone_HF or clone_HD) on every similarity record; None elsewhere
        "sim_placement": sim_placement_of(stim, fmt),
        "placement": sim_placement_of(stim, fmt),
        "position_order": list(order), "stimulus_id": stim["id"],
        "seq_index": (session or {}).get("seq_index"),
        "session_id": f"S{session['session'] + 1:04d}" if session else None,
        "script_id": (session or {}).get("script_id"),
        "prompt_text": prompt, "raw_response": raw_response,
        "parsed_choice": parsed, "parse_method": parse_method,
        "exclusion_flag": exclusion_flag, "exclusion_reason": exclusion_reason,
        "latency_ms": latency_ms, "cost_usd": cost_usd,
        "timestamp": timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "shown_codes": codes,
        # the metadata the analysis reads for the family classes and the comparison of older and newer models
        # (synth.py carries the same two fields): family is the developer, generation is new or old
        "family": reg.get("family", model_key),
        "generation": reg.get("generation", "new"),
        "model_slot": reg.get("slot"), "model_tier": reg.get("tier"),
        "model_group": reg.get("group"), "price_tier": reg.get("price_tier"),
        # an open model's call records the served model, its pinned revision and the server's sampling defaults
        # (the vllm route; None on the other routes)
        "served": served,
        # the substitution rule's record: None, or (planned api_id, reason, date) when the slot was filled
        # by a substitute under the registered rule, so both models are reported from the data itself
        "model_substituted_from": list(reg["substituted_from"]) if reg.get("substituted_from") else None,
    }
    if probe is not None:
        row.update(probe)
    return row

def orders_for_delivery(fmt, n_opts, stim_id=None):
    """Position orders a delivery runs in. Picture cells run in the CANONICAL order only: the picture is the
    whole-set PNG the participants see, drawn once with the options labelled Option A, B, C in canonical
    order, and the human picture arm never rotates it. Rotating the
    letters in the text while the picture stays fixed would contradict the picture. Every other delivery
    runs every registered order. A twelve-option menu's orders are registered per stimulus (twelve full
    shuffles, order_plan.py, 2026-09-29), so a menu needs stim_id; without it this refuses."""
    if fmt.split(":")[0] == "pictures":
        return [tuple(range(n_opts))]
    return orders_for(n_opts, stim_id)

def picture_file(image):
    """(png_path, png_sha256, svg_sha256) for a pictures delivery, refusing a PNG whose bytes are not the
    registered file (the one the participants see)."""
    svg_name = os.path.basename(image["image_ref"])
    png_name, png_sha = PICTURE_FILES[svg_name]
    path = os.path.join(PNG_DIR, png_name)
    got = hashlib.sha256(open(path, "rb").read()).hexdigest() if os.path.exists(path) else None
    if got != png_sha:
        raise RuntimeError(f"picture {png_name}: sha256 {got} is not the registered {png_sha}")
    return path, png_sha, image.get("image_sha256")

def neutral_specs(stim, cat, model_key, cat_target_focal, pid_list, persona_id=None, arm="primary", setting=None):
    """Every neutral-grid call for one stimulus and one model: delivery form x order x paraphrase. Picture
    deliveries are skipped for a model that takes no image input (not applicable, never a missing call)."""
    reg = MODEL_REGISTRY[model_key]
    setting = setting_for(model_key, arm, setting)
    prefix = (PERSONAS[persona_id] + " ") if persona_id else ""
    for fmt, opts, wmap, image in deliveries(stim):
        if fmt == "pictures" and not reg["accepts_images"]:
            continue
        for order in orders_for_delivery(fmt, len(opts), stim["id"]):
            for pid in pid_list:
                prompt, codes = build_prompt(stim, cat, order, pid, fmt.split(":")[0], opts, wmap, prefix)
                yield dict(kind="choice", model_key=model_key, stim=stim, cat=cat, fmt=fmt, opts=opts,
                           order=order, pid=pid, codes=codes, prompt=prompt, image=image,
                           mode=ARM_MODE[arm], persona=persona_id, cat_target_focal=cat_target_focal, arm=arm,
                           session=None, draw_index=0, setting=setting)

def build_probe(stim, cat, call_index=0):
    """The registered recognition-probe message for one stimulus: the behavioral prompt's option lines
    (numbers format) in place of [option lines]. authors rule 2026-09-29: the three probe calls per
    stimulus are made non-identical by showing the options in the first three registered orders, one order per
    call (call_index 0, 1, 2 -> registered order 1, 2, 3). A two-option set has only two registered orders, so
    its third call repeats its first order (the one case where two probe calls are identical).
    Returns (text, order, shown_codes)."""
    opts = stim["options"]
    ords = orders_for(len(opts), stim["id"])
    order = ords[call_index % len(ords)]
    full, codes = build_prompt(stim, cat, order, 1, "numbers", opts)
    lines = [l for l in full.split("\n") if OPTION_LINE.match(l)]   # the option lines only
    return PROBE_TEMPLATE.replace("[option lines]", "\n".join(lines)), order, codes

def load_session_plan():
    """The sequential arm's sessions, built from the SAME 180 seven-trial scripts the human backbone
    participants take (scriptset_180.csv + the backbone mapping of indices to category and structure).
    Registered rule: session s = 0..999
    takes script (s mod 180) + 1 in script-id order; its frame is
    paraphrase ((s div 180) mod 3) + 1; trial t (0..6) uses position order index (s + t) mod n_orders; a
    similarity trial alternates its clone placement by (s div 180 + t) mod n_placements. Deterministic."""
    import csv
    mp = json.load(open(BACKBONE_MAPPING_PATH, encoding="utf-8"))
    ci, si = mp["category_index_to_name"], mp["structure_index_to_code"]
    scripts = {}
    with open(SCRIPTSET_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = f"{si[row['structure']]}_{ci[row['category']]}_t{row['tier']}"
            scripts.setdefault(int(row["script_id"]), []).append((int(row["position"]), sid))
    ids = sorted(scripts)
    plan = []
    for s in range(SEQ_SESSIONS):
        script_id = ids[s % len(ids)]
        trials = [sid for _, sid in sorted(scripts[script_id])]
        plan.append(dict(session=s, script_id=script_id, pid=(s // len(ids)) % 3 + 1, trials=trials))
    return plan

def iter_specs(stimuli, cats, models, arm="primary", draws="all", setting=None):
    """Every call an arm makes, as fully specified call specs, in a fixed deterministic order.
    primary / crossed / ladder / temp_0 / temp_1: the neutral grid (every model x stimulus x delivery x order x
    paraphrase; picture cells canonical-order only and only on image-capable models), each grid point repeated
    draws_for(arm, format, model, setting) times, DRAW-MAJOR (the whole grid at draw 0, then at draw 1, ...).
    A crossed or ladder arm runs each model at every setting of that arm in its plan, one setting after the other,
    or at the one setting named. persona: the same grid under each of the twenty personas. recognition: one probe
    per stimulus and paraphrase index. sequential: SEQ_SESSIONS seven-decision conversations per model
    (load_session_plan). A model that does not run the arm yields nothing. Every spec carries draw_index and
    setting. draws="first" yields draw_index 0 only (the small tracked dry-run log); a live run always uses "all"."""
    if draws not in ("all", "first"):
        raise ValueError(f"draws must be 'all' or 'first', not {draws!r}")
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    catmap = {c["id"]: c for c in cats}
    stimmap = {s["id"]: s for s in stimuli}
    cat_target_focal = cat_target_focal_map(stimuli)
    for model_key in models:
        settings = arm_settings(model_key, arm)
        if setting is not None:
            if arm not in SETTING_ARMS:
                setting_for(model_key, arm, setting)        # refuses a setting other than the primary
            settings = [s for s in settings if s == setting]
        if arm in NEUTRAL_ARMS:
            for s in settings:
                grid = [sp for stim in stimuli for sp in neutral_specs(stim, catmap[stim["category"]], model_key,
                                                                       cat_target_focal, list(PARAPHRASES), arm=arm,
                                                                       setting=s)]
                n_draws = [draws_for(arm, sp["fmt"], model_key, s) for sp in grid]
                top = 1 if draws == "first" else max(n_draws, default=0)
                for d in range(top):
                    for sp, n in zip(grid, n_draws):
                        if d < n:
                            yield dict(sp, draw_index=d)       # a fresh spec per draw: nothing carries over
            continue
        if not settings:
            continue
        prim = settings[0]
        if arm == "persona":
            for persona_id in PERSONAS:
                for stim in stimuli:
                    yield from neutral_specs(stim, catmap[stim["category"]], model_key, cat_target_focal,
                                             list(PARAPHRASES), persona_id=persona_id, arm=arm)
        elif arm == "recognition":
            for stim in stimuli:
                cat = catmap[stim["category"]]
                for pid in PARAPHRASES:                 # probe call 1..3 = registered order 1..3
                    text, order, codes = build_probe(stim, cat, pid - 1)
                    yield dict(kind="probe", model_key=model_key, stim=stim, cat=cat, fmt="numbers",
                               opts=stim["options"], order=order, pid=pid, codes=codes, prompt=text, image=None,
                               mode="recognition", persona=None, cat_target_focal=cat_target_focal, arm=arm,
                               session=None, draw_index=0, setting=prim)
        elif arm == "sequential":
            for sess in load_session_plan():
                s = sess["session"]
                for t, sid in enumerate(sess["trials"]):
                    stim = stimmap[sid]
                    cat = catmap[stim["category"]]
                    forms = [(f, o, w) for f, o, w, img in deliveries(stim) if f.split(":")[0] == "numbers"]
                    fmt, opts, wmap = forms[(s // 180 + t) % len(forms)]
                    ords = orders_for(len(opts), stim["id"])
                    order = ords[(s + t) % len(ords)]
                    prompt, codes = build_prompt(stim, cat, order, sess["pid"], "numbers", opts, wmap)
                    if t == 0:
                        prompt = SEQUENTIAL_OPENING + SEQUENTIAL_SEPARATOR + prompt
                    yield dict(kind="choice", model_key=model_key, stim=stim, cat=cat, fmt=fmt, opts=opts,
                               order=order, pid=sess["pid"], codes=codes, prompt=prompt, image=None,
                               mode="sequential", persona=None, cat_target_focal=cat_target_focal, arm=arm,
                               session=dict(session=s, script_id=sess["script_id"], seq_index=t + 1),
                               draw_index=0, setting=prim)

def iter_manifest(stimuli, cats, models, mode="neutral", persona=None, persona_prefix="", arm="primary",
                  setting=None):
    """Kept for callers of the June interface: the neutral grid of one arm (see iter_specs)."""
    return iter_specs(stimuli, cats, models, arm=arm, setting=setting)

# ===================================================================================================
# PROVIDER CLIENTS. Lazily constructed from env keys; a missing key for a needed provider is a logged
# preflight error, never a silent skip. The chat call returns (raw_text, echoed_model_id, usage_dict,
# sampling_effective). A rejected param surfaces as a recorded fact in sampling_effective, not a fallback.
# ===================================================================================================
def load_env_file_if_present():
    """For local smokes: if CONTEXT_FX_ENV_FILE points at a .env, load its KEY=VALUE lines into os.environ
    (without overwriting anything already set). Keys are never printed. No-op if the var is unset."""
    envp = os.environ.get("CONTEXT_FX_ENV_FILE")
    if not envp or not os.path.exists(envp):
        return
    for line in open(envp, encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# Every client gets an explicit timeout. A call at a high reasoning setting may think for many minutes, and the
# Anthropic SDK refuses a non-streaming request whose output ceiling suggests more than ten minutes unless the client's
# timeout is set (found on 2026-11-24 by test_batch.py's comparison with the SDK's own requests: every Anthropic call
# at the MAX setting, with its 32,768-token ceiling, raised "Streaming is required").
CALL_TIMEOUT_S = 1800.0


class Clients:
    """Holds provider SDK clients, built on demand from env keys. Real-call path only (never in dry-run).
    Base URLs are PINNED: the SDKs otherwise read OPENAI_BASE_URL / ANTHROPIC_BASE_URL from the environment, and on
    this estate ANTHROPIC_BASE_URL points at a local proxy, so a row saying provider=anthropic could have been served
    through something else. The vllm route is the exception by design: its server runs inside the supercomputer job, so
    its address comes from VLLM_BASE_URL (set by the job script)."""
    def __init__(self):
        import itertools, threading
        self._made = {}
        self._vllm_cycle, self._lock, self._itertools = None, threading.Lock(), itertools

    def client(self, route):
        # A model served across several nodes runs one API server per node (external load balancing); the job
        # exports their addresses in VLLM_BASE_URLS (head first, comma-separated), and the calls are spread over them
        # in turn, so no node's engine sits idle (a client that calls only the first node drives one engine of three).
        if route == "vllm" and os.environ.get("VLLM_BASE_URLS"):
            with self._lock:
                if self._vllm_cycle is None:
                    from openai import OpenAI
                    key = os.environ.get("VLLM_API_KEY") or "EMPTY"
                    urls = [u.strip() for u in os.environ["VLLM_BASE_URLS"].split(",") if u.strip()]
                    self._vllm_cycle = self._itertools.cycle([OpenAI(api_key=key, base_url=u, timeout=CALL_TIMEOUT_S) for u in urls])
                return next(self._vllm_cycle)
        if route not in self._made:
            if route not in ROUTE_BASE:
                raise RuntimeError(f"unknown route {route!r}")
            key = next((os.environ.get(k) for k in ROUTE_KEYS[route] if os.environ.get(k)), None)
            if route == "vllm":
                base = os.environ.get("VLLM_BASE_URL")
                if not base:
                    raise RuntimeError("VLLM_BASE_URL not in environment (the open-model server's job sets it)")
                key = key or "EMPTY"                       # a local vLLM server takes any key
            else:
                base = ROUTE_BASE[route]
                if not key:
                    raise RuntimeError(f"{' or '.join(ROUTE_KEYS[route])} not in environment")
            if route == "anthropic":
                import anthropic
                self._made[route] = anthropic.Anthropic(api_key=key, base_url=base, timeout=CALL_TIMEOUT_S)
            else:
                from openai import OpenAI
                self._made[route] = OpenAI(api_key=key, base_url=base, timeout=CALL_TIMEOUT_S)
        return self._made[route]

    # the June interface, kept for callers
    def openai(self): return self.client("openai")
    def openrouter(self): return self.client("openrouter")
    def anthropic(self): return self.client("anthropic")
    def google(self): return self.client("google")


# The routes: base URL, the environment variables that may hold the key, and the SDK. Every base URL is the
# developer's documented one and is a check for the pre-test calls (model_registry.json route_note).
ROUTE_BASE = {"openai": "https://api.openai.com/v1", "anthropic": "https://api.anthropic.com",
              "google": "https://generativelanguage.googleapis.com/v1beta/openai/", "xai": "https://api.x.ai/v1",
              "mistral": "https://api.mistral.ai/v1", "openrouter": "https://openrouter.ai/api/v1",
              "vllm": None}
ROUTE_KEYS = {"openai": ("OPENAI_API_KEY",), "anthropic": ("ANTHROPIC_API_KEY",),
              "google": ("GOOGLE_API_KEY", "GEMINI_API_KEY"), "xai": ("XAI_API_KEY",),
              "mistral": ("MISTRAL_API_KEY",), "openrouter": ("OPENROUTER_API_KEY",), "vllm": ("VLLM_API_KEY",)}
ROUTE_SDK = {r: ("anthropic" if r == "anthropic" else "openai") for r in ROUTE_BASE}
OPENAI_COMPATIBLE = ("openai", "google", "xai", "mistral", "vllm")

def route_for(reg):
    """The route one model's calls take."""
    return reg["route"]

# ===================================================================================================
# REQUEST CONSTRUCTION. build_request() is the ONE place a request is shaped, per route, for one model in one arm
# at one setting. The live call sends exactly what it returns; the dry run records exactly what it returns (so the
# dry-run log shows the reasoning and sampling settings a live run would send); the selftest checks every payload
# it can produce. The setting's parameters come from the registry's settings map unchanged; {} sends nothing, so
# the provider's default runs, and that is recorded in reasoning_requested.
# ===================================================================================================
def build_request(model_key, arm="primary", route=None, setting=None):
    """Return a dict: route, model_id, api_flavor, kwargs (the SDK call's keyword arguments except the messages),
    setting, reasoning_requested, temperature_requested, sampling_requested, max_tokens."""
    import copy
    reg = MODEL_REGISTRY[model_key]
    if arm not in ARMS:
        raise ValueError(f"unknown arm {arm!r}")
    setting = setting_for(model_key, arm, setting)
    route = route or route_for(reg)
    params = copy.deepcopy(reg["settings"][setting])
    max_tokens = reg["max_tokens"][setting]
    if arm == "recognition":
        max_tokens = max(max_tokens, PROBE_ANSWER_TOKENS)   # "1: YES; 2: C" needs more than a letter's cap
    temp = ARM_TEMPERATURE.get(arm, reg["temperature"])
    if arm in ARM_TEMPERATURE and not reg["accepts_temperature"]:
        raise ValueError(f"{model_key} does not accept a temperature and is not in the temperature arms")
    kwargs, extra_body, sampling = {}, {}, {}
    if reg["rejects_temperature"]:
        # never sent; recorded on every row of this model as the API fact it is
        sampling["temperature_not_sent"] = f"{reg['api_id']} does not accept a temperature (API fact)"
        temp = None
    model_id = reg["model_id"]
    if route == "anthropic":
        flavor = "messages"
        kwargs["max_tokens"] = max_tokens
        if "thinking" in params:
            kwargs["thinking"] = params.pop("thinking")
        extra_body.update(params)                 # output_config goes through extra_body (any SDK version)
    elif route in OPENAI_COMPATIBLE:
        flavor = "chat.completions"
        kwargs["max_completion_tokens" if route == "openai" else "max_tokens"] = max_tokens
        if "reasoning_effort" in params:
            kwargs["reasoning_effort"] = params.pop("reasoning_effort")
        extra_body.update(params)                 # chat_template_kwargs and any other non-SDK parameter
    elif route == "openrouter":
        flavor = "chat.completions"
        kwargs["max_tokens"] = max_tokens
        extra_body.update(params)                 # OpenRouter's reasoning object
        if reg.get("provider_pin"):
            extra_body["provider"] = dict(reg["provider_pin"])
    else:
        raise ValueError(f"unknown route {route!r}")
    if temp is not None:
        kwargs["temperature"] = temp
        sampling["temperature"] = temp
    if extra_body:
        kwargs["extra_body"] = extra_body
    reasoning = {"setting": setting, "params": copy.deepcopy(reg["settings"][setting]),
                 "sent": "nothing (the provider's default)" if not reg["settings"][setting] else "the params above"}
    sampling["max_tokens"] = max_tokens
    if reg.get("provider_pin") and route == "openrouter":
        sampling["provider_pin"] = dict(reg["provider_pin"])
    return dict(route=route, model_id=model_id, api_flavor=flavor, kwargs=kwargs, setting=setting,
                reasoning_requested=reasoning, temperature_requested=temp,
                sampling_requested=sampling, max_tokens=max_tokens)

PROBE_ANSWER_TOKENS = 32
_PNG_B64 = {}

def build_messages(spec, route):
    """Provider-format messages for one call: any earlier turns of a sequential session (history), then this
    call's user message. A picture call's user message is three parts, mirroring the participants' page:
    the frame line, the picture (the registered PNG, base64), then the option lines and the instruction."""
    import base64
    msgs = [dict(m) for m in (spec.get("history") or [])]
    img = spec.get("image")
    if spec.get("fmt", "numbers").split(":")[0] == "pictures" and isinstance(img, dict) and img.get("image_ref"):
        path, png_sha, _ = picture_file(img)
        if path not in _PNG_B64:
            _PNG_B64[path] = base64.b64encode(open(path, "rb").read()).decode("ascii")
        b64 = _PNG_B64[path]
        head, rest = split_head(spec["prompt"])        # the picture follows the whole question, as on the page
        if route == "anthropic":
            pic = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}}
        else:
            pic = {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}
        msgs.append({"role": "user", "content": [{"type": "text", "text": head}, pic, {"type": "text", "text": rest}]})
    else:
        msgs.append({"role": "user", "content": spec["prompt"]})
    return msgs

def logged_prompt(spec):
    """prompt_text for the call record: the text sent, with a picture call's image position and file shown."""
    img = spec.get("image")
    if spec.get("fmt", "numbers").split(":")[0] == "pictures" and isinstance(img, dict) and img.get("image_ref"):
        png_name, png_sha = PICTURE_FILES[os.path.basename(img["image_ref"])]
        head, rest = split_head(spec["prompt"])
        return f"{head}\n[picture: {png_name}, sha256 {png_sha}]\n{rest}"
    return spec["prompt"]

def echo_ok(reg, requested_id, echoed):
    """True when the echoed model id names the registered model: the id we sent, a registered echo id, or a
    dated form of the id we sent (an alias resolving to its snapshot). Anything else is id drift."""
    if not echoed:
        return True
    if echoed == requested_id or echoed in reg.get("echo_ids", ()):
        return True
    base = re.escape(requested_id)
    return bool(re.fullmatch(base + r"-(\d{4}-\d{2}-\d{2}|\d{8})", echoed))

def _usd(usage, reg):
    """Per-call cost from token usage at the registry's per-1M prices (reasoning tokens are inside the
    completion/output count on every route used here, and bill at the output rate)."""
    if not usage:
        return 0.0
    p_in, p_out = reg["price_per_1m"]
    return round(((usage.get("prompt_tokens", 0) or 0) * p_in +
                  (usage.get("completion_tokens", 0) or 0) * p_out) / 1e6, 6)

def _reasoning_tokens(u):
    """usage.completion_tokens_details.reasoning_tokens where the route reports it (OpenAI, OpenRouter)."""
    det = getattr(u, "completion_tokens_details", None) if u is not None else None
    if det is None:
        return None
    return getattr(det, "reasoning_tokens", None) if not isinstance(det, dict) else det.get("reasoning_tokens")

def call_model(clients, spec):
    """Make ONE real model call for a spec. Returns a dict with raw_response, model_id_requested,
    model_id_echoed, usage, sampling_params_effective, reasoning_requested, reasoning_effective, latency_ms,
    cost_usd, and any error. Never raises - the caller logs the row regardless (a crashed call becomes a
    recorded exclusion, so the run never dies). A 400 on a reasoning or temperature setting lands in the
    row's error text: a recorded API fact, never a silent retry without the setting."""
    req = build_request(spec["model_key"], spec.get("arm", "primary"), setting=spec.get("setting"))
    t0 = time.time()
    try:
        messages = build_messages(spec, req["route"])
        if req["route"] == "anthropic":
            r = clients.client("anthropic").messages.create(model=req["model_id"], messages=messages, **req["kwargs"])
        else:
            r = clients.client(req["route"]).chat.completions.create(model=req["model_id"], messages=messages,
                                                                      **req["kwargs"])
        return result_from_response(spec, req, r, int((time.time() - t0) * 1000))
    except Exception as e:
        return result_from_error(spec, req, f"{type(e).__name__}: {e}", int((time.time() - t0) * 1000))

def result_from_response(spec, req, r, latency_ms, price_factor=1.0, batch=None):
    """The call record's fields from one provider response: an SDK object from a live call, or the same response
    read back from a batch's results file (as_attrs turns its JSON into attributes). price_factor is 0.5 for a batch,
    which bills half; batch names the batch the answer came from."""
    reg = MODEL_REGISTRY[spec["model_key"]]
    sampling_effective = dict(req["sampling_requested"])
    if batch:
        sampling_effective["batch"] = batch
    if req["route"] == "anthropic":
        blocks = list(getattr(r, "content", []) or [])
        raw = "".join(b.text for b in blocks if getattr(b, "type", None) == "text")
        echoed = getattr(r, "model", None)
        u = getattr(r, "usage", None)
        usage = {"prompt_tokens": getattr(u, "input_tokens", 0),
                 "completion_tokens": getattr(u, "output_tokens", 0)} if u else {}
        stop = getattr(r, "stop_reason", None)
        sampling_effective["stop_reason"] = stop
        reasoning_effective = {"thinking_blocks": sum(1 for b in blocks if getattr(b, "type", None) == "thinking"),
                               "output_tokens_incl_thinking": usage.get("completion_tokens"),
                               "stop_reason": stop}
    else:
        ch = r.choices[0]
        raw = ch.message.content or ""
        echoed = getattr(r, "model", None)
        u = getattr(r, "usage", None)
        usage = {}
        if u:
            pt = getattr(u, "prompt_tokens", 0) or 0
            ct = getattr(u, "completion_tokens", 0) or 0
            tt = getattr(u, "total_tokens", 0) or 0
            # Some OpenAI-compatible surfaces (reported for Gemini's) leave thinking tokens out of
            # completion_tokens while counting them in total_tokens; bill the larger of the two readings.
            usage = {"prompt_tokens": pt, "completion_tokens": max(ct, tt - pt),
                     "completion_tokens_reported": ct, "total_tokens": tt}
        extra = getattr(r, "model_extra", None) or {}
        sampling_effective["finish_reason"] = getattr(ch, "finish_reason", None)
        if req["route"] == "openrouter":
            sampling_effective["served_by"] = extra.get("provider")   # verifies the host pin
        reasoning_effective = {"reasoning_tokens": _reasoning_tokens(u),
                               "finish_reason": getattr(ch, "finish_reason", None)}
        # vLLM with a reasoning parser (and OpenRouter) return the thinking as its own field of the message, often
        # with no reasoning-token count; its length is recorded, and it counts as reasoning for the flag below
        thought = getattr(ch.message, "reasoning_content", None) or getattr(ch.message, "reasoning", None)
        if isinstance(thought, str) and thought.strip():
            reasoning_effective["reasoning_chars"] = len(thought)
    # A request registered as reasoning OFF that still reports hidden reasoning is flagged, never hidden.
    if (req["setting"] == "OFF" and has_reasoning(reg)
            and (reasoning_effective.get("reasoning_tokens") or reasoning_effective.get("thinking_blocks")
                 or reasoning_effective.get("reasoning_chars"))):
        reasoning_effective["off_request_reasoned"] = True
    return dict(raw_response=raw, model_id_requested=req["model_id"], model_id_echoed=echoed, usage=usage,
                sampling_params_effective=sampling_effective, reasoning_requested=req["reasoning_requested"],
                reasoning_effective=reasoning_effective, temperature_requested=req["temperature_requested"],
                api_flavor=req["api_flavor"], route=req["route"], setting=req["setting"],
                served=served_record(reg, req["route"], echoed),
                latency_ms=latency_ms, cost_usd=round(_usd(usage, reg) * price_factor, 6), error=None)

def result_from_error(spec, req, message, latency_ms, batch=None):
    """The fields of a call that failed (no answer): never written to the data log, only to the errors file."""
    sampling_effective = dict(req["sampling_requested"], error=message)
    if batch:
        sampling_effective["batch"] = batch
    return dict(raw_response=None, model_id_requested=req["model_id"], model_id_echoed=None, usage={},
                sampling_params_effective=sampling_effective, reasoning_requested=req["reasoning_requested"],
                reasoning_effective={"error": message.split(":")[0]},
                temperature_requested=req["temperature_requested"], api_flavor=req["api_flavor"],
                route=req["route"], setting=req["setting"], served=None,
                latency_ms=latency_ms, cost_usd=0.0, error=message)

class as_attrs:
    """A JSON object read back from a batch's results, with attribute access like the SDK's response objects (lists
    and nested objects too; a missing attribute raises AttributeError, as on the SDK's objects, so getattr with a
    default works), so a batch answer is parsed by the same code as a live one. model_extra holds the whole object,
    as on the SDK's objects."""
    def __init__(self, d):
        self._d = d or {}
        self.model_extra = self._d
    def __getattr__(self, k):
        if k.startswith("_") or k not in self._d:
            raise AttributeError(k)
        return _attrs(self._d[k])

def _attrs(v):
    if isinstance(v, dict):
        return as_attrs(v)
    if isinstance(v, list):
        return [_attrs(x) for x in v]
    return v

def served_record(reg, route, echoed=None):
    """What served an open model's call: the model the server names, the registered repository and revision, and
    the server's record of its revision and sampling defaults. The supercomputer job writes that record before the run
    (VLLM_SERVED_INFO, a JSON file: the vLLM version, the model's path and revision as loaded, and the sampling
    defaults read from the repository's generation_config.json). None on every other route."""
    if route != "vllm":
        return None
    info = {}
    path = os.environ.get("VLLM_SERVED_INFO")
    if path and os.path.exists(path):
        info = json.load(open(path, encoding="utf-8"))
    # revision_started is the --revision the server was started with, read from the job's own serve arguments; with
    # HF_HUB_OFFLINE=1 the server can load no other revision, so it differs from the registry's only when the job
    # was started at another revision
    return {"model_echoed": echoed, "hf_repo": reg["hf_repo"], "hf_revision": reg["hf_revision"][1],
            "revision_started": info.get("revision"), "snapshot_present": info.get("snapshot_present"),
            "vllm_version": info.get("vllm_version"), "sampling_defaults": info.get("sampling_defaults"),
            "revision_matches": info.get("revision") == reg["hf_revision"][1] if info else None}

# ===================================================================================================
# REGISTRY VALIDATOR + SELFTEST (no network). validate_registry() returns every broken rule for a registry;
# the selftest requires it to return nothing for the real registry AND to catch each planted fault in a
# mutated copy (a check that cannot fail is decorative). It then builds every request payload the runner
# can send and checks the payload rules. Run: python run.py --selftest (exit 0 = pass, 1 = fail).
# ===================================================================================================
REQUIRED_FIELDS = ("key", "slot", "developer", "model_name", "group", "tier", "price_tier", "family", "generation",
                   "release", "route", "provider", "api_id", "model_id", "open_weights", "accepts_images",
                   "price_per_1m", "has_off", "levels", "settings", "max_tokens", "accepts_temperature",
                   "rejects_temperature", "temperature", "plan", "unconfirmed", "batch", "echo_ids", "hf_revision",
                   "provider_pin")
GROUPS = ("closed_current", "closed_previous", "open")
ROUTES = tuple(ROUTE_BASE)

def validate_registry(registry):
    """Every broken rule of a registry, as a list of sentences (empty = the registry passes). The plan's counts are
    cost_plan.py's (working repository/design/models-2026-11/test_registry.py checks them model by model); these rules check
    that each entry can be run as it says."""
    problems = []
    if not registry:
        return ["the registry is empty"]
    slots = sorted(r.get("slot") or 0 for r in registry.values())
    if slots != list(range(1, len(registry) + 1)):
        problems.append(f"slots are not exactly 1..{len(registry)}")
    for k, r in registry.items():
        missing = [f for f in REQUIRED_FIELDS if f not in r]
        if missing:
            problems.append(f"{k}: missing fields {missing}")
            continue
        if r["key"] != k:
            problems.append(f"{k}: key field {r['key']!r} differs")
        if r["group"] not in GROUPS:
            problems.append(f"{k}: unknown group {r['group']!r}")
        if r["route"] not in ROUTES or r["provider"] != r["route"]:
            problems.append(f"{k}: unknown route {r['route']!r}")
        if r["generation"] not in ("new", "old"):
            problems.append(f"{k}: generation must be new or old")
        if r["family"] != f"{r['developer']} {'open' if r['group'] == 'open' else 'closed'}":
            problems.append(f"{k}: family must be the developer and its access, closed or open (the Method's definition)")
        if r["group"] == "closed_current" and r["generation"] != "new":
            problems.append(f"{k}: a current closed model is the new generation")
        if r["group"] == "closed_previous" and r["generation"] != "old":
            problems.append(f"{k}: a previous closed model is the old generation")
        lv = list(r["levels"])
        if not lv or any(s not in SETTINGS for s in lv) or len(set(lv)) != len(lv):
            problems.append(f"{k}: levels {lv} are not distinct common settings")
        if sorted(r["settings"]) != sorted(lv) or sorted(r["max_tokens"]) != sorted(lv):
            problems.append(f"{k}: the settings map and the ceilings must cover exactly its levels {lv}")
        if r["has_off"] != ("OFF" in lv):
            problems.append(f"{k}: has_off disagrees with its levels")
        p = r["plan"]
        prim = (p.get("primary") or {}).get("setting")
        want_prim = "OFF" if "OFF" in lv else next((s for s in SETTINGS if s in lv), None)
        if prim != want_prim:
            problems.append(f"{k}: the primary setting must be the lowest it offers ({want_prim}), not {prim!r}")
        used = [prim] + [c["setting"] for c in p.get("crossed", []) + p.get("ladder", [])]
        if any(s not in lv for s in used) or len(set(used)) != len(used):
            problems.append(f"{k}: the plan runs a setting the model does not offer, or one setting twice: {used}")
        for c in [p.get("primary") or {}] + p.get("crossed", []) + p.get("ladder", []):
            if not isinstance(c.get("draws"), int) or c["draws"] < 1 or c.get("picture_draws") != 6 * c["draws"]:
                problems.append(f"{k}: a setting needs draws >= 1 and six times as many picture draws: {c}")
        for s in lv:
            room = r["max_tokens"][s]
            thinks = s != "OFF"
            if thinks and room < 1024:
                problems.append(f"{k}: setting {s} reasons but its ceiling is {room} (< 1024)")
            if not thinks and room < 16:
                problems.append(f"{k}: setting OFF has a ceiling under 16")
        if "OFF" in lv and has_reasoning(r) and r["settings"]["OFF"] == {} \
                and not (r["route"] == "anthropic" and len(lv) == 1):
            problems.append(f"{k}: OFF sends nothing on a model that reasons, so the provider's default would run")
        blob = json.dumps(r["settings"])
        if r["route"] == "anthropic" and ("reasoning_effort" in blob or '"none"' in blob):
            problems.append(f"{k}: Anthropic takes output_config.effort and the thinking parameter, not reasoning_effort")
        if r["route"] == "openrouter":
            pin = r.get("provider_pin") or {}
            if len(pin.get("only") or []) != 1 or pin.get("allow_fallbacks") is not False \
                    or not pin.get("require_parameters"):
                problems.append(f"{k}: an OpenRouter model needs ONE pinned host, no fallbacks, require_parameters")
        elif r.get("provider_pin"):
            problems.append(f"{k}: a provider pin on a direct route")
        if r["open_weights"] != (r["group"] == "open") or (r["route"] == "vllm") != (r["group"] == "open"):
            problems.append(f"{k}: an open model runs on vllm, and only an open model does")
        if r["group"] == "open":
            hv = r.get("hf_revision")
            if not hv or len(hv) != 2 or hv[0] != r["model_id"] or len(hv[1] or "") != 40:
                problems.append(f"{k}: an open model needs its Hugging Face repository and a 40-character revision")
            if any(r["price_per_1m"]):
                problems.append(f"{k}: an open model has no API price")
        if r["rejects_temperature"] == r["accepts_temperature"]:
            problems.append(f"{k}: rejects_temperature must be the opposite of accepts_temperature")
        if p.get("temperature") and not r["accepts_temperature"]:
            problems.append(f"{k}: in the temperature arms but does not accept a temperature")
        if r["temperature"] is not None and r["rejects_temperature"]:
            problems.append(f"{k}: sends a temperature it does not accept")
        if r["price_tier"] == "premium" and (p.get("persona") or p.get("ladder") or p.get("temperature")):
            problems.append(f"{k}: a premium model runs no persona, ladder or temperature condition")
        if r["route"] == "vllm" and r["batch"]:
            problems.append(f"{k}: the vllm route has no batch service")
        if len(r["price_per_1m"]) != 2:
            problems.append(f"{k}: price_per_1m must be (input, output)")
        sub = r.get("substituted_from")
        if sub is not None and (not isinstance(sub, tuple) or len(sub) != 3):
            problems.append(f"{k}: substituted_from must be (planned id, reason, date)")
    if not any(r.get("accepts_images") for r in registry.values()):
        problems.append("no image-capable model")
    return problems

class _NS:
    """Tiny attribute bag for the offline fake responses."""
    def __init__(self, **kw):
        self.__dict__.update(kw)

class _FakeProvider:
    """Stands in for one SDK client, offline. Records every create() call's kwargs and returns a response with
    the attributes the real SDK objects expose. reasoning_tokens / hidden_in_total_only shape the usage block;
    fail=True raises like a dead key or route. alternate=True answers A, B, A, B ... in call order (every reply
    kept in .replies), so a test can prove that each logged row holds the answer of its own call."""
    def __init__(self, calls, reasoning_tokens=0, hidden_in_total_only=0, fail=False, served_by="Novita",
                 alternate=False):
        self.calls, self.rt, self.hidden, self.fail, self.served_by = calls, reasoning_tokens, hidden_in_total_only, fail, served_by
        self.alternate, self.replies = alternate, []
        self.chat = _NS(completions=_NS(create=self._chat))
        self.messages = _NS(create=self._messages)

    def _chat(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise RuntimeError("simulated API failure")
        usage = _NS(prompt_tokens=100, completion_tokens=5 + self.rt, total_tokens=105 + self.rt + self.hidden,
                    completion_tokens_details=_NS(reasoning_tokens=self.rt))
        reply = "AB"[(len(self.calls) - 1) % 2] if self.alternate else "B"
        self.replies.append(reply)
        return _NS(choices=[_NS(message=_NS(content=reply), finish_reason="stop")], model=kw["model"], usage=usage,
                   model_extra={"provider": self.served_by})

    def _messages(self, **kw):
        self.calls.append(kw)
        if self.fail:
            raise RuntimeError("simulated API failure")
        blocks = ([_NS(type="thinking", thinking="")] if self.rt else []) + [_NS(type="text", text="B")]
        return _NS(content=blocks, model=kw["model"], usage=_NS(input_tokens=100, output_tokens=5 + self.rt),
                   stop_reason="end_turn")

class _FakeClients:
    def __init__(self, **kw):
        self.calls = []
        self.p = _FakeProvider(self.calls, **kw)
    def client(self, route): return self.p
    def openai(self): return self.p
    def openrouter(self): return self.p
    def google(self): return self.p
    def anthropic(self): return self.p

# The models the slow checks (whole-grid enumeration, the live loop) run on: one of each kind that changes how a call
# is built or counted. The fast checks (the validator, every request payload, the offline call path) run on all.
SELFTEST_IMAGE_MODEL = "gpt-6-luna"     # budget, reasoning off at primary, pictures, every arm, a ladder
SELFTEST_TEXT_MODEL = "qwen25-7b"       # open, vllm, no reasoning mode, text only, temperature arms

def representative_models():
    """One model per (route, accepts pictures, price tier, has an off setting, runs a ladder), in roster order."""
    seen, out = set(), []
    for k, r in MODEL_REGISTRY.items():
        shape = (r["route"], r["accepts_images"], r["price_tier"], r["has_off"], bool(r["plan"]["ladder"]))
        if shape not in seen:
            seen.add(shape)
            out.append(k)
    return out

def arm_calls(model_key):
    """Every (arm, setting) one model runs."""
    return [(arm, s) for arm in ARMS for s in arm_settings(model_key, arm)]

def _offline_call_checks():
    """call_model and run_collection driven through fake clients: no network, no SDK needed. Returns failures."""
    import contextlib, io, tempfile, shutil
    bad = []
    prompt = "Choose a backpack from these options:\n  A. 30 liters capacity, $29.99\n  B. 40 liters capacity, $39.99\n" + RESP
    saved = os.environ.get("VLLM_SERVED_INFO")
    os.environ.pop("VLLM_SERVED_INFO", None)
    for k, reg in MODEL_REGISTRY.items():
        for arm in ("primary", "crossed", "ladder"):
            for s in arm_settings(k, arm):
                fc = _FakeClients()
                res = call_model(fc, dict(model_key=k, prompt=prompt, arm=arm, setting=s))
                req = build_request(k, arm, setting=s)
                sent = fc.calls[-1] if fc.calls else {}
                tag = f"offline {k}/{arm}/{s}"
                if res["error"] is not None:
                    bad.append(f"{tag}: call_model errored: {res['error']}")
                    continue
                if sent.get("model") != req["model_id"] or sent.get("messages") != [{"role": "user", "content": prompt}]:
                    bad.append(f"{tag}: model or messages sent differ from build_request")
                for key, val in req["kwargs"].items():
                    if sent.get(key) != val:
                        bad.append(f"{tag}: sent {key}={sent.get(key)!r}, built {val!r}")
                if res["reasoning_requested"] != req["reasoning_requested"] or res["setting"] != s \
                        or res["temperature_requested"] != req["temperature_requested"]:
                    bad.append(f"{tag}: recorded request differs from the payload")
                if reg["route"] == "vllm":
                    if res["cost_usd"] != 0 or not res["served"] or res["served"]["hf_revision"] != reg["hf_revision"][1]:
                        bad.append(f"{tag}: an open model's call must cost nothing and record its revision")
                elif not res["cost_usd"] > 0 or res["served"] is not None:
                    bad.append(f"{tag}: no cost recorded, or a served record on a closed route")
                if req["route"] == "openrouter" and res["sampling_params_effective"].get("served_by") != "Novita":
                    bad.append(f"{tag}: served_by host not recorded")
    if saved is not None:
        os.environ["VLLM_SERVED_INFO"] = saved
    # a reasoning-OFF request that still reports reasoning is flagged; a clean one is not; a model with no reasoning
    # mode is never flagged
    for k in ("claude-haiku-5-5", "gpt-6-luna", "qwen35-27b"):
        r1 = call_model(_FakeClients(reasoning_tokens=7), dict(model_key=k, prompt=prompt, arm="primary"))
        r0 = call_model(_FakeClients(reasoning_tokens=0), dict(model_key=k, prompt=prompt, arm="primary"))
        if not r1["reasoning_effective"].get("off_request_reasoned") or r0["reasoning_effective"].get("off_request_reasoned"):
            bad.append(f"offline {k}: off_request_reasoned flag wrong")
    rn = call_model(_FakeClients(reasoning_tokens=7), dict(model_key=SELFTEST_TEXT_MODEL, prompt=prompt, arm="primary"))
    if rn["reasoning_effective"].get("off_request_reasoned"):
        bad.append("offline: a model with no reasoning mode was flagged for reasoning")
    # thinking counted only in total_tokens (reported for Gemini's OpenAI-compatible surface) is still billed
    rg = call_model(_FakeClients(hidden_in_total_only=300), dict(model_key="gemini-4-neon", prompt=prompt, arm="primary"))
    if rg["usage"].get("completion_tokens") != 305:
        bad.append(f"offline gemini: hidden tokens in total_tokens not counted (got {rg['usage'].get('completion_tokens')})")
    rf = call_model(_FakeClients(fail=True), dict(model_key=SELFTEST_IMAGE_MODEL, prompt=prompt, arm="primary"))
    if rf["error"] is None or rf["raw_response"] is not None:
        bad.append("offline: a raised API error was not reported as an error")
    # the live loop: errors are retried, not logged as data; foreign runs refused; cost cap checked first
    m = SELFTEST_IMAGE_MODEL
    tmp = tempfile.mkdtemp(prefix="runpy_selftest_")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            lp = os.path.join(tmp, "model_log.jsonl")
            fail = _FakeClients(fail=True)
            s = run_collection(True, 3, 5.0, [m], "SELFTEST", clients=fail, log_path=lp)
            ep = lp[:-len(".jsonl")] + ".errors.jsonl"
            errs = [json.loads(l) for l in open(ep, encoding="utf-8")] if os.path.exists(ep) else []
            logged = open(lp, encoding="utf-8").read().strip() if os.path.exists(lp) else ""
            if s["written"] != 0 or logged or len(errs) != 20:
                bad.append(f"live loop: failed calls must go to the errors file only and stop after 20 in a row "
                           f"(written {s['written']}, errors {len(errs)})")
            good = _FakeClients()
            s2 = run_collection(True, 3, 5.0, [m], "SELFTEST", clients=good, log_path=lp)
            rows = [json.loads(l) for l in open(lp, encoding="utf-8")]
            if s2["written"] != 3 or [r["record_id"] for r in rows] != [e["record_id"] for e in errs[:3]]:
                bad.append("live loop: failed calls were not retried on the next run")
            if any(r["run_id"] != "SELFTEST" for r in rows):
                bad.append("live loop: wrong run_id on rows")
            if any(r.get("setting") != "OFF" or r.get("arm") != "primary" for r in rows):
                bad.append("live loop: a primary row does not carry its arm and setting")
            with open(lp, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(dict(rows[0], record_id="x", run_id="DRYRUN")) + "\n")
            try:
                run_collection(True, 1, 5.0, [m], "SELFTEST", clients=good, log_path=lp)
                bad.append("live loop: a log holding DRYRUN rows was not refused")
            except SystemExit:
                pass
            cap = _FakeClients()
            s3 = run_collection(True, 3, 1e-9, [m], "SELFTEST", clients=cap, log_path=os.path.join(tmp, "cap.jsonl"))
            if s3["written"] != 0 or cap.calls:
                bad.append("live loop: the cost cap did not stop the run before the first call")
            # a crossed arm runs one setting per log, and its rows say so
            lc = os.path.join(tmp, "crossed.jsonl")
            run_collection(True, 2, 5.0, [m], "SELFTEST", clients=_FakeClients(), arm="crossed", setting="HIGH",
                           log_path=lc)
            rc = [json.loads(l) for l in open(lc, encoding="utf-8")]
            if len(rc) != 2 or any(r.get("arm") != "crossed" or r.get("setting") != "HIGH" or r.get("reasoning_mode") != "on"
                                   for r in rc):
                bad.append("live loop: crossed rows must carry arm crossed, their setting and reasoning_mode on")
            try:
                run_collection(True, 1, 5.0, [m], "SELFTEST", clients=_FakeClients(), arm="crossed",
                               log_path=os.path.join(tmp, "nos.jsonl"))
                bad.append("live loop: a crossed run without its setting was accepted")
            except ValueError:
                pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return bad

def _materials_and_arms_checks():
    """Checks added with the registered materials and the picture protocol. Returns (n_checks, failures)."""
    import contextlib, io, tempfile, shutil
    bad, n = [], 0
    def need(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            bad.append(msg)
    M = REGISTERED_PROMPT_MATERIALS
    # 10. materials: the published file equals the registered constant; twenty personas; P07 unchanged
    need(os.path.exists(MATERIALS_PATH) and json.load(open(MATERIALS_PATH, encoding="utf-8")) == M,
         "prompt_materials.json differs from the registered constant")
    need(list(PERSONAS) == [f"P{i:02d}" for i in range(1, 21)], "personas must be exactly P01..P20 in order")
    need(PERSONAS["P07"] == "You are a 34-year-old teacher from Ohio shopping on a moderate budget.",
         "P07 changed from the June persona")
    need(all(p.startswith("You are a ") and p.endswith(" budget.") for p in PERSONAS.values()),
         "a persona is not in the registered sentence form")
    need(PROBE_TEMPLATE.count("[option lines]") == 1 and PROBE_TEMPLATE.endswith(
        "Reply in exactly this format: 1: YES or NO; 2: a letter or NONE"), "probe template altered")
    need(SEQUENTIAL_OPENING == ("You will make seven separate shopping decisions, one at a time. For each one, "
                                "choose the option you would buy."), "sequential opening altered")
    # 11. the probe parser, case by case (3 options shown unless noted)
    cases = [("1: YES; 2: C", 3, ("YES", "C", "exact")), ("1: no; 2: none", 3, ("NO", "NONE", "exact")),
             ("1: YES; 2: B.", 3, ("YES", "B", "exact")), ("1: YES\n2: A", 3, ("YES", "A", "exact")),
             ("1:YES;2:C", 3, ("YES", "C", "exact")),
             ("Sure. 1: YES; 2: C", 3, ("YES", "C", "fallback_regex")),
             ("1. YES\n2. NONE (nothing added)", 3, ("YES", "NONE", "fallback_regex")),
             ("1: YES; 2: D", 3, (None, None, "failed")), ("1: MAYBE; 2: A", 3, (None, None, "failed")),
             ("YES, option B", 3, (None, None, "failed")), ("", 3, (None, None, "failed")),
             ("1: YES; 2: L", 12, ("YES", "L", "exact")), ("1: NO; 2: B", 3, ("NO", "B", "exact"))]
    for raw, k, want in cases:
        need(parse_probe(raw, k) == want, f"parse_probe({raw!r}, {k}) = {parse_probe(raw, k)}, want {want}")
    # 12. probe scoring: YES + the added option = 1; a wrong letter = 0; binary control YES = 1; NO+letter flagged
    need(score_probe("FRQ", "YES", "B", ["TARGET", "DECOY", "COMP"])["recognition"] == 1, "FRQ decoy named: 1")
    need(score_probe("FRQ", "YES", "A", ["TARGET", "DECOY", "COMP"])["recognition"] == 0, "FRQ wrong letter: 0")
    need(score_probe("FRQ", "NO", "NONE", ["TARGET", "DECOY", "COMP"])["recognition"] == 0, "FRQ NO: 0")
    need(score_probe("BIN", "YES", "NONE", ["TARGET", "COMP"])["recognition"] == 1, "BIN YES: 1")
    need(score_probe("MOT", "YES", "NONE", ["X"] * 12)["recognition"] == 1, "MOT YES: 1")
    need(score_probe("SOT", "NO", "B", ["A1", "EXTREME", "C1"])["probe_inconsistent"] is True, "NO + letter flagged")
    # the probe message: registered text around the behavioral prompt's option lines, first order
    d = json.load(open(STIM, encoding="utf-8"))
    stimuli, cats = d["stimuli"], d["categories"]
    catmap = {c["id"]: c for c in cats}
    frq = next(s for s in stimuli if s["id"] == "FRQ_bluetooth_speakers_t2")
    text, order, codes = build_probe(frq, catmap[frq["category"]])
    behav, _ = build_prompt(frq, catmap[frq["category"]], orders_for(3)[0], 1, "numbers", frq["options"])
    need(text == PROBE_TEMPLATE.replace("[option lines]", "\n".join(behav.split("\n")[1:-1])),
         "probe message is not the template filled with the behavioral option lines")
    need(order == orders_for(3)[0], "probe call 1 does not use the first registered order")
    # three probe calls per stimulus, one per registered order: distinct for 3+ options; a two-option set
    # has two orders, so its third call repeats its first
    for s in stimuli:
        c = catmap[s["category"]]
        trio = [build_probe(s, c, i) for i in range(3)]
        ords = orders_for(len(s["options"]), s["id"])
        need([t[1] for t in trio] == [ords[i % len(ords)] for i in range(3)], f"{s['id']}: probe orders wrong")
        if len(ords) >= 3:
            need(len({t[0] for t in trio}) == 3, f"{s['id']}: the three probe calls are not distinct")
        else:
            need(trio[2][0] == trio[0][0] and trio[1][0] != trio[0][0], f"{s['id']}: two-option probe pattern")
    probes = [sp for sp in iter_specs(stimuli, cats, [SELFTEST_IMAGE_MODEL], arm="recognition")]
    need(len(probes) == len(stimuli) * 3, "three probe calls per stimulus")
    need([sp["order"] for sp in probes[:3]] == [build_probe(probes[0]["stim"], probes[0]["cat"], i)[1] for i in range(3)],
         "the recognition arm does not pair call k with order k")
    # the recognition rate: share of a stimulus's scoreable probe calls that recognize
    rr = [{"prompting_mode": "recognition", "stimulus_id": "X", "recognition": v} for v in (1, 0, None)]
    need(recognition_rate(rr, "X") == 0.5 and recognition_rate(rr, "Y") is None, "recognition_rate rule")
    # the frames: every category's product phrase, with its article, is the participants' own wording
    need(all("{product}" in f and "a {" not in f for f in PARAPHRASES.values()), "frames must take {product}")
    for c in cats:
        phrase = product_phrase(c)
        stems = [s["stem"] for s in stimuli if s["category"] == c["id"] and s.get("stem")]
        need(bool(stems) and all(phrase in st for st in stems), f"{c['id']}: '{phrase}' is not in its human stems")
        lead = f"{frame_verb(c)} {phrase}"          # frame 1 reads exactly as the participants' question
        need(bool(stems) and all(lead in st for st in stems), f"{c['id']}: frame 1 '{lead}' is not in its human stems")
        for pid in PARAPHRASES:
            head = frame_head(pid, c)
            need(not re.search(r"\ba [aeiouAEIOU]", head) and not re.search(r"\ban [^aeiouAEIOU\s]", head),
                 f"{c['id']}: article error in frame {pid}: {head}")
            need("shopping for a restaurant" not in head and "restaurant to purchase" not in head,
                 f"{c['id']}: frame {pid} misreads a restaurant: {head}")
    need(frame_head(2, next(c for c in cats if c["id"] == "restaurants")) ==
         "You are choosing a restaurant to eat at. The available options are:", "restaurants frame 2 wording")
    need(len(PRODUCT_PHRASES) == 10, "ten product phrases")
    for s in stimuli:
        added = PROBE_SINGLE_ADDED.get(s["structure"])
        if added:
            need(added in [o["code"] for o in s["options"]], f"{s['id']}: its added option {added} is not shown")
    # 13. pictures: only on image-capable slots, canonical order only, the registered PNG in the payload
    # (distinct picture prompts, draw_index 0; the repeated draws are checked in _draw_checks)
    rec = {k: [sp for sp in iter_specs(stimuli, cats, [k], draws="first") if sp["fmt"] == "pictures"]
           for k in set(representative_models()) | {SELFTEST_IMAGE_MODEL, SELFTEST_TEXT_MODEL}}
    for k, specs in rec.items():
        if MODEL_REGISTRY[k]["accepts_images"]:
            need(len(specs) == 27, f"{k}: {len(specs)} picture calls, want 9 sets x 3 frames = 27")
            need(all(sp["order"] == tuple(range(len(sp["opts"]))) for sp in specs), f"{k}: a picture cell rotated")
        else:
            need(not specs, f"{k}: a text-only slot has picture calls")
    pic = rec[SELFTEST_IMAGE_MODEL][0]
    png_name, png_sha = PICTURE_FILES[os.path.basename(pic["image"]["image_ref"])]
    for route in ("openai", "anthropic", "openrouter"):
        msgs = build_messages(pic, route)
        parts = msgs[-1]["content"]
        need(isinstance(parts, list) and len(parts) == 3 and parts[0]["type"] == "text", f"{route}: picture message shape")
        blob = parts[1]["source"]["data"] if route == "anthropic" else parts[1]["image_url"]["url"].split(",", 1)[1]
        import base64
        need(hashlib.sha256(base64.b64decode(blob)).hexdigest() == png_sha, f"{route}: the picture sent is not the registered PNG")
    row = contract_b_row("T", SELFTEST_IMAGE_MODEL, pic["stim"], pic["cat"], pic["fmt"], pic["order"], pic["codes"],
                         pic["pid"], pic["mode"], None, logged_prompt(pic), pic["image"], draw_index=pic["draw_index"])
    need(row["image_ref"] == png_name and row["image_sha256"] == png_sha
         and row["image_source_svg_sha256"] == pic["image"]["image_sha256"], "picture hashes not recorded")
    need(f"[picture: {png_name}, sha256 {png_sha}]" in row["prompt_text"], "prompt_text does not mark the picture")
    # 14. sequential: the registered opening, the human scripts, deterministic sessions, a growing conversation
    plan = load_session_plan()
    need(len(plan) == SEQ_SESSIONS and all(len(p["trials"]) == SEQ_LEN for p in plan), "session plan size")
    need(all(len({x.rsplit("_t", 1)[0].split("_", 1)[1] for x in p["trials"]}) == SEQ_LEN for p in plan[:180]),
         "a session repeats a category (the human scripts never do)")
    stim_ids = {s["id"] for s in stimuli}
    need(all(t in stim_ids for p in plan for t in p["trials"]), "a script cell is not a stimulus")
    seq = list(iter_specs(stimuli, cats, [SELFTEST_IMAGE_MODEL], arm="sequential"))
    need(len(seq) == SEQ_SESSIONS * SEQ_LEN, "sequential calls per model")
    need(seq[0]["prompt"].startswith(SEQUENTIAL_OPENING + SEQUENTIAL_SEPARATOR) and
         not seq[1]["prompt"].startswith(SEQUENTIAL_OPENING), "the opening must lead the first decision only")
    need(seq == list(iter_specs(stimuli, cats, [SELFTEST_IMAGE_MODEL], arm="sequential")), "sessions not deterministic")
    # 15. per-slot neutral counts equal build_manifest's plan: moved into _draw_checks (2026-09-29), which counts
    # every slot's calls with their repeated draws and its distinct grid points (full arm totals: run.py --count)
    # 17. similarity placement: each placement decodes against its own pair
    sims = [s for s in stimuli if s["structure"] == "SIM"]
    need(all(s.get("sim_placement") == "clone_HF" for s in sims), "base similarity placement is not clone_HF")
    ctf = cat_target_focal_map(stimuli)
    for s in sims:
        pv = (s.get("placement_variants") or {}).get("clone_HD")
        if not pv:
            continue
        # the planted answer: the clone_HD placement's own target, which the old decode scored as COMP
        planted = pv["target"]
        need(decode_choice("SIM", planted, s, pv["options"], ctf, placement="clone_HD") == ("TARGET", True),
             f"{s['id']}: clone_HD target not decoded as TARGET")
        need(decode_choice("SIM", planted, s, pv["options"], ctf) != ("TARGET", True),
             f"{s['id']}: the planted answer does not discriminate the old decode (check is decorative)")
        need(decode_choice("SIM", pv["competitor"], s, pv["options"], ctf, placement="clone_HD") == ("COMP", True),
             f"{s['id']}: clone_HD competitor not decoded as COMP")
        need(decode_choice("SIM", s["target"], s, s["options"], ctf, placement="clone_HF") == ("TARGET", True),
             f"{s['id']}: base clone_HF target not decoded as TARGET")
    # end to end: a dry run's similarity records carry sim_placement and are coded against that placement
    tmp2 = tempfile.mkdtemp(prefix="runpy_selftest_sim_")
    try:
        lp2 = os.path.join(tmp2, "sim.jsonl")
        with contextlib.redirect_stdout(io.StringIO()):
            run_collection(False, 0, 0.0, [SELFTEST_IMAGE_MODEL], "DRYRUN", arm="primary", log_path=lp2, draws="first")
        simrows = [r for r in (json.loads(l) for l in open(lp2, encoding="utf-8")) if r["structure"] == "SIM"]
        need(bool(simrows) and all(r["sim_placement"] in ("clone_HF", "clone_HD") for r in simrows),
             "a similarity record lacks sim_placement")
        need({r["sim_placement"] for r in simrows} == {"clone_HF", "clone_HD"}, "both placements must be present")
        stimmap = {s["id"]: s for s in stimuli}
        wrong = 0
        for r in simrows:
            letter, _ = parse_letter(r["raw_response"], len(r["shown_codes"]))
            if letter is None or r["exclusion_reason"]:
                continue
            code = r["shown_codes"][LETTERS.index(letter)]
            s = stimmap[r["stimulus_id"]]
            pair = s["placement_variants"][r["sim_placement"]] if r["sim_placement"] == "clone_HD" else s
            want = "TARGET" if code == pair["target"] else "COMP" if code == pair["competitor"] else "CLONE"
            wrong += (r["parsed_choice"] != want)
        need(wrong == 0, f"{wrong} similarity records coded against the wrong placement's pair")
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)
    # 18. twelve-option menus: the models get the participants' kind of order,
    # twelve registered FULL shuffles per menu stimulus, never the June tier blocks
    import order_plan as _op
    menus = [s for s in stimuli if len(s["options"]) == 12]
    need(len(menus) == 17, f"{len(menus)} twelve-option menus, expected 17")
    doc = json.load(open(_op.MOT_ORDERS_PATH, encoding="utf-8"))
    need(sorted(doc["orders"]) == sorted(s["id"] for s in menus), "mot_orders.json does not cover exactly the menus")
    tampered = json.loads(json.dumps(doc))
    first = sorted(tampered["orders"])[0]
    tampered["orders"][first][0] = list(reversed(tampered["orders"][first][0]))
    try:
        _op.validate_mot_doc(tampered)
        need(False, "a tampered mot_orders document was accepted")
    except ValueError:
        need(True, "")
    menu_orders = {}
    for sp in iter_specs(stimuli, cats, [SELFTEST_IMAGE_MODEL], arm="primary"):
        if sp["stim"]["structure"] == "MOT" and sp["pid"] == 1 and sp["draw_index"] == 0:
            menu_orders.setdefault(sp["stim"]["id"], []).append(sp["order"])
            texts = {re.sub(r"^\s+[A-L]\. ", "", l) for l in sp["prompt"].split("\n") if re.match(r"\s+[A-L]\. ", l)}
            need(len(texts) == 3 and "Brand" not in sp["prompt"],
                 f"{sp['stim']['id']}: a menu card carries a label participants do not see, or not 3 texts")
    for s in menus:
        ords = menu_orders.get(s["id"], [])
        tiers = [o["tier"] for o in s["options"]]
        need(len(ords) == 12 and len(set(ords)) == 12 and all(sorted(o) == list(range(12)) for o in ords),
             f"{s['id']}: the menu does not run twelve distinct full orders")
        need(ords == _op.mot_shuffle_orders(s["id"]), f"{s['id']}: prompt orders are not the registered draw")
        blocked = sum(1 for o in ords if all(len({tiers[i] for i in o[b * 4:(b + 1) * 4]}) == 1 for b in range(3)))
        need(blocked == 0, f"{s['id']}: {blocked} of its orders keep the quality levels in blocks")
        for t in ("High", "Middle", "Low"):
            spread = {p for o in ords for p, i in enumerate(o) if tiers[i] == t}
            need(len(spread) >= 9, f"{s['id']}: level {t} lands in only {len(spread)} of 12 positions")
    # 19. the participants' explanatory text: every frame carries it verbatim,
    # taken from the stimulus's own registered stem, in its registered place
    want_expl = {"earbuds", "restaurants", "televisions", "hard_drives_pf", "restaurants_pf", "televisions_pf"}
    by_cat = {}
    for s in stimuli:
        by_cat.setdefault(s["category"], set()).add(stem_explanation(s))
    need(all(len(v) == 1 for v in by_cat.values()), "a category's stems disagree on the explanatory text")
    need({c for c, v in by_cat.items() if next(iter(v))} == want_expl,
         f"categories with an explanatory text: {sorted(c for c, v in by_cat.items() if next(iter(v)))}")
    for s in stimuli:
        expl = stem_explanation(s)
        if not expl:
            continue
        need(expl in s["stem"], f"{s['id']}: the explanation is not verbatim from the stem")
        c = catmap[s["category"]]
        for pid in PARAPHRASES:
            full, _ = build_prompt(s, c, orders_for(len(s["options"]), s["id"])[0], pid, "numbers", s["options"])
            head, rest = split_head(full)
            hl = head.split("\n")
            if pid in (1, 2):
                intro = "You are considering the following options:" if pid == 1 else "The available options are:"
                need(len(hl) == 1 and f" {expl} {intro}" in hl[0],
                     f"{s['id']} frame {pid}: the explanation is not just before the options sentence")
            else:
                need(len(hl) == 2 and hl[1] == expl and hl[0].endswith("from these options:"),
                     f"{s['id']} frame 3: the explanation is not the line after the frame")
            need(rest.startswith("  A. "), f"{s['id']} frame {pid}: the options do not follow the question")
    # 16. a sequential conversation survives a failed call and a resume: history rebuilt from the log
    tmp = tempfile.mkdtemp(prefix="runpy_selftest_seq_")
    try:
        lp = os.path.join(tmp, "seq.jsonl")
        with contextlib.redirect_stdout(io.StringIO()):
            ok = _FakeClients()
            run_collection(True, 3, 5.0, [SELFTEST_IMAGE_MODEL], "SELFTEST", clients=ok, arm="sequential", log_path=lp)
            ok2 = _FakeClients()
            run_collection(True, 2, 5.0, [SELFTEST_IMAGE_MODEL], "SELFTEST", clients=ok2, arm="sequential", log_path=lp)
        need(len(ok2.calls) == 2 and len(ok2.calls[0]["messages"]) == 7,
             "resumed trial 4 must carry the 3 logged turns (6 messages) plus its own")
        need(ok2.calls[0]["messages"][0]["content"].startswith(SEQUENTIAL_OPENING), "resumed history lost the opening")
        need([m["role"] for m in ok2.calls[1]["messages"]] == ["user", "assistant"] * 4 + ["user"],
             "conversation roles out of order")
        rows = [json.loads(l) for l in open(lp, encoding="utf-8")]
        need([r["seq_index"] for r in rows] == [1, 2, 3, 4, 5] and all(r["session_id"] == "S0001" for r in rows),
             "sequential rows must carry session S0001 and positions 1..5")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return n, bad

def _draw_checks():
    """The registered repeated draws and settings (see REPEATED DRAWS). Returns (n_checks, failures). The reference
    numbers come from build_manifest.py, which multiplies each model's grid points by its registry draws; this
    enumerates the calls one by one, so the two are independent computations of the same plan."""
    import contextlib, io, tempfile, shutil
    from collections import Counter, defaultdict
    import build_manifest as bm
    bad, n = [], 0
    def need(cond, msg):
        nonlocal n
        n += 1
        if not cond:
            bad.append(msg)
    d = json.load(open(STIM, encoding="utf-8"))
    stimuli, cats = d["stimuli"], d["categories"]
    stimmap = {s["id"]: s for s in stimuli}
    plan = bm.compute_plan()
    # a. every model's draws: a picture prompt six times a text prompt, so a pictures cell (1 order x 3 frames)
    #    carries as many calls as a three-option numbers cell (6 orders x 3 frames)
    three = len(orders_for(3))
    for k, r in MODEL_REGISTRY.items():
        for c in [r["plan"]["primary"]] + r["plan"]["crossed"] + r["plan"]["ladder"]:
            need(c["picture_draws"] == three * c["draws"], f"{k}/{c['setting']}: picture draws are not {three} x draws")
    # b. the repeated arms of the representative models, setting by setting: calls, grid points, draws per grid
    #    point, the draw-major order, cell sizes, unique record ids (a draw or setting never resumes as another)
    for k in representative_models():
        for arm in ("primary", "crossed", "ladder"):
            for s in arm_settings(k, arm):
                tag = f"{k}/{arm}/{s}"
                specs = list(iter_specs(stimuli, cats, [k], arm=arm, setting=s))
                w_txt, w_pic = draws_for(arm, "numbers", k, s), draws_for(arm, "pictures", k, s)
                gkey = lambda sp: (sp["stim"]["id"], sp["fmt"], sp["order"], sp["pid"])
                draws = defaultdict(list)
                for sp in specs:
                    draws[gkey(sp)].append(sp["draw_index"])
                pic = [g for g in draws if g[1] == "pictures"]
                txt = [g for g in draws if g[1] != "pictures"]
                need(len(specs) == plan["calls"][k][(arm, s)], f"{tag}: runner {len(specs)} calls, manifest "
                     f"{plan['calls'][k][(arm, s)]}")
                need(len(draws) == plan["per_model"][k], f"{tag}: {len(draws)} grid points, manifest {plan['per_model'][k]}")
                need(len(pic) == (9 * len(PARAPHRASES) if MODEL_REGISTRY[k]["accepts_images"] else 0),
                     f"{tag}: {len(pic)} picture prompts")
                need(all(draws[g] == list(range(w_txt)) for g in txt),
                     f"{tag}: a text grid point is not called {w_txt} times (draw_index 0..{w_txt - 1})")
                need(all(draws[g] == list(range(w_pic)) for g in pic),
                     f"{tag}: a picture prompt is not called {w_pic} times (draw_index 0..{w_pic - 1})")
                need(all(sp["setting"] == s and sp["arm"] == arm for sp in specs), f"{tag}: a spec lost its setting")
                di = [sp["draw_index"] for sp in specs]
                need(di == sorted(di), f"{tag}: the plan is not draw-major")
                block0 = [gkey(sp) for sp in specs[:len(draws)]]
                need(all(x == 0 for x in di[:len(draws)]) and len(set(block0)) == len(draws),
                     f"{tag}: draw 0 is not the whole grid, once, first")
                by_draw = defaultdict(list)
                for sp in specs:
                    by_draw[sp["draw_index"]].append(gkey(sp))
                need(all(by_draw[dd] == [g for g in block0 if len(draws[g]) > dd] for dd in by_draw),
                     f"{tag}: a later draw does not keep the registered grid order")
                cell = Counter((sp["stim"]["id"], sp["fmt"]) for sp in specs)
                for (sid, f), c in cell.items():
                    if f == "pictures":
                        need(c == len(PARAPHRASES) * w_pic, f"{tag}: pictures cell {sid} carries {c} calls")
                        if len(stimmap[sid]["options"]) == 3:
                            need(c == cell[(sid, "numbers")],
                                 f"{tag}: pictures cell {sid} carries {c} calls, its numbers cell {cell[(sid, 'numbers')]}")
                rids = [spec_record_id("SELFTEST", sp) for sp in specs]
                need(len(set(rids)) == len(rids), f"{tag}: two calls share a record_id")
                s0 = specs[0]
                need(rids[0] == record_id("SELFTEST", k, s0["stim"]["id"], s0["fmt"], s0["order"], s0["pid"], s0["mode"],
                                          s0["persona"], arm, None, 0, s), f"{tag}: draw 0's record_id changed form")
    # c. the same grid point at two settings, and in the primary arm, never shares a record_id; a crossed call
    #    without its setting is refused at the record_id
    m = SELFTEST_IMAGE_MODEL
    sp = next(iter_specs([stimmap["FRQ_bluetooth_speakers_t2"]], cats, [m], arm="primary"))
    ids = {record_id("SELFTEST", m, sp["stim"]["id"], sp["fmt"], sp["order"], sp["pid"], "neutral", None, arm, None, 0, s)
           for arm, s in [("primary", "OFF")] + [("crossed", x) for x in arm_settings(m, "crossed")]
           + [("ladder", x) for x in arm_settings(m, "ladder")]}
    need(len(ids) == 1 + len(arm_settings(m, "crossed")) + len(arm_settings(m, "ladder")),
         "two settings of one grid point share a record_id")
    try:
        record_id("SELFTEST", m, "x", "numbers", (0, 1, 2), 1, "neutral", None, "crossed")
        need(False, "a crossed record_id was built without its setting")
    except ValueError:
        need(True, "")
    # d. the arms that do not repeat: every call is draw 0, every grid point once, at the primary setting
    sub = [stimmap["FRQ_bluetooth_speakers_t2"]]            # numbers, words and a picture: 39 grid points
    for arm in ("persona", "temp_0", "temp_1", "sequential", "recognition"):
        pool = stimuli if arm in ("sequential", "recognition") else sub
        specs = list(iter_specs(pool, cats, [m], arm=arm))
        need(bool(specs) and all(x["draw_index"] == 0 for x in specs), f"{m}/{arm}: a one-call arm repeats a draw")
        need(all(x["setting"] == MODEL_REGISTRY[m]["plan"]["primary"]["setting"] for x in specs),
             f"{m}/{arm}: a one-call arm left the primary setting")
        rids = [spec_record_id("SELFTEST", x) for x in specs]
        need(len(set(rids)) == len(rids), f"{m}/{arm}: two calls share a record_id")
    need(not list(iter_specs(sub, cats, ["gpt-6.2-astra"], arm="persona")), "a premium model yields persona calls")
    # e. the live loop, offline, every draw of one stimulus: each draw its own API call, no history, each row holding
    #    its own call's answer; a finished log re-calls nothing; a half-finished one completes the rest
    sid = "FRQ_bluetooth_speakers_t2"
    specs = list(iter_specs(sub, cats, [m], arm="primary"))
    plan_rids = [spec_record_id("SELFTEST", x) for x in specs]
    wt, wp = draws_for("primary", "numbers", m), draws_for("primary", "pictures", m)
    tmp = tempfile.mkdtemp(prefix="runpy_selftest_draws_")
    try:
        lp = os.path.join(tmp, "draws.jsonl")
        fc = _FakeClients(alternate=True)
        with contextlib.redirect_stdout(io.StringIO()):
            s = run_collection(True, 0, 5.0, [m], "SELFTEST", clients=fc, arm="primary", log_path=lp,
                               stimulus_ids={sid})
        rows = [json.loads(l) for l in open(lp, encoding="utf-8")] if os.path.exists(lp) else []
        need(s["written"] == len(specs) == len(rows) == len(fc.calls) and s["skipped"] == 0,
             f"live loop: {len(specs)} registered calls, {s['written']} written, {len(fc.calls)} API calls, "
             f"{s['skipped']} skipped (every draw is its own call)")
        need(all(len(c["messages"]) == 1 for c in fc.calls), "a repeated draw was sent with conversation history")
        need(len(set(fc.p.replies)) == 2 and [r["raw_response"] for r in rows] == fc.p.replies,
             "a row does not hold the answer of its own call (an answer reused across draws)")
        need([r.get("draw_index") for r in rows] == [x["draw_index"] for x in specs],
             "rows do not carry the registered draw_index")
        need([r["record_id"] for r in rows] == plan_rids, "row record_ids differ from the plan's")
        need(Counter(r["format"] for r in rows) == Counter({"numbers": 18 * wt, "words": 18 * wt, "pictures": 3 * wp}),
             "the stimulus's numbers, words and pictures cells do not carry equal calls")
        fc2 = _FakeClients()
        with contextlib.redirect_stdout(io.StringIO()):
            s2 = run_collection(True, 0, 5.0, [m], "SELFTEST", clients=fc2, arm="primary", log_path=lp,
                                stimulus_ids={sid})
        need(s2["written"] == 0 and not fc2.calls and s2["skipped"] == len(specs), "resume re-called finished draws")
        lp3 = os.path.join(tmp, "partial.jsonl")
        with contextlib.redirect_stdout(io.StringIO()):
            run_collection(True, 50, 5.0, [m], "SELFTEST", clients=_FakeClients(), arm="primary",
                           log_path=lp3, stimulus_ids={sid})
            s3 = run_collection(True, 0, 5.0, [m], "SELFTEST", clients=_FakeClients(), arm="primary",
                                log_path=lp3, stimulus_ids={sid})
        rows3 = [json.loads(l) for l in open(lp3, encoding="utf-8")]
        need(s3["written"] == len(specs) - 50 and [r["record_id"] for r in rows3] == plan_rids,
             "a resumed run did not complete exactly the missing draws, in plan order")
        try:
            run_collection(True, 1, 5.0, [m], "SELFTEST", clients=_FakeClients(), arm="primary",
                           log_path=os.path.join(tmp, "first.jsonl"), draws="first", stimulus_ids={sid})
            need(False, "a live run accepted draws='first'")
        except ValueError:
            need(True, "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # f. a record without draw_index is refused at the one place records are built
    catmap = {c["id"]: c for c in cats}
    try:
        contract_b_row("T", m, sub[0], catmap[sub[0]["category"]], "numbers", (0, 1, 2),
                       ["TARGET", "DECOY", "COMP"], 1, "neutral", None, "p", None)
        need(False, "contract_b_row wrote a record without draw_index")
    except ValueError:
        need(True, "")
    return n, bad

def _payload_checks(need):
    """Every request payload the runner can send: every model, every arm and setting it runs."""
    for k, reg in MODEL_REGISTRY.items():
        for arm, s in arm_calls(k):
            q = build_request(k, arm, setting=s)
            kw, eb = q["kwargs"], q["kwargs"].get("extra_body", {})
            params = reg["settings"][s]
            tag = f"{k}/{arm}/{s}"
            need(q["setting"] == s and q["route"] == reg["route"], f"{tag}: wrong setting or route")
            need(q["model_id"] == reg["model_id"], f"{tag}: the id sent is not the registered model_id")
            # temperature: only in the two temperature arms, only to a model that accepts one
            if arm in ARM_TEMPERATURE:
                need(kw.get("temperature") == ARM_TEMPERATURE[arm] and reg["accepts_temperature"],
                     f"{tag}: arm temperature not sent, or sent to a model that does not accept one")
            else:
                need("temperature" not in kw, f"{tag}: temperature sent outside the temperature arms")
            need(q["temperature_requested"] == kw.get("temperature"), f"{tag}: temperature_requested differs")
            if reg["rejects_temperature"]:
                need("temperature_not_sent" in q["sampling_requested"], f"{tag}: rejection fact not recorded")
            # the setting's parameters are sent exactly, and DEFAULT sends no reasoning parameter at all
            sent = {}
            if reg["route"] == "anthropic":
                if "thinking" in kw:
                    sent["thinking"] = kw["thinking"]
            elif "reasoning_effort" in kw:
                sent["reasoning_effort"] = kw["reasoning_effort"]
            sent.update({x: v for x, v in eb.items() if x != "provider"})
            need(sent == params, f"{tag}: sent {sent}, registered {params}")
            if s == "DEFAULT":
                blob = json.dumps({x: v for x, v in kw.items() if x != "extra_body"}) + json.dumps(sent)
                need(not any(w in blob for w in ("reasoning", "thinking", "effort", "chat_template_kwargs")),
                     f"{tag}: DEFAULT sent a reasoning parameter")
            # the output ceiling sent is the registered one
            want_max = reg["max_tokens"][s]
            if arm == "recognition":
                want_max = max(want_max, PROBE_ANSWER_TOKENS)
            tok = "max_completion_tokens" if reg["route"] == "openai" else "max_tokens"
            need(kw.get(tok) == want_max == q["max_tokens"], f"{tag}: output ceiling sent {kw.get(tok)}, registered {want_max}")
            need(q["max_tokens"] >= (1024 if s != "OFF" else 16), f"{tag}: a reasoning setting without room to think")
            if reg["route"] == "openrouter":
                need(eb.get("provider") == reg["provider_pin"], f"{tag}: provider pin missing or altered")

def selftest():
    import copy
    checks, failures = 0, []
    def need(cond, msg):
        nonlocal checks
        checks += 1
        if not cond:
            failures.append(msg)
    # 1. the real registry passes every rule
    probs = validate_registry(MODEL_REGISTRY)
    need(not probs, "real registry breaks rules: " + "; ".join(probs))
    # 2. planted faults: each mutated copy must be refused (the checks are alive)
    def mutated(fn):
        reg = copy.deepcopy(MODEL_REGISTRY)
        fn(reg)
        return validate_registry(reg)
    def plan(R, k):
        return R[k]["plan"]
    faults = {
        "Claude Opus 5.5 put in the temperature arms": lambda R: plan(R, "claude-opus-5-5").update(temperature=True),
        "GPT-6.2 Sol's primary raised above its lowest setting": lambda R: plan(R, "gpt-6.2-sol")["primary"].update(
            setting="DEFAULT"),
        "OFF sends nothing on a model that reasons": lambda R: R["qwen35-27b"]["settings"].update(OFF={}),
        "a reasoning setting left at the June 10-token cap": lambda R: R["gpt-6.2-sol"]["max_tokens"].update(LOW=10),
        "an open model without its revision": lambda R: R["qwen25-7b"].update(hf_revision=None),
        "an OpenRouter pin that allows fallbacks": lambda R: R["qwen4-max"].update(
            provider_pin=dict(R["qwen4-max"]["provider_pin"], allow_fallbacks=True)),
        "an OpenRouter model without require_parameters": lambda R: R["muse-wonder"].update(
            provider_pin=dict(R["muse-wonder"]["provider_pin"], require_parameters=False)),
        "a crossed setting the model does not offer": lambda R: plan(R, "gpt-6.2-sol")["crossed"].append(
            {"setting": "OFF", "draws": 1, "picture_draws": 6}),
        "a premium model given personas": lambda R: plan(R, "gpt-6.2-astra").update(persona=True),
        "a settings map missing one of its levels": lambda R: R["claude-haiku-5-5"]["settings"].pop("MAX"),
        "Anthropic given reasoning_effort": lambda R: R["claude-opus-5-5"]["settings"].update(
            LOW={"reasoning_effort": "low"}),
        "a previous closed model marked new": lambda R: R["gpt-5.4-mini"].update(generation="new"),
        "an entry without its family": lambda R: R["grok-4.7"].pop("family"),
        "picture draws not six times the text draws": lambda R: plan(R, "gpt-6-luna")["primary"].update(picture_draws=10),
        "one setting run twice": lambda R: plan(R, "gpt-6-luna")["crossed"].append(
            dict(plan(R, "gpt-6-luna")["crossed"][0])),
        "an open model sent to a closed route": lambda R: R["qwen25-7b"].update(route="openrouter",
                                                                                provider="openrouter"),
    }
    caught = 0
    for name, fn in faults.items():
        got = mutated(fn)
        need(bool(got), f"planted fault NOT caught: {name}")
        caught += bool(got)
    # 3. every request payload the runner can send
    _payload_checks(need)
    # 4. arms and settings a model does not run are refused by the request builder
    for k, arm, s in (("claude-opus-5-5", "temp_0", None), ("gpt-6.2-astra", "persona", None),
                      ("gpt-6.2-sol", "crossed", "MAX"), ("qwen25-7b", "crossed", None),
                      ("gpt-6-luna", "persona", "HIGH")):
        try:
            build_request(k, arm, setting=s)
            need(False, f"{k}/{arm}/{s}: an arm or setting the model does not run was built")
        except ValueError:
            need(True, "")
    # 5. the id-drift check: dated alias resolution passes, another model fails
    astra = MODEL_REGISTRY["gpt-6.2-astra"]
    need(echo_ok(astra, "gpt-6.2-astra", "gpt-6.2-astra-2026-11-17"), "dated echo refused")
    need(not echo_ok(astra, "gpt-6.2-astra", "gpt-6.2-sol"), "a different model passed the echo check")
    need(not echo_ok(astra, "gpt-6.2-astra", "gpt-6.2-astra-pro"), "the pro variant passed the echo check")
    neon = MODEL_REGISTRY["gemini-4-neon"]
    need(echo_ok(neon, "gemini-4-neon", "models/gemini-4-neon"), "Google's models/<id> echo refused")
    need(not echo_ok(neon, "gemini-4-neon", "models/gemini-4-carbon"), "another Gemini model passed the echo check")
    need(echo_ok(MODEL_REGISTRY["qwen4-max"], "qwen/qwen4-max", "qwen/qwen4-max-20261116"),
         "an OpenRouter dated slug refused")
    # 6. the arms follow the registry plans
    need(models_for_arm("primary") == PRIMARY_LINEUP, "primary arm size")
    need(len(models_for_arm("persona")) == sum(1 for r in MODEL_REGISTRY.values() if r["plan"]["persona"]),
         "persona arm size")
    need(set(models_for_arm("temp_0")) == {k for k, r in MODEL_REGISTRY.items() if r["plan"]["temperature"]},
         "temperature arm membership")
    need(all(r["plan"]["crossed"] == [] for k, r in MODEL_REGISTRY.items() if len(r["levels"]) == 1),
         "a model with one setting runs a crossed condition")
    # 7. each arm and setting logs to its own file; only the primary arm writes the confirmatory model_log.jsonl
    combos = [(arm, s) for arm in ARMS for s in (SETTINGS if arm in SETTING_ARMS else [None])]
    paths = {c: log_path_for(c[0], setting=c[1]) for c in combos}
    need(len(set(paths.values())) == len(combos), "two arms or settings share a log file")
    need(os.path.basename(paths[("primary", None)]) == "model_log.jsonl", "primary arm must write model_log.jsonl")
    # 8. every route has its base URL and key names; the vllm route takes its address from the environment only
    need(set(r["route"] for r in MODEL_REGISTRY.values()) <= set(ROUTE_BASE), "a model's route is not defined")
    saved = os.environ.pop("VLLM_BASE_URL", None)
    try:
        Clients().client("vllm")
        need(False, "the vllm route ran without VLLM_BASE_URL")
    except RuntimeError:
        need(True, "")
    finally:
        if saved is not None:
            os.environ["VLLM_BASE_URL"] = saved
    # 9. call_model and the live loop, offline, through fake clients
    for msg in _offline_call_checks():
        need(False, msg)
    checks += 1
    # 10-17. registered materials, the probe, pictures, sequential sessions
    n_extra, extra_bad = _materials_and_arms_checks()
    checks += n_extra
    for msg in extra_bad:
        need(False, msg)
    # 18. the repeated draws and settings
    n_draw, draw_bad = _draw_checks()
    checks += n_draw
    for msg in draw_bad:
        need(False, msg)
    if failures:
        print(f"SELFTEST FAIL: {len(failures)} of {checks} checks failed")
        for f in failures:
            print("  -", f)
        return 1
    print(f"SELFTEST PASS: {checks} checks; {caught} of {len(faults)} planted registry faults refused; "
          f"{len(MODEL_REGISTRY)} models, roster of {IDS_VERIFIED_ON}. No network, no cost.")
    return 0

# ===================================================================================================
# SYNTHETIC RESPONDER (dry-run): produces a deterministic, plausible chosen LETTER per call WITHOUT any
# network. Deterministic in the record_id so re-runs are byte-identical; a small, fixed fraction of calls
# are turned into refusals / unparseable replies so the dry run exercises the exclusion accounting too.
# This lets the WHOLE loop (parse -> decode -> contract-B row -> resume skip -> cost guard) run offline.
# ===================================================================================================
def synthetic_response(spec, rid):
    """Return (raw_text, echoed_model_id) for a dry-run call. Picks a shown letter deterministically;
    1-in-40 calls return a refusal and 1-in-40 an unparseable blob, to exercise exclusion handling."""
    h = int(hashlib.sha1(rid.encode()).hexdigest(), 16)
    n = len(spec["codes"])
    if h % 40 == 0:
        return "I'm sorry, I cannot choose for you.", MODEL_REGISTRY[spec["model_key"]]["api_id"]
    if h % 40 == 1:
        return "(no clear preference)", MODEL_REGISTRY[spec["model_key"]]["api_id"]
    if spec.get("kind") == "probe":
        reply = f"1: YES; 2: {LETTERS[h % n]}" if h % 2 else "1: NO; 2: NONE"
        return reply, MODEL_REGISTRY[spec["model_key"]]["api_id"]
    letter = LETTERS[h % n]
    # id-drift probe: 1-in-50 dry-run calls echo a drifted id so the id_drift exclusion path is exercised.
    echoed = MODEL_REGISTRY[spec["model_key"]]["api_id"]
    if h % 50 == 7:
        echoed = echoed + "-DRIFT"
    return letter, echoed

# ===================================================================================================
# THE LOOP. Shared by dry-run and live: iterate the manifest, (synth or real) call, parse, decode, build
# the contract-B row, and append it. Resume-skips existing record_ids; enforces the cost cap; records
# refusals, unparseable replies, and id-drift as exclusions; flushes each row so a crash loses nothing.
# ===================================================================================================
def log_path_for(arm, out_dir=None, setting=None):
    """Each arm writes its OWN log: the primary arm to model_log.jsonl (the confirmatory grid analyze.py reads),
    a crossed or ladder arm to model_log_<arm>_<setting>.jsonl, every other arm to model_log_<arm>.jsonl. Separate
    files keep the other settings and the temperature re-runs out of the confirmatory estimates by construction;
    analyze.py also separates them by arm (split_arms)."""
    if arm == "primary":
        name = "model_log.jsonl"
    elif arm in SETTING_ARMS:
        if setting not in SETTINGS:
            raise ValueError(f"a {arm} log is per setting (got {setting!r})")
        name = f"model_log_{arm}_{setting}.jsonl"
    else:
        name = f"model_log_{arm}.jsonl"
    return os.path.join(out_dir or HERE, name)

class CallsAhead:
    """Keeps up to `window` calls in flight on a thread pool, in plan order; get(rid) returns one call's result,
    waiting for it if needed, and submits the next. Used by run_collection for the vllm route only."""
    def __init__(self, clients, specs, run_id, window):
        from concurrent.futures import ThreadPoolExecutor
        self.clients, self.specs, self.run_id, self.window = clients, list(specs), run_id, window
        self.pool = ThreadPoolExecutor(max_workers=window)
        self.futures, self.next = {}, 0
        self._fill()

    def _fill(self):
        while self.next < len(self.specs) and len(self.futures) < self.window:
            sp = self.specs[self.next]
            self.futures[spec_record_id(self.run_id, sp)] = self.pool.submit(call_model, self.clients, sp)
            self.next += 1

    def get(self, rid):
        fut = self.futures.pop(rid, None)
        if fut is None:
            return None          # beyond the calls planned ahead (max_calls reached once failed calls are counted)
        res = fut.result()
        self._fill()
        return res

    def close(self):
        self.pool.shutdown(wait=True, cancel_futures=True)


def run_collection(live, max_calls, cost_cap, models, run_id, clients=None, arm="primary", log_path=None,
                   draws="all", stimulus_ids=None, setting=None, concurrency=1, results=None):
    """The collection loop. draws="first" (dry runs only) keeps draw_index 0; a live run refuses it, so a live
    collection always runs every registered draw. A crossed or ladder arm runs one setting per call of this function
    (its own log). stimulus_ids (neutral arms only; the selftest uses it) restricts the loop to those stimuli.
    results (batch mode, batch.py): {record_id: the call's result} read back from finished batches; the loop then
    makes no call at all, writes a row for every planned call that has a result, and leaves the others for later."""
    if results is not None and (not live or arm == "sequential" or concurrency > 1):
        raise ValueError("batch results are read into a live log, for arms without a conversation, one at a time")
    if live and draws != "all":
        raise ValueError("a live run collects every registered draw (draws='all')")
    if arm in SETTING_ARMS and setting not in SETTINGS:
        raise ValueError(f"the {arm} arm runs one setting at a time; name it (one of {SETTINGS})")
    log_path = log_path or log_path_for(arm, setting=setting)
    d = json.load(open(STIM, encoding="utf-8"))
    stimuli, cats = d["stimuli"], d["categories"]
    if stimulus_ids is not None:
        if arm not in NEUTRAL_ARMS:
            raise ValueError("stimulus_ids restricts a neutral-grid arm only")
        stimuli = [s for s in stimuli if s["id"] in stimulus_ids]

    # resume-on-crash: read the record_ids already logged so a re-run continues where it stopped.
    # LOG INTEGRITY: one log holds ONE run. A live run refuses a log that
    # holds rows of any other run_id (the tracked dry-run rows are run_id DRYRUN; a pre-acceptance smoke has
    # its own run_id), so synthetic or smoke rows can never be pooled with, or resumed into, real data.
    seen, foreign, seen_raw = set(), {}, {}
    if os.path.exists(log_path):
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    seen.add(row["record_id"])
                    if row.get("prompting_mode") == "sequential":     # rebuilds a session's conversation
                        seen_raw[row["record_id"]] = row.get("raw_response") or ""
                    if row.get("run_id") != run_id:
                        foreign[row.get("run_id")] = foreign.get(row.get("run_id"), 0) + 1
    if live and foreign:
        sys.exit(f"[run] REFUSING: {log_path} already holds rows of other runs {foreign}. A live run writes only "
                 f"to a log of its own run_id ({run_id!r}): move that file aside, or pass --out-dir.")
    print(f"[run] mode={'LIVE' if live else 'DRY-RUN'} run_id={run_id} arm={arm} setting={setting or 'primary'} "
          f"draws={draws}  resume: {len(seen)} record_ids already logged")

    # Failed API calls (a raised error, no reply) are NOT written to the data log and NOT marked seen, so the
    # next run retries them; each one is recorded in <log>.errors.jsonl. The SDKs already retry 429/5xx twice.
    # MAX_CONSECUTIVE_ERRORS in a row stops the run (a dead key or route, not a flaky call).
    err_path = log_path[:-len(".jsonl")] + ".errors.jsonl"
    MAX_CONSECUTIVE_ERRORS = 20
    consecutive_errors = errors = 0
    cost_so_far = 0.0
    written = refusals = unparsed = id_drift = skipped = 0
    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
        with open(log_path, "rb") as fb:                     # a hard kill can leave a partial last line;
            fb.seek(-1, os.SEEK_END)                          # start the next row on a fresh line
            needs_newline = fb.read(1) != b"\n"
    else:
        needs_newline = False
    out = open(log_path, "a", encoding="utf-8", newline="\n")
    if needs_newline:
        out.write("\n")
    # Sequential sessions are conversations: the history of each (model, session) holds every earlier user
    # message and the model's answer. On resume, a logged trial's answer is replayed from the log into the
    # history; a failed call abandons the rest of that session for this run (retried next run, history rebuilt).
    histories, broken = {}, set()
    ahead = None
    if live and concurrency > 1:
        # Concurrent calls (the open models on the supercomputer: a runner that sends one call at a time leaves the cards
        # idle). Only on the vllm route, which costs no dollars, so the cost cap cannot be overrun by calls in
        # flight, and never for sequential sessions, whose calls depend on the answers before them. The rows are
        # still written in plan order, and max_calls bounds the calls made.
        if arm == "sequential" or any(MODEL_REGISTRY[m]["route"] != "vllm" for m in models):
            raise ValueError("concurrent calls are for the vllm route and for arms without a conversation")
        pending = [sp for sp in iter_specs(stimuli, cats, models, arm=arm, draws=draws, setting=setting)
                   if spec_record_id(run_id, sp) not in seen]
        ahead = CallsAhead(clients, pending[:max_calls] if max_calls else pending, run_id, concurrency)
    for spec in iter_specs(stimuli, cats, models, arm=arm, draws=draws, setting=setting):
        rid = spec_record_id(run_id, spec)
        skey = (spec["model_key"], spec["session"]["session"]) if spec.get("session") else None
        if skey is not None:
            if skey in broken:
                continue
            spec["history"] = histories.setdefault(skey, [])
        if rid in seen:
            if skey is not None:
                spec["history"].extend([{"role": "user", "content": spec["prompt"]},
                                        {"role": "assistant", "content": seen_raw.get(rid, "")}])
            skipped += 1
            continue
        if max_calls and written >= max_calls:
            print(f"[run] max-calls reached ({max_calls}); stopping.")
            break

        reg = MODEL_REGISTRY[spec["model_key"]]
        served = None
        if results is not None and rid not in results:
            continue                            # this call's batch has not returned it yet
        if live:
            # cost cap: stop BEFORE a call whose worst case (input at ~3 chars per token, plus the full output
            # ceiling at the output price) would take the session past the cap.
            chars = len(spec["prompt"]) + sum(len(m["content"]) for m in spec.get("history") or [])
            worst = worst_case_cost(spec["model_key"], arm, chars, n_images=int(spec["fmt"] == "pictures"),
                                    setting=spec["setting"])
            if cost_so_far + worst > cost_cap:
                print(f"[run] COST CAP: cost ${cost_so_far:.4f}; the next call could cost up to ${worst:.4f}, which "
                      f"would pass the ${cost_cap:.2f} cap. Stopping cleanly.")
                break
            res = results[rid] if results is not None else (ahead.get(rid) if ahead else call_model(clients, spec))
            if res is None:      # review finding m4: the calls planned ahead are used up; stop as max_calls would
                print(f"[run] max-calls reached ({max_calls}) with calls in flight; stopping.")
                break
            if res["error"] is not None:
                errors += 1
                consecutive_errors += 1
                if skey is not None:
                    broken.add(skey)            # the conversation cannot continue without this answer
                with open(err_path, "a", encoding="utf-8", newline="\n") as ef:
                    ef.write(json.dumps({"record_id": rid, "run_id": run_id, "model_key": spec["model_key"],
                                         "arm": arm, "setting": spec["setting"],
                                         "model_id_requested": res["model_id_requested"], "error": res["error"],
                                         "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                                        ensure_ascii=False) + "\n")
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS and results is None:   # a batch is read whole
                    print(f"[run] {consecutive_errors} API errors in a row (last: {res['error'][:200]}); stopping. "
                          f"See {os.path.basename(err_path)}.")
                    break
                continue
            consecutive_errors = 0
            raw, echoed = res["raw_response"], res["model_id_echoed"]
            sampling_eff, latency, cost = res["sampling_params_effective"], res["latency_ms"], res["cost_usd"]
            requested_id, flavor, route = res["model_id_requested"], res["api_flavor"], res["route"]
            reason_req, reason_eff, temp_req = (res["reasoning_requested"], res["reasoning_effective"],
                                                res["temperature_requested"])
            served = res.get("served")
            cost_so_far += cost or 0.0
            ts = None   # live: real wall-clock timestamp (contract_b_row fills it from time.gmtime())
        else:
            # dry run: the SAME request builder the live path uses, so the log shows exactly what a live run
            # would send.
            req = build_request(spec["model_key"], arm, setting=spec["setting"])
            msgs = build_messages(spec, req["route"])      # exercised offline too (pictures, history)
            raw, echoed = synthetic_response(spec, rid)
            sampling_eff = dict(req["sampling_requested"], note="dry_run_synthetic")
            if skey is not None:
                sampling_eff["messages_in_conversation"] = len(msgs)
            requested_id, flavor, route = req["model_id"], req["api_flavor"], req["route"]
            reason_req, reason_eff, temp_req = req["reasoning_requested"], {"note": "dry_run_synthetic"}, \
                req["temperature_requested"]
            latency, cost = 1, 0.0
            ts = DRY_RUN_TIMESTAMP   # dry-run: a STABLE timestamp so two dry-runs are byte-identical

        if skey is not None:
            if live:
                sampling_eff["messages_in_conversation"] = len(spec["history"]) + 1
            spec["history"].extend([{"role": "user", "content": spec["prompt"]},
                                    {"role": "assistant", "content": raw or ""}])

        # parse: a probe reply through parse_probe and score_probe; a choice letter through the shared codebook.
        excl_flag, excl_reason, parsed, probe = False, "", None, None
        if spec.get("kind") == "probe":
            q1, q2, parse_method = parse_probe(raw, len(spec["codes"]))
            if q1 is None:
                excl_flag = True
                if looks_like_refusal(raw):
                    excl_reason, refusals = "refusal", refusals + 1
                else:
                    excl_reason, unparsed = "unparseable", unparsed + 1
                probe = {"probe_q1": None, "probe_q2": None, "recognition": None}
            else:
                parsed = q1
                probe = score_probe(spec["stim"]["structure"], q1, q2, spec["codes"])
            letter = None
        else:
            letter, parse_method = parse_letter(raw, len(spec["codes"]))
            if letter is not None and parse_method != "exact" and needs_exact_reply(reg):
                # a model that reasons with no reasoning parser may return its reasoning in the answer, where the
                # fallback pattern would read a word such as "a" as a letter: such a reply is unreadable
                letter, parse_method = None, "fallback_refused"
        if spec.get("kind") == "probe":
            pass
        elif letter is None:
            excl_flag = True
            if looks_like_refusal(raw):
                excl_reason, refusals = "refusal", refusals + 1
            else:
                excl_reason, unparsed = "unparseable", unparsed + 1
            parse_method = "failed" if parse_method != "fallback_refused" else parse_method
        else:
            code = spec["codes"][LETTERS.index(letter)]
            parsed, valid = decode_choice(spec["stim"]["structure"], code, spec["stim"], spec["opts"],
                                          cat_target_focal=spec["cat_target_focal"],
                                          placement=sim_placement_of(spec["stim"], spec["fmt"]))
            if not valid:
                excl_flag, excl_reason = True, "unparseable"   # phantom / impossible decode

        # id-drift: an echoed id that does not name the registered model is an exclusion flag per CONTRACTS B
        # (kept, recorded). echo_ok accepts the id sent, the registered echo ids, and a dated form of the id.
        if echoed and requested_id and not echo_ok(reg, requested_id, echoed):
            id_drift += 1
            if not excl_flag:
                excl_flag, excl_reason = True, "id_drift"
            else:
                excl_reason = excl_reason + "+id_drift"

        row = contract_b_row(
            run_id, spec["model_key"], spec["stim"], spec["cat"], spec["fmt"], spec["order"], spec["codes"],
            spec["pid"], spec["mode"], spec["persona"], logged_prompt(spec), spec["image"],
            provider=route, api_flavor=flavor,
            model_id_requested=requested_id, model_id_echoed=echoed,
            temperature_requested=temp_req, sampling_params_effective=sampling_eff,
            raw_response=(raw if raw is not None else ""), parsed=parsed, parse_method=parse_method,
            exclusion_flag=excl_flag, exclusion_reason=excl_reason, latency_ms=latency, cost_usd=cost,
            timestamp=ts, arm=arm, reasoning_requested=reason_req, reasoning_effective=reason_eff,
            session=spec.get("session"), probe=probe, draw_index=spec["draw_index"], setting=spec["setting"],
            served=served)
        out.write(json.dumps(row, ensure_ascii=False) + "\n")
        out.flush()
        seen.add(rid)
        written += 1
    out.close()
    if ahead:
        ahead.close()
    print(f"[run] wrote {written} new rows -> {os.path.basename(log_path)}  (skipped {skipped} already-logged; "
          f"refusals {refusals}, unparseable {unparsed}, id_drift {id_drift}; API errors {errors}, left for retry; "
          f"cost_so_far ${cost_so_far:.4f})")
    return dict(written=written, skipped=skipped, refusals=refusals, unparsed=unparsed,
                id_drift=id_drift, errors=errors, cost_so_far=cost_so_far)

IMAGE_TOKEN_ALLOWANCE = 2000        # generous per-picture input allowance for the cost cap (1224 px PNGs)

def worst_case_cost(model_key, arm, chars, n_images=0, setting=None):
    """Upper bound on one call's cost: the conversation's characters at ~3 per token (generous), a fixed
    allowance per picture, plus the call's full output ceiling at the output price. Used by the cost cap
    BEFORE each live call. `chars` may be a prompt string or a character count."""
    reg = MODEL_REGISTRY[model_key]
    p_in, p_out = reg["price_per_1m"]
    n_chars = len(chars) if isinstance(chars, str) else chars
    max_out = build_request(model_key, arm, setting=setting)["max_tokens"]
    return ((n_chars / 3.0 + 50 + n_images * IMAGE_TOKEN_ALLOWANCE) * p_in + max_out * p_out) / 1e6

def preflight(models):
    """Per-route preflight for a live run: every route the run will use has its key (or, for vllm, its server
    address) in the environment and its SDK importable. Returns a list of problems (empty = ready)."""
    problems, need = [], {}
    for k in models:
        need.setdefault(route_for(MODEL_REGISTRY[k]), []).append(k)
    for route, ks in need.items():
        names = ", ".join(ks[:4]) + (f" and {len(ks) - 4} more" if len(ks) > 4 else "")
        if route == "vllm":
            if not (os.environ.get("VLLM_BASE_URL") or os.environ.get("VLLM_BASE_URLS")):
                problems.append(f"route vllm ({names}): no VLLM_BASE_URL in the environment (the open-model server's job sets it)")
        elif not any(os.environ.get(x) for x in ROUTE_KEYS[route]):
            problems.append(f"route {route} ({names}): no {' or '.join(ROUTE_KEYS[route])} in the environment")
        try:
            __import__(ROUTE_SDK[route])
        except ImportError:
            problems.append(f"route {route} ({names}): the '{ROUTE_SDK[route]}' Python package is not installed")
    return problems

SAMPLE_MODEL = SELFTEST_IMAGE_MODEL

def write_sample_prompts(sample_path=None):
    """Human-readable check: one distinct prompt per (structure x format), printed and saved to
    SAMPLE_CALLS.jsonl. No network, no cost. Complements the dry-run model_log.jsonl."""
    sample_path = sample_path or SAMPLE_PATH
    d = json.load(open(STIM, encoding="utf-8"))
    stimuli, cats = d["stimuli"], d["categories"]
    seen, samples, printed = set(), [], 0
    m = SAMPLE_MODEL
    def picked():
        # one per (structure x format) of the neutral grid (all draw_index 0), one repeated draw (the first picture
        # prompt at its last registered draw: the same prompt as its draw-0 sample row, a separate call with its own
        # record_id), the first call at each other setting, one recognition probe (attraction), and the first two
        # decisions of the first sequential session
        for spec in iter_specs(stimuli, cats, [m], arm="primary", draws="first"):
            key = (spec["stim"]["structure"], spec["fmt"])
            if key not in seen:
                seen.add(key)
                yield spec
        last = draws_for("primary", "pictures", m) - 1
        yield next(s for s in iter_specs(stimuli, cats, [m], arm="primary")
                   if s["fmt"] == "pictures" and s["draw_index"] == last)
        for arm in SETTING_ARMS:
            for st in arm_settings(m, arm):
                yield next(iter_specs(stimuli, cats, [m], arm=arm, setting=st))
        yield next(s for s in iter_specs(stimuli, cats, [m], arm="recognition")
                   if s["stim"]["structure"] == "FRQ")
        seq = iter_specs(stimuli, cats, [m], arm="sequential")
        yield next(seq)
        yield next(seq)
    for spec in picked():
        arm = spec["arm"]
        req = build_request(spec["model_key"], arm, setting=spec["setting"])
        row = contract_b_row(
            "DRYRUN", spec["model_key"], spec["stim"], spec["cat"], spec["fmt"], spec["order"], spec["codes"],
            spec["pid"], spec["mode"], spec["persona"], logged_prompt(spec), spec["image"],
            provider=req["route"], api_flavor=req["api_flavor"], model_id_requested=req["model_id"],
            temperature_requested=req["temperature_requested"], sampling_params_effective=req["sampling_requested"],
            parse_method="dry_run", timestamp=DRY_RUN_TIMESTAMP, reasoning_requested=req["reasoning_requested"],
            arm=arm, session=spec.get("session"), draw_index=spec["draw_index"], setting=spec["setting"])
        samples.append(row)
        if printed < 6:
            print(f"\n--- {spec['stim']['id']} [{spec['fmt']}] order={spec['order']} P{spec['pid']} ---\n{spec['prompt']}")
            printed += 1
    with open(sample_path, "w", encoding="utf-8", newline="\n") as f:
        for r in samples:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[run] {len(samples)} sample calls (one per structure x format, one repeated draw, the first call at each "
          f"other setting, one probe, two sequential decisions) -> {os.path.basename(sample_path)}")

def count_against_manifest(models=None):
    """Walk every arm's call generator for every model at every setting it runs, count the calls, and compare with
    the plan build_manifest.py computes. The runner and the manifest are two independent computations of the same
    plan (one enumerates the calls, the other multiplies counts), so agreement is a real check. models limits the
    walk (the full walk enumerates every one of the plan's calls and takes several minutes)."""
    import build_manifest
    d = json.load(open(STIM, encoding="utf-8"))
    stimuli, cats = d["stimuli"], d["categories"]
    plan = build_manifest.compute_plan()
    keys = models or PRIMARY_LINEUP
    ok, total = True, 0
    by_cond = {}
    for k in keys:
        for arm, s in arm_calls(k):
            n = sum(1 for _ in iter_specs(stimuli, cats, [k], arm=arm, setting=s))
            want = plan["calls"][k].get((arm, s))
            total += n
            cond = build_manifest.ARM_CONDITION[arm]
            by_cond[cond] = by_cond.get(cond, 0) + n
            if n != want:
                ok = False
                print(f"  {k:<22}{arm:<12}{s:<8}{n:>10,}{(want or 0):>12,}   <-- DIFFERS")
        if set(plan["calls"][k]) != set(arm_calls(k)):
            ok = False
            print(f"  {k}: the runner's arms {sorted(arm_calls(k))} differ from the manifest's {sorted(plan['calls'][k])}")
    want_total = sum(plan["model_total"][k] for k in keys)
    print(f"{'condition':<14}{'runner':>12}")
    for c, n in by_cond.items():
        print(f"{c:<14}{n:>12,}" + (f"{plan['by_condition'][c]:>12,}" if not models else ""))
    ok &= total == want_total
    print(("COUNT OK: the runner enumerates exactly the manifest's " if ok else "COUNT MISMATCH against the manifest's ")
          + f"{want_total:,} calls" + (f" for {len(keys)} of {len(PRIMARY_LINEUP)} models" if models else ""))
    return 0 if ok else 1

def main():
    ap = argparse.ArgumentParser(description="Model engine runner: full manifest collection loop (dry-run default).")
    ap.add_argument("--live", action="store_true", help="REAL calls (incurs cost, logged); default is dry-run")
    ap.add_argument("--max-calls", type=int, default=0, help="cap the number of NEW calls (0 = no cap; live smoke should set this)")
    ap.add_argument("--cost-cap", type=float, default=5.0, help="hard per-session USD cap ; the loop stops before exceeding it")
    ap.add_argument("--fresh", action="store_true", help="dry-run only: delete model_log.jsonl first so the dry run starts clean")
    ap.add_argument("--models", default="", help="comma-separated registry keys to run (default: every model the arm runs on)")
    ap.add_argument("--arm", default="primary", choices=ARMS,
                    help="primary (the confirmatory neutral grid, every model) | crossed | ladder (the other settings; "
                         "name one with --setting) | temp_0 / temp_1 | persona | sequential | recognition")
    ap.add_argument("--setting", default=None, choices=SETTINGS,
                    help="the setting a crossed or ladder arm runs (OFF, LOW, DEFAULT, HIGH, MAX)")
    ap.add_argument("--selftest", action="store_true", help="registry + request-payload selftest; no network, no cost")
    ap.add_argument("--out-dir", default="", help="write the logs here instead of this folder (dry run: also "
                    "SAMPLE_CALLS.jsonl). A pre-acceptance smoke should always use its own folder.")
    ap.add_argument("--run-id", default="", help="LIVE runs: required. One log holds one run; e.g. SMOKE-2026-10-01 "
                    "for a capped smoke, STAGE2 for the registered collection. Dry runs always use DRYRUN.")
    ap.add_argument("--write-materials", action="store_true",
                    help="write prompt_materials.json from the registered constant in this file, then stop")
    ap.add_argument("--count", action="store_true",
                    help="count every arm's calls from the runner's own call generator and compare them with "
                         "build_manifest.py's plan (no network); exit 1 on any difference. With --models, those only")
    ap.add_argument("--draws", choices=("first", "all"), default=None,
                    help="dry runs: 'first' (default) writes draw_index 0 only, which keeps the tracked "
                         "model_log.jsonl small; 'all' writes every registered draw. Live runs always run every "
                         "draw and refuse 'first'.")
    a = ap.parse_args()

    if a.write_materials:
        write_prompt_materials()
        print(f"[run] wrote {os.path.basename(MATERIALS_PATH)} from REGISTERED_PROMPT_MATERIALS")
        return
    load_prompt_materials()                         # refuses if the published copy drifted from run.py
    if a.selftest:
        sys.exit(selftest())
    if a.count:
        sys.exit(count_against_manifest([m.strip() for m in a.models.split(",") if m.strip()] or None))
    probs = validate_registry(MODEL_REGISTRY)      # refuse to run at all on a registry that breaks a rule
    if probs:
        sys.exit("[run] MODEL_REGISTRY breaks registered rules; refusing to run:\n  " + "\n  ".join(probs))
    if a.arm in SETTING_ARMS and not a.setting:
        sys.exit(f"[run] the {a.arm} arm runs one setting at a time: pass --setting (one of {', '.join(SETTINGS)})")
    if a.arm not in SETTING_ARMS and a.setting:
        sys.exit(f"[run] the {a.arm} arm runs at each model's lowest setting; --setting is for crossed and ladder")

    eligible = models_for_arm(a.arm, a.setting)
    models = [m.strip() for m in a.models.split(",") if m.strip()] or eligible
    bad = [m for m in models if m not in MODEL_REGISTRY]
    if bad:
        sys.exit(f"unknown model key(s): {bad}. valid: {PRIMARY_LINEUP}")
    wrong_arm = [m for m in models if m not in eligible]
    if wrong_arm:
        sys.exit(f"model(s) {wrong_arm} are not registered for arm {a.arm!r}"
                 f"{' at ' + a.setting if a.setting else ''}; it runs on {eligible}")

    if not a.live:
        # DRY-RUN: exercise the WHOLE loop on synthetic responses, no network, no cost.
        out_dir = os.path.abspath(a.out_dir) if a.out_dir else HERE
        os.makedirs(out_dir, exist_ok=True)
        log_path = log_path_for(a.arm, out_dir, a.setting)
        if a.fresh and os.path.exists(log_path):
            os.remove(log_path)
        write_sample_prompts(os.path.join(out_dir, "SAMPLE_CALLS.jsonl"))
        # default dry-run: one model so the sample log stays small but the full per-cell logic runs.
        dry_models = models if a.models else [SAMPLE_MODEL if SAMPLE_MODEL in eligible else eligible[0]]
        draws = a.draws or "first"
        stats = run_collection(live=False, max_calls=a.max_calls, cost_cap=a.cost_cap,
                               models=dry_models, run_id="DRYRUN", arm=a.arm, log_path=log_path, draws=draws,
                               setting=a.setting)
        print(f"\nDRY-RUN OK: full loop ran on synthetic data (models={dry_models}, arm={a.arm}, draws={draws}"
              f"{'; draw_index 0 only, --draws all writes every registered draw' if draws == 'first' else ''}). "
              f"{stats['written']} contract-B rows -> {os.path.basename(log_path)}; refusals/unparseable/id_drift "
              f"exercised; NO API calls, NO cost. Run analyze.py --model model_log.jsonl to validate downstream.")
        return
    if a.draws == "first":
        sys.exit("[run] --draws first is for dry runs only: a live run collects every registered draw.")

    # LIVE: real capped smoke (the Stage 2 run is the full collection). Keys from env; cost_so_far logged.
    load_env_file_if_present()
    if not a.max_calls:
        print("[run] LIVE without --max-calls would attempt the full grid. Refusing: set --max-calls N "
              "for a capped smoke (the full collection is the Stage 2 run). No cost_so_far incurred.")
        sys.exit(2)
    if not a.run_id or a.run_id == "DRYRUN":
        sys.exit("[run] LIVE needs --run-id (for example SMOKE-2026-10-01 for a capped smoke, STAGE2 for the "
                 "registered collection). One log holds one run, so smoke rows can never count as Stage 2 data.")
    probs = preflight(models)
    if probs:
        sys.exit("[run] LIVE preflight failed; nothing was called:\n  " + "\n  ".join(probs))
    out_dir = os.path.abspath(a.out_dir) if a.out_dir else HERE
    os.makedirs(out_dir, exist_ok=True)
    log_path = log_path_for(a.arm, out_dir, a.setting)
    print(f"[run] LIVE: run_id={a.run_id}, arm={a.arm}, setting={a.setting or 'primary'}, max_calls={a.max_calls}, "
          f"cost_cap=${a.cost_cap:.2f}, log={log_path}. The cost of every call is logged.")
    clients = Clients()
    stats = run_collection(live=True, max_calls=a.max_calls, cost_cap=a.cost_cap,
                           models=models, run_id=a.run_id, clients=clients, arm=a.arm, log_path=log_path,
                           setting=a.setting)
    print(f"\nLIVE RUN DONE: {stats['written']} calls logged, {stats['errors']} API errors left for retry, "
          f"${stats['cost_so_far']:.4f} cost (cap ${a.cost_cap:.2f}).")

if __name__ == "__main__":
    main()
