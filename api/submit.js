// ISS Partner Application — Vercel serverless function.
// Receives the application form POST (JSON), creates a GHL contact, tags it,
// and (once pipeline IDs are provisioned) drops an opportunity into the ISS
// pipeline. Mirrors the REST calls in projects/ghl-cli/ghl.py.
//
// GHL API: base https://services.leadconnectorhq.com, Bearer auth,
//          Version: 2021-07-28 header.
//
// Required env vars (set in Vercel project settings — NEVER commit):
//   GHL_API_KEY      location API key
//   GHL_LOCATION_ID  matching location id
// Gated (Phase 3b — drop in once Hank provisions the ISS pipeline):
//   GHL_PIPELINE_ID  ISS pipeline id
//   GHL_STAGE_ID     first stage (new application) id

const GHL_BASE = "https://services.leadconnectorhq.com";
const GHL_VERSION = "2021-07-28";

function ghlHeaders(apiKey) {
  return {
    Authorization: `Bearer ${apiKey}`,
    Version: GHL_VERSION,
    "Content-Type": "application/json",
    Accept: "application/json",
  };
}

function splitName(full) {
  const parts = String(full || "").trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { firstName: "", lastName: "" };
  if (parts.length === 1) return { firstName: parts[0], lastName: "" };
  return { firstName: parts[0], lastName: parts.slice(1).join(" ") };
}

function bool(v) {
  if (v === true || v === "yes") return "Yes";
  if (v === false || v === "no") return "No";
  return "";
}

function money(n) {
  const num = Number(n);
  if (!isFinite(num)) return "";
  return "$" + Math.round(num).toLocaleString("en-US");
}

// Build a human-readable notes block from the enablement answers, so the data
// is captured even before custom fields are provisioned in GHL.
function buildNotes(p) {
  const services = Array.isArray(p.services) ? p.services.join(", ") : "";
  const lines = [
    "ISS Partner Application",
    "------------------------",
    `Service area: ${p.area || "—"}`,
    `Inspections per month: ${p.volume || "—"}`,
    `Services referred out today: ${services || "—"}`,
    `Est. monthly revenue walking away: ${money(p.leak) || "—"}  (~${money(Number(p.leak) * 12) || "—"}/yr)`,
    `Website: ${p.website || "—"}`,
    `Emails agents: ${bool(p.emailsAgents) || "—"}${p.agentsExample ? ` (example: ${p.agentsExample})` : ""}`,
    `Emails clients: ${bool(p.emailsClients) || "—"}${p.clientsExample ? ` (example: ${p.clientsExample})` : ""}`,
    `Promotes add-ons today: ${p.promoToday || "—"}`,
    `Wants ISS to build promo: ${bool(p.wantsPromoBuild) || "—"}`,
  ];
  return lines.join("\n");
}

async function readJsonBody(req) {
  // Vercel usually parses JSON into req.body; fall back to manual read.
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string" && req.body.length) {
    try { return JSON.parse(req.body); } catch (e) { /* fall through */ }
  }
  return await new Promise((resolve) => {
    let data = "";
    req.on("data", (c) => (data += c));
    req.on("end", () => {
      try { resolve(JSON.parse(data || "{}")); }
      catch (e) { resolve({}); }
    });
    req.on("error", () => resolve({}));
  });
}

