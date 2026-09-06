// ISS Partner Application — Vercel serverless function.
// Receives the application form POST (JSON), creates/updates a GHL contact,
// maps every enablement answer to a dedicated custom field, tags it, attaches
// a human-readable note, and drops an opportunity into the ISS pipeline.
// Mirrors the REST calls in projects/ghl-cli/ghl.py.
//
// GHL API: base https://services.leadconnectorhq.com, Bearer auth,
//          Version: 2021-07-28 header.
//
// Required env vars (set in Vercel project settings — NEVER commit):
//   GHL_API_KEY      location API key  (Breathe Easy)
//   GHL_LOCATION_ID  matching location id (g5Y1tSfwVfelJu6fbSF9)
//   GHL_PIPELINE_ID  ISS pipeline id (6syqBAylxnFNuqcnYwqx)
//   GHL_STAGE_ID     New Application stage (47047cee-f52e-431b-afc6-1d3e06ade258)
//
// NOTE on the form↔webhook contract: the browser POSTs the payload built by
// buildPayload() in apply.html (generated from build_apply.py). That payload
// uses these keys — which is what we read below:
//   name, company, email, phone, area, volume, website,
//   services (array), leak (number), emailsAgents ("yes"/"no"/null),
//   agentsExample, emailsClients, clientsExample, promoToday,
//   wantsPromoBuild ("yes"/"no"/null)
// The raw form input name="" attributes (agentsExample, clientsExample,
// promoToday, etc.) are a SUBSET; the JS state machine adds services/leak/
// the yes-no toggles. The keys below match buildPayload(), end to end.

const GHL_BASE = "https://services.leadconnectorhq.com";
const GHL_VERSION = "2021-07-28";

// ---------------------------------------------------------------------------
// GHL custom field IDs (Breathe Easy location g5Y1tSfwVfelJu6fbSF9).
// Field IDs are NOT secrets — safe to hardcode. Created/verified 2026-06-21.
//   - SERVICE_AREA / INSPECTIONS_PER_MONTH reuse pre-existing fields.
//   - The ISS_* fields were created specifically for this application.
// To re-list:  python3 projects/ghl-cli/ghl.py custom-fields list -l breatheeasy --json
// ---------------------------------------------------------------------------
const CF = {
  // "As-submitted" application fields. These ALWAYS capture exactly what the
  // applicant typed, even when GHL's no-duplicate rule merges the submission
  // into a pre-existing contact (matched by phone) whose primary email/company
  // are different/stale. This is the source of truth for the application.
  APPLIED_EMAIL: "rSPCMofynR8Mj9XzXda5",         // "ISS Applied Email" (TEXT)
  APPLIED_BUSINESS_NAME: "PTCckIPhit8lwTatWK7w", // "ISS Applied Business Name" (TEXT)
  APPLIED_PHONE: "BBVmEBzA220mb3y029OX",         // "ISS Applied Phone" (TEXT)
  SERVICE_AREA: "uXqDkKSJDSWny9z2HYDm",          // "Primary Service Area" (LARGE_TEXT, existing)
  INSPECTIONS_PER_MONTH: "9vHzd7RT7v0QwIzQHD99",  // "Average Inspections Per Month" (NUMERICAL, existing)
  SERVICES_REFERRED_OUT: "SsMJ8xipBBan1sHHVFa7",  // "ISS Services Referred Out" (TEXT)
  EST_MONTHLY_REVENUE_LEAK: "uRZPmhu8egnilDKlN3BN", // "ISS Est Monthly Revenue Leak" (NUMERICAL)
  EMAILS_AGENTS: "OibMeaVLj7JikoOdg9f2",          // "ISS Emails Agents" (TEXT, Yes/No)
  EMAILS_CLIENTS: "Mlc2EU4usK2pBI7hSD57",         // "ISS Emails Clients" (TEXT, Yes/No)
  PROMOTES_ADDONS_TODAY: "N35NwDRkUjVB01n8fEX4",  // "ISS Promotes Add-ons Today" (LARGE_TEXT)
  WANTS_ISS_BUILD_PROMO: "N7XOHA77lYCH9sFNC4vT",  // "ISS Wants ISS To Build Promo" (TEXT, Yes/No)
  AGENTS_EXAMPLE: "cPBlRwiaX9DQhITIGyga",         // "ISS Agents Example" (LARGE_TEXT)
  CLIENTS_EXAMPLE: "Kx7c9N5OoSpSCmjvUmy1",        // "ISS Clients Example" (LARGE_TEXT)
};

const JUNK_TAG = "couldn't find caller name";

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

// Normalize a yes/no answer ("yes"/"no"/true/false/null) to "Yes"/"No"/"".
function yesno(v) {
  if (v === true || v === "yes" || v === "Yes") return "Yes";
  if (v === false || v === "no" || v === "No") return "No";
  return "";
}

function money(n) {
  const num = Number(n);
  if (!isFinite(num)) return "";
  return "$" + Math.round(num).toLocaleString("en-US");
}

