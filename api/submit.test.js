// Self-check for the ISS application handler. No framework: `node api/submit.test.js`.
// Stubs GHL entirely — never touches the live location.
const assert = require("assert");

process.env.GHL_API_KEY = "test-key";
process.env.GHL_LOCATION_ID = "loc_test";
process.env.GHL_PIPELINE_ID = "pipe_test";
process.env.GHL_STAGE_ID = "stage_new_application";

const handler = require("./submit.js");

const APPLICATION = {
  name: "Dana Reyes",
  company: "Reyes Home Inspections",
  email: "dana@reyesinspect.com",
  phone: "+16025550143",
  area: "Chandler / Gilbert",
  volume: 22,
  website: "reyesinspect.com",
  services: ["Sewer scope", "Radon"],
  leak: 1800,
  emailsAgents: "yes",
  agentsExample: "Monthly market note",
  emailsClients: "no",
  promoToday: "Nothing formal",
  wantsPromoBuild: "yes",
};

function res() {
  return {
    code: null,
    body: null,
    status(c) { this.code = c; return this; },
    json(o) { this.body = o; return this; },
  };
}

const ok = (body) => ({ ok: true, status: 200, json: async () => body });
const err = (status, body) => ({ ok: false, status, json: async () => body });

// Route stubbed GHL calls; record every request for assertions.
function stubFetch(routes) {
  const calls = [];
  global.fetch = async (url, opts = {}) => {
    const method = opts.method || "GET";
    calls.push({ url, method, body: opts.body ? JSON.parse(opts.body) : null });
    for (const [match, respond] of routes) {
      if (match(url, method)) return respond();
    }
    return ok({});
  };
  return calls;
}

const isContactCreate = (u, m) => u.endsWith("/contacts/") && m === "POST";
const isContactUpdate = (u, m) => /\/contacts\/[^/]+$/.test(u) && m === "PUT";
const isOppCreate = (u, m) => u.endsWith("/opportunities/") && m === "POST";
const isNote = (u) => u.includes("/notes");

async function run(name, fn) {
  await fn();
  console.log("  ok -", name);
}

(async () => {
  console.log("ISS /api/submit self-check");

  await run("new applicant: contact + opportunity both created", async () => {
    stubFetch([
      [isContactCreate, () => ok({ contact: { id: "c_new" } })],
      [isOppCreate, () => ok({ opportunity: { id: "o_new" } })],
    ]);
    const r = res();
    await handler({ method: "POST", body: { ...APPLICATION } }, r);
    assert.strictEqual(r.code, 200);
    assert.strictEqual(r.body.ok, true);
    assert.strictEqual(r.body.contactId, "c_new");
    assert.strictEqual(r.body.opportunityId, "o_new");
    assert.strictEqual(r.body.opportunityOutcome, "created");
    assert.strictEqual(r.body.warnings, undefined, "clean run must report no warnings");
  });

  await run("service area is never written to address1", async () => {
    const calls = stubFetch([
      [isContactCreate, () => ok({ contact: { id: "c_new" } })],
      [isOppCreate, () => ok({ opportunity: { id: "o_new" } })],
    ]);
    await handler({ method: "POST", body: { ...APPLICATION } }, res());
    const create = calls.find((c) => isContactCreate(c.url, c.method));
    assert.ok(!("address1" in create.body), "address1 would overwrite a real mailing address");
    const areaField = create.body.customFields.find((f) => f.id === "uXqDkKSJDSWny9z2HYDm");
    assert.strictEqual(areaField.field_value, "Chandler / Gilbert", "service area belongs in its own field");
  });

  await run("returning applicant: duplicate contact is updated, identity left intact", async () => {
    const calls = stubFetch([
      [isContactCreate, () => err(400, { meta: { contactId: "c_existing" } })],
      [isOppCreate, () => ok({ opportunity: { id: "o_new" } })],
    ]);
    const r = res();
    await handler({ method: "POST", body: { ...APPLICATION } }, r);
    assert.strictEqual(r.body.contactId, "c_existing");
    const put = calls.find((c) => isContactUpdate(c.url, c.method));
    assert.ok(put, "a matched contact must still receive the business fields");
    assert.ok(!("email" in put.body), "must not overwrite the canonical email");
    assert.ok(!("firstName" in put.body), "must not overwrite the canonical name");
    const applied = put.body.customFields.find((f) => f.id === "rSPCMofynR8Mj9XzXda5");
    assert.strictEqual(applied.field_value, "dana@reyesinspect.com", "as-submitted email must survive");
  });

  await run("repeat applicant: existing opportunity reused, stage NOT reset", async () => {
    const calls = stubFetch([
      [isContactCreate, () => err(400, { meta: { contactId: "c_existing" } })],
      [isOppCreate, () => err(400, {
        code: "OPPORTUNITY_NO_DUPLICATE",
        message: "Can not create duplicate opportunity for the contact.",
        meta: { existingId: "enLMF2nITfYYXTQMzKmV" },
      })],
    ]);
    const r = res();
    await handler({ method: "POST", body: { ...APPLICATION } }, r);
    assert.strictEqual(r.body.ok, true, "applicant must not see a failure");
    assert.strictEqual(r.body.opportunityId, "enLMF2nITfYYXTQMzKmV");
    assert.strictEqual(r.body.opportunityOutcome, "existing-reused");
    assert.strictEqual(r.body.warnings, undefined, "a known repeat applicant is not a retry case");
    // The regression that matters: nothing may push the existing opp back to New Application.
    const staged = calls.filter((c) => c.url.includes("/opportunities/") && c.method !== "POST");
    assert.strictEqual(staged.length, 0, "an active partner must never be moved back to New Application");
  });

  await run("opportunity hard failure is recorded for retry", async () => {
    stubFetch([
      [isContactCreate, () => ok({ contact: { id: "c_new" } })],
      [isOppCreate, () => err(500, { message: "boom" })],
    ]);
    const r = res();
    await handler({ method: "POST", body: { ...APPLICATION } }, r);
    assert.strictEqual(r.body.ok, true, "the application is captured, so the applicant is not blocked");
    assert.strictEqual(r.body.opportunityOutcome, "failed");
    assert.ok(r.body.warnings.some((w) => w.step === "opportunity-create"), "failure must be retryable, not silent");
  });

  await run("a dropped note is recorded instead of swallowed", async () => {
    stubFetch([
      [isContactCreate, () => ok({ contact: { id: "c_new" } })],
      [isOppCreate, () => ok({ opportunity: { id: "o_new" } })],
      [(u, m) => isNote(u) && m === "POST", () => err(500, { message: "note down" })],
    ]);
    const r = res();
    await handler({ method: "POST", body: { ...APPLICATION } }, r);
    assert.ok(r.body.warnings.some((w) => w.step === "note-add"));
  });

  await run("incomplete submission is rejected", async () => {
    stubFetch([]);
    const r = res();
    await handler({ method: "POST", body: { name: "No Contact Details" } }, r);
    assert.strictEqual(r.code, 400);
    assert.strictEqual(r.body.ok, false);
  });

  console.log("\nall checks passed");
})().catch((e) => {
  console.error("\nFAILED:", e.message);
  process.exit(1);
});