module.exports = async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ ok: false, error: "Method not allowed." });
    return;
  }

  const apiKey = process.env.GHL_API_KEY;
  const locationId = process.env.GHL_LOCATION_ID;
  if (!apiKey || !locationId) {
    console.error("[iss/submit] Missing GHL_API_KEY or GHL_LOCATION_ID env vars.");
    res.status(500).json({ ok: false, error: "Server is not configured yet. Please email john@inspectionsupportservices.com." });
    return;
  }

  let p;
  try {
    p = await readJsonBody(req);
  } catch (e) {
    res.status(400).json({ ok: false, error: "Could not read your submission." });
    return;
  }

  // Minimal validation (front-end also enforces this on step 1).
  if (!p || (!p.email && !p.phone) || !p.name) {
    res.status(400).json({ ok: false, error: "Please include your name and either an email or phone." });
    return;
  }

  const { firstName, lastName } = splitName(p.name);

  // ---- 1) Create contact (POST /contacts/) ----
  const contactPayload = {
    locationId,
    firstName,
    lastName,
    name: p.name,
    email: p.email || undefined,
    phone: p.phone || undefined,
    companyName: p.company || undefined,
    website: p.website || undefined,
    address1: p.area || undefined, // service area, best-effort mapping
    tags: ["iss-partner-application"],
    source: "ISS Partner Landing Page",
    // Enablement answers captured as notes (see buildNotes). When ISS custom
    // fields are provisioned, map them here as customFields: [{id, value}].
  };
  Object.keys(contactPayload).forEach((k) => contactPayload[k] === undefined && delete contactPayload[k]);

  let contactId;
  try {
    const r = await fetch(`${GHL_BASE}/contacts/`, {
      method: "POST",
      headers: ghlHeaders(apiKey),
      body: JSON.stringify(contactPayload),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) {
      // Duplicate contact: GHL returns 400 with the existing contact id.
      const dupId =
        (body && body.meta && body.meta.contactId) ||
        (body && body.contact && body.contact.id);
      if (r.status === 400 && dupId) {
        contactId = dupId;
        console.warn(`[iss/submit] Duplicate contact, reusing ${contactId}.`);
      } else {
        console.error(`[iss/submit] contact create failed HTTP ${r.status}:`, JSON.stringify(body));
        res.status(502).json({ ok: false, error: "We couldn't save your application. Please try again, or email john@inspectionsupportservices.com." });
        return;
      }
    } else {
      contactId = (body.contact && body.contact.id) || body.id;
    }
  } catch (e) {
    console.error("[iss/submit] contact create threw:", e && e.message);
    res.status(502).json({ ok: false, error: "We couldn't reach our system. Please try again shortly." });
    return;
  }

  if (!contactId) {
    console.error("[iss/submit] No contactId returned.");
    res.status(502).json({ ok: false, error: "We couldn't save your application. Please try again." });
    return;
  }

  // ---- 2) Ensure the tag is applied (idempotent; create payload already tags) ----
  try {
    await fetch(`${GHL_BASE}/contacts/${contactId}/tags`, {
      method: "POST",
      headers: ghlHeaders(apiKey),
      body: JSON.stringify({ tags: ["iss-partner-application"] }),
    });
  } catch (e) {
    console.warn("[iss/submit] tag add non-fatal error:", e && e.message);
  }

  // ---- 3) Attach the enablement answers as a contact note ----
  try {
    await fetch(`${GHL_BASE}/contacts/${contactId}/notes`, {
      method: "POST",
      headers: ghlHeaders(apiKey),
      body: JSON.stringify({ body: buildNotes(p) }),
    });
  } catch (e) {
    console.warn("[iss/submit] note add non-fatal error:", e && e.message);
  }

  // ---- 4) Create opportunity in the ISS pipeline ----
  // =====================================================================
  // TODO (Phase 3b — GATED): pipeline drop. Hank is provisioning the ISS
  // pipeline + first stage in parallel. Once GHL_PIPELINE_ID and
  // GHL_STAGE_ID are set in Vercel env, this block activates automatically.
  // Endpoint + payload mirror ghl.py cmd_opportunities_create():
  //   POST /opportunities/  { locationId, contactId, pipelineId,
  //                           pipelineStageId, name, monetaryValue, status }
  // DO NOT invent pipeline/stage IDs — leave gated on the env vars.
  // =====================================================================
  const pipelineId = process.env.GHL_PIPELINE_ID;
  const stageId = process.env.GHL_STAGE_ID;
  let opportunityId = null;
  if (pipelineId && stageId) {
    try {
      const oppPayload = {
        locationId,
        contactId,
        pipelineId,
        pipelineStageId: stageId,
        name: `ISS Partner — ${p.company || p.name}`,
        status: "open",
        monetaryValue: Number(p.leak) || 0,
      };
      const r = await fetch(`${GHL_BASE}/opportunities/`, {
        method: "POST",
        headers: ghlHeaders(apiKey),
        body: JSON.stringify(oppPayload),
      });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) {
        console.error(`[iss/submit] opportunity create failed HTTP ${r.status}:`, JSON.stringify(body));
        // Non-fatal: the contact is already saved. Still report ok so the
        // applicant isn't blocked; the lead is captured + tagged.
      } else {
        opportunityId = (body.opportunity && body.opportunity.id) || body.id || null;
      }
    } catch (e) {
      console.warn("[iss/submit] opportunity create non-fatal error:", e && e.message);
    }
  } else {
    console.warn("[iss/submit] GHL_PIPELINE_ID/GHL_STAGE_ID not set — skipping opportunity create (Phase 3b gated).");
  }

  res.status(200).json({ ok: true, contactId, opportunityId });
};