function servicesList(p) {
  return Array.isArray(p.services) ? p.services.join(", ") : "";
}

// Build a human-readable notes block (belt-and-suspenders alongside the
// structured custom fields).
function buildNotes(p) {
  const services = servicesList(p);
  const lines = [
    "ISS Partner Application",
    "------------------------",
    `Business (as submitted): ${p.company || "—"}`,
    `Applicant email (as submitted): ${p.email || "—"}`,
    `Applicant phone (as submitted): ${p.phone || "—"}`,
    `Service area: ${p.area || "—"}`,
    `Inspections per month: ${p.volume || "—"}`,
    `Services referred out today: ${services || "—"}`,
    `Est. monthly revenue walking away: ${money(p.leak) || "—"}  (~${money(Number(p.leak) * 12) || "—"}/yr)`,
    `Website: ${p.website || "—"}`,
    `Emails agents: ${yesno(p.emailsAgents) || "—"}${p.agentsExample ? ` (example: ${p.agentsExample})` : ""}`,
    `Emails clients: ${yesno(p.emailsClients) || "—"}${p.clientsExample ? ` (example: ${p.clientsExample})` : ""}`,
    `Promotes add-ons today: ${p.promoToday || "—"}`,
    `Wants ISS to build promo: ${yesno(p.wantsPromoBuild) || "—"}`,
  ];
  return lines.join("\n");
}

