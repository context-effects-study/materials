// worker.js: the survey-assignment service (a Cloudflare Worker) for the words, pictures and price-free
// surveys.
//
// At the start of a response the survey calls GET /assign?arm=<price-free|words|pictures>; the service
// returns one pre-built script (script_id and the embedded-data fields the choice pages render) and the
// survey stores it in embedded data. Per survey the service keeps a count per script and hands out the
// least-used script, breaking ties at random, which balances presentations the way Qualtrics' even
// presentation does. Two calls at the same instant can occasionally receive the same script, a small
// imbalance the design tolerates. The service stores only these counts: it reads no personal data and never
// receives responses.
//
// Endpoints: GET /assign?arm=<arm>, GET /health, GET /stats[?arm=<arm>].
// The script tables are built by build_worker_data.py.

import { MANIFEST, ARMS_GZ_B64 } from "./scripts_data.js";

const VERSION = "survey-assign-worker-1.2 (2026-07-02, locked bundle: calibrated values + enrichment; pictures arm 2,100 scripts after the hard-drives pictures exit)";
const ARMS = Object.keys(MANIFEST);

// ---- one-time, cached decompression of the bundled script tables (module scope persists across reqs) ---
let _arms = null;
async function loadArms() {
  if (_arms) return _arms;
  _arms = {};
  for (const arm of ARMS) {
    const gz = Uint8Array.from(atob(ARMS_GZ_B64[arm]), (c) => c.charCodeAt(0));
    const ds = new DecompressionStream("gzip");
    const stream = new Response(new Blob([gz]).stream().pipeThrough(ds));
    const text = await stream.text();
    _arms[arm] = JSON.parse(text); // array of flat field-dicts, one per script
  }
  return _arms;
}

function json(obj, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "access-control-allow-origin": "*", // Qualtrics Web Service calls server-side; CORS harmless
      ...extraHeaders,
    },
  });
}

const COUNTS_KEY = (arm) => `counts:${arm}`;

async function readCounts(env, arm, n) {
  const raw = await env.CFX_ASSIGN.get(COUNTS_KEY(arm));
  if (!raw) return new Array(n).fill(0);
  let arr;
  try {
    arr = JSON.parse(raw);
  } catch {
    arr = [];
  }
  if (!Array.isArray(arr) || arr.length !== n) {
    // length drift (e.g. a data rebuild changed n) -> reset to a clean zero vector for this arm
    arr = new Array(n).fill(0);
  }
  return arr;
}

// Pick the least-used script index; random tie-break among the current minima to spread concurrent calls.
function pickLeastUsed(counts) {
  let min = Infinity;
  for (const c of counts) if (c < min) min = c;
  const minima = [];
  for (let i = 0; i < counts.length; i++) if (counts[i] === min) minima.push(i);
  return minima[Math.floor(Math.random() * minima.length)];
}

async function handleAssign(env, url) {
  const arm = url.searchParams.get("arm");
  if (!arm || !ARMS.includes(arm)) {
    return json({ ok: false, error: `unknown or missing arm; expected one of ${ARMS.join(", ")}` }, 400);
  }
  const arms = await loadArms();
  const table = arms[arm];
  const n = table.length;

  const counts = await readCounts(env, arm, n);
  const idx = pickLeastUsed(counts);
  counts[idx] += 1;
  // best-effort write-back (read-modify-write; see the guarantee/caveat in the file header)
  await env.CFX_ASSIGN.put(COUNTS_KEY(arm), JSON.stringify(counts));

  const fields = table[idx]; // the flat embedded-data payload (already includes script_id)
  return json({
    ok: true,
    arm,
    assignment_version: MANIFEST[arm].deal_sha256_12,
    assigned_index: idx,
    assigned_count: counts[idx],
    ...fields,
  });
}

async function handleStats(env, url) {
  const arms = await loadArms();
  const want = url.searchParams.get("arm");
  const out = {};
  for (const arm of ARMS) {
    if (want && want !== arm) continue;
    const n = arms[arm].length;
    const counts = await readCounts(env, arm, n);
    let total = 0,
      min = Infinity,
      max = -Infinity,
      used = 0;
    for (const c of counts) {
      total += c;
      if (c < min) min = c;
      if (c > max) max = c;
      if (c > 0) used += 1;
    }
    out[arm] = {
      n_scripts: n,
      total_assigned: total,
      distinct_scripts_used: used,
      min_count: min === Infinity ? 0 : min,
      max_count: max === -Infinity ? 0 : max,
      spread: (max === -Infinity ? 0 : max) - (min === Infinity ? 0 : min),
      deal_sha256_12: MANIFEST[arm].deal_sha256_12,
    };
  }
  return json({ ok: true, version: VERSION, stats: out });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";
    try {
      if (path === "/health" || path === "/") {
        const m = {};
        for (const arm of ARMS) m[arm] = { n_scripts: MANIFEST[arm].n_scripts, k_trials: MANIFEST[arm].k_trials };
        return json({ ok: true, version: VERSION, arms: m });
      }
      if (path === "/assign") return await handleAssign(env, url);
      if (path === "/stats") return await handleStats(env, url);
      return json({ ok: false, error: "not found", paths: ["/assign?arm=", "/health", "/stats"] }, 404);
    } catch (e) {
      return json({ ok: false, error: String(e && e.message ? e.message : e) }, 500);
    }
  },
};