// Map the enablement answers to GHL custom fields. Only include fields that
// actually have a value, so we never blank out existing data on a dup update.
function buildCustomFields(p) {
  const out = [];
  const push = (id, value) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      out.push({ id, field_value: value });
    }
  };
  // As-submitted truth — captured no matter which contact GHL merges into.
  push(CF.APPLIED_EMAIL, p.email);
  push(CF.APPLIED_BUSINESS_NAME, p.company);
  push(CF.APPLIED_PHONE, p.phone);
  push(CF.SERVICE_AREA, p.area);
  push(CF.INSPECTIONS_PER_MONTH, p.volume);
  push(CF.SERVICES_REFERRED_OUT, servicesList(p));
  // leak: always a number from the slider; record it explicitly (even default).
  if (p.leak !== undefined && p.leak !== null && String(p.leak).trim() !== "") {
    out.push({ id: CF.EST_MONTHLY_REVENUE_LEAK, field_value: Number(p.leak) || 0 });
  }
  push(CF.EMAILS_AGENTS, yesno(p.emailsAgents));
  push(CF.EMAILS_CLIENTS, yesno(p.emailsClients));
  push(CF.PROMOTES_ADDONS_TODAY, p.promoToday);
  push(CF.WANTS_ISS_BUILD_PROMO, yesno(p.wantsPromoBuild));
  push(CF.AGENTS_EXAMPLE, p.agentsExample);
  push(CF.CLIENTS_EXAMPLE, p.clientsExample);
  return out;
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
  const customFields = buildCustomFields(p);

  // IMPORTANT — contact-match / no-duplicate behavior:
  // This Breathe Easy location is configured to NOT allow duplicate contacts.
  // GHL dedupes by phone (and/or email). So a returning/known person (e.g. an
  // owner already in the CRM under a different identity/email) who applies will
  // be MATCHED to their existing contact, and POST /contacts/ returns 400 with
  // that contact's id. The applicant's submitted email/company would then be
  // masked by the stale record.
  //
  // Strategy:
  //   - IDENTITY fields (email, firstName, lastName, name): only set when we
  //     CREATE a brand-new contact. On a match we do NOT overwrite them, so we
  //     never corrupt a real person's canonical record with the application's
  //     contact email. The application's true email/phone/company are instead
  //     preserved in the ISS_APPLIED_* custom fields (always written, both
  //     paths) — so the submitted data ALWAYS wins where it matters.
  //   - BUSINESS fields (companyName, website, address1/service area, all
  //     enablement custom fields, source): safe to update on a match too.
  const identityFields = {
    firstName,
    lastName,
    name: p.name,
    email: p.email || undefined,
    phone: p.phone || undefined,
  };
  const businessFields = {
    companyName: p.company || undefined,
    website: p.website || undefined,
    // NOTE: service area is NOT written to address1 — on a duplicate match the PUT
    // would overwrite the contact's real mailing address. It lives in CF.SERVICE_AREA.
    source: "ISS Partner Landing Page",
  };
  if (customFields.length) businessFields.customFields = customFields;

  // ---- 1) Create contact (POST /contacts/) ----
  const contactPayload = Object.assign(
    { locationId, tags: ["iss-partner-application"] },
    identityFields,
    businessFields
  );
  Object.keys(contactPayload).forEach((k) => contactPayload[k] === undefined && delete contactPayload[k]);

  let contactId;
  let wasDuplicate = false;
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
        wasDuplicate = true;
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

  // Partial-integration failures. The application is already captured on the contact
  // by this point, so none of these block the applicant — but they MUST be visible
  // and retryable instead of silently swallowed.
  const warnings = [];
  const warn = (step, detail) => {
    warnings.push({ step, detail: String(detail).slice(0, 300) });
    console.error(`[iss/submit] RETRY-NEEDED step=${step} contact=${contactId}:`, detail);
  };
  // Check a GHL response and record a warning when it failed.
  const checked = async (step, promise) => {
    try {
      const r = await promise;
      if (!r.ok) warn(step, `HTTP ${r.status} ${JSON.stringify(await r.json().catch(() => ({})))}`);
      return r;
    } catch (e) {
      warn(step, (e && e.message) || e);
      return null;
    }
  };

  // ---- 1b) If the contact already existed (matched by phone/email), the POST
  // above does NOT update it. PUT the BUSINESS data + enablement custom fields
  // onto it (company, website, service area, ISS_* fields). We deliberately do
  // NOT push identity fields here, so the matched contact's canonical email and
  // name are left intact — the application's true email/company/phone live in
  // the ISS_APPLIED_* custom fields (included in businessFields.customFields).
  if (wasDuplicate) {
    const updatePayload = Object.assign({}, businessFields);
    Object.keys(updatePayload).forEach((k) => updatePayload[k] === undefined && delete updatePayload[k]);
    await checked("dup-contact-update", fetch(`${GHL_BASE}/contacts/${contactId}`, {
      method: "PUT",
      headers: ghlHeaders(apiKey),
      body: JSON.stringify(updatePayload),
    }));
  }

  // ---- 2) Ensure the tag is applied (idempotent; create payload already tags) ----
  await checked("tag-add", fetch(`${GHL_BASE}/contacts/${contactId}/tags`, {
    method: "POST",
    headers: ghlHeaders(apiKey),
    body: JSON.stringify({ tags: ["iss-partner-application"] }),
  }));

  // ---- 2b) Strip the GHL "couldn't find caller name" junk tag if present.
  // (Gets auto-added when a contact is first created by the phone API before
  // a proper first/last name is on file. We always send a clean name, so this
  // tag is noise — remove it.)
  // Not wrapped in checked(): a failure here means a cosmetic tag stayed put,
  // which is not worth flagging for retry.
  try {
    await fetch(`${GHL_BASE}/contacts/${contactId}/tags`, {
      method: "DELETE",
      headers: ghlHeaders(apiKey),
      body: JSON.stringify({ tags: [JUNK_TAG] }),
    });
  } catch (e) {
    console.warn("[iss/submit] junk tag remove non-fatal error:", e && e.message);
  }

  // ---- 3) Attach the enablement answers as a contact note (belt + suspenders) ----
  await checked("note-add", fetch(`${GHL_BASE}/contacts/${contactId}/notes`, {
    method: "POST",
    headers: ghlHeaders(apiKey),
    body: JSON.stringify({ body: buildNotes(p) }),
  }));

  // ---- 4) Create opportunity in the ISS pipeline ----
  // Endpoint + payload mirror ghl.py cmd_opportunities_create():
  //   POST /opportunities/  { locationId, contactId, pipelineId,
  //                           pipelineStageId, name, monetaryValue, status }
  const pipelineId = process.env.GHL_PIPELINE_ID;
  const stageId = process.env.GHL_STAGE_ID;
  let opportunityId = null;
  let opportunityOutcome = "skipped"; // created | existing-reused | failed | skipped
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
      if (r.ok) {
        opportunityId = (body.opportunity && body.opportunity.id) || body.id || null;
        opportunityOutcome = "created";
      } else if (body && body.code === "OPPORTUNITY_NO_DUPLICATE") {
        // Repeat applicant: this contact already has an opportunity in this
        // pipeline. GHL hands back its id. Reconcile to it and REPORT it —
        // deliberately WITHOUT touching its stage. An already-active partner
        // must never be dragged back to "New Application" by re-applying.
        opportunityId = (body.meta && body.meta.existingId) || null;
        opportunityOutcome = "existing-reused";
        console.warn(`[iss/submit] Existing opportunity ${opportunityId} reused for contact ${contactId}; stage left unchanged.`);
        if (!opportunityId) warn("opportunity-duplicate-no-id", JSON.stringify(body));
      } else {
        opportunityOutcome = "failed";
        warn("opportunity-create", `HTTP ${r.status} ${JSON.stringify(body)}`);
      }
    } catch (e) {
      opportunityOutcome = "failed";
      warn("opportunity-create", (e && e.message) || e);
    }
  } else {
    console.warn("[iss/submit] GHL_PIPELINE_ID/GHL_STAGE_ID not set — skipping opportunity create.");
  }

  // ok:true means the APPLICATION IS CAPTURED on the contact. opportunityOutcome and
  // warnings say whether the pipeline side fully succeeded, so a partial failure is
  // recorded rather than reported as a clean success.
  res.status(200).json({
    ok: true,
    contactId,
    opportunityId,
    opportunityOutcome,
    warnings: warnings.length ? warnings : undefined,
  });
};
