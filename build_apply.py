#!/usr/bin/env python3
"""
Resolve ISS-Partner-Application-CLEAN.html (Claude Design DCLogic export) into a
static, deployable apply.html with a vanilla-JS state machine that mirrors the
export's Component (3-step form, services toggle, leak slider, yes/no toggles,
conditional reveals) and POSTs to /api/submit, rendering the confirmation on
ok:true. Preserves all inlined data-URI lines untouched.
"""
import re, sys

SRC = "ISS-Partner-Application-CLEAN.html"
OUT = "apply.html"

with open(SRC, "r", encoding="utf-8") as f:
    src = f.read()

# ---------------------------------------------------------------------------
# 1) Resolve all sc-if blocks: UNWRAP (keep inner content) and give the inner
#    wrapper an id/class so vanilla JS can show/hide. We tag each by its token.
#    Strategy: replace <sc-if value="{{ TOKEN }}" ...> ... </sc-if> with a
#    <div data-scif="TOKEN"> ... </div> wrapper, so JS controls visibility.
#    EXCEPT showForm/submitted top-level which we map to #iss-form / #iss-confirm.
# ---------------------------------------------------------------------------
def scif_repl(m):
    token = m.group(1).strip()
    inner = m.group(2)
    return '<div data-scif="%s">%s</div>' % (token, inner)

# Non-greedy, innermost-first is tricky with nested sc-if. The app has nesting:
# showForm > (isStep0|isStep1|isStep2 > showAgents|showClients), plus submitted.
# Resolve repeatedly until no sc-if remain (handles nesting inside-out).
scif_pat = re.compile(r"<sc-if value=\"\{\{ ([^}]*) \}\}\"[^>]*>(.*?)</sc-if>", re.DOTALL)
prev = None
while prev != src:
    prev = src
    src = scif_pat.sub(scif_repl, src)

# ---------------------------------------------------------------------------
# 2) Resolve the services sc-for into 6 static buttons with data-key, default
#    (unchecked) styling. JS toggles active styling + check glyph.
# ---------------------------------------------------------------------------
SERVICES = [
    {"key": "radon", "label": "Radon"},
    {"key": "air",   "label": "Air quality"},
    {"key": "sewer", "label": "Sewer line"},
    {"key": "solar", "label": "Solar + energy"},
    {"key": "mold",  "label": "Mold"},
    {"key": "other", "label": "Other"},
]
inactive_btn = ("display:flex;align-items:center;gap:11px;cursor:pointer;"
                "background:#16243a;border:1px solid rgba(255,255,255,.1);"
                "border-radius:10px;padding:14px 15px;color:#F5F5F7;"
                "font-family:Montserrat;text-align:left;")
inactive_box = ("flex:none;width:22px;height:22px;border-radius:6px;"
                "border:2px solid rgba(255,255,255,.28);background:transparent;"
                "color:#06241a;display:flex;align-items:center;justify-content:center;"
                "font-size:13px;font-weight:800;")
svc_tpl = (
    '              <button type="button" class="iss-svc" data-key="{key}" style="{btn}">\n'
    '                <span class="iss-svc-box" style="{box}"></span>\n'
    '                <span style="font-size:15px;font-weight:600;">{label}</span>\n'
    '              </button>'
)
svc_html = "\n".join(
    svc_tpl.format(key=s["key"], label=s["label"], btn=inactive_btn, box=inactive_box)
    for s in SERVICES
)
src = re.sub(
    r"<sc-for list=\"\{\{ services \}\}\"[^>]*>.*?</sc-for>",
    lambda m: svc_html, src, flags=re.DOTALL,
)

# ---------------------------------------------------------------------------
# 3) Resolve inline {{ }} tokens in the static markup to their initial values
#    / wire hooks. We replace token attributes with ids/classes JS controls.
# ---------------------------------------------------------------------------
accent = "#3DB088"
inactive_track = "linear-gradient(to right,#F4C542 0%,#F4C542 25.0%,#0F1E35 25.0%,#0F1E35 100%)"  # leak=1500 -> 25%

# progress bars initial: step 0 -> p1 active, p2/p3 inactive
src = src.replace("background:{{ p1 }};", "background:%s;" % accent, 1)
src = src.replace("background:{{ p2 }};", "background:rgba(255,255,255,.1);", 1)
src = src.replace("background:{{ p3 }};", "background:rgba(255,255,255,.1);", 1)

# onField handlers -> remove (JS reads inputs by name at submit; also live for name)
src = src.replace('onchange="{{ onField }}"', 'data-field')

# leak slider
src = src.replace('value="{{ leak }}"', 'value="1500" id="iss-leak"')
src = src.replace('oninput="{{ onLeak }}"', "")
src = src.replace("background:{{ leakTrack }};", "background:%s;" % inactive_track)
# leak labels (id hooks). leak=1500 -> $1,500 ; year -> $18,000
src = src.replace("{{ leakLabel }}", '<span id="iss-leak-label">$1,500</span>')
src = src.replace("about {{ leakYear }} a year", 'about <span id="iss-leak-year">$18,000</span> a year')

# services buttons already resolved (s.* tokens gone)

# yes/no toggle buttons: agents
toggle_inactive = ("flex:1;cursor:pointer;font-family:Montserrat;font-weight:700;font-size:15px;"
                   "padding:14px 16px;border-radius:9px;background:#16243a;color:#A1A5B0;"
                   "border:1px solid rgba(255,255,255,.12);")
src = src.replace('onclick="{{ agentsYes }}" style="{{ agentsYesStyle }}"',
                  'type="button" class="iss-toggle" data-group="agents" data-val="yes" style="%s"' % toggle_inactive)
src = src.replace('onclick="{{ agentsNo }}" style="{{ agentsNoStyle }}"',
                  'type="button" class="iss-toggle" data-group="agents" data-val="no" style="%s"' % toggle_inactive)
src = src.replace('onclick="{{ clientsYes }}" style="{{ clientsYesStyle }}"',
                  'type="button" class="iss-toggle" data-group="clients" data-val="yes" style="%s"' % toggle_inactive)
src = src.replace('onclick="{{ clientsNo }}" style="{{ clientsNoStyle }}"',
                  'type="button" class="iss-toggle" data-group="clients" data-val="no" style="%s"' % toggle_inactive)
src = src.replace('onclick="{{ promoYes }}" style="{{ promoYesStyle }}"',
                  'type="button" class="iss-toggle" data-group="promo" data-val="yes" style="%s"' % toggle_inactive)
src = src.replace('onclick="{{ promoNo }}" style="{{ promoNoStyle }}"',
                  'type="button" class="iss-toggle" data-group="promo" data-val="no" style="%s"' % toggle_inactive)

# nav buttons
src = src.replace('onclick="{{ back }}"', 'type="button" id="iss-back"')
src = src.replace('onclick="{{ submit }}"', 'type="button" id="iss-submit"')
src = src.replace('onclick="{{ next }}"', 'type="button" id="iss-next"')

# err message
src = src.replace("{{ errMsg }}", "")

# confirmation name
src = src.replace("Application received{{ nameComma }}.", 'Application received<span id="iss-name-comma"></span>.')

# Fix the back-link to the landing route
src = src.replace('href="ISS Partner Landing.html"', 'href="/"')

# ---------------------------------------------------------------------------
# 4) Map the data-scif wrappers to controllable ids/classes.
#    showForm -> #iss-form ; submitted -> #iss-confirm (hidden initially)
#    isStep0/1/2 -> .iss-stepwrap data-step ; showAgents/showClients ->
#    .iss-reveal ; canBack/showNext/isStep2(submit)/err -> nav controls.
# ---------------------------------------------------------------------------
src = src.replace('<div data-scif="showForm">', '<div id="iss-form">', 1)
src = src.replace('<div data-scif="submitted">', '<div id="iss-confirm" style="display:none;">', 1)
src = src.replace('<div data-scif="isStep0">', '<div class="iss-stepwrap" data-step="0">', 1)
src = src.replace('<div data-scif="isStep1">', '<div class="iss-stepwrap" data-step="1" style="display:none;">', 1)
# isStep2 appears twice: the step-3 panel AND the submit-button gate. First is panel.
src = src.replace('<div data-scif="isStep2">', '<div class="iss-stepwrap" data-step="2" style="display:none;">', 1)
# remaining isStep2 (submit gate) and others
src = src.replace('<div data-scif="showAgents">', '<div class="iss-reveal" data-reveal="agents" style="display:none;">', 1)
src = src.replace('<div data-scif="showClients">', '<div class="iss-reveal" data-reveal="clients" style="display:none;">', 1)
src = src.replace('<div data-scif="canBack">', '<div id="iss-back-wrap" style="display:none;">', 1)
src = src.replace('<div data-scif="isStep2">', '<div id="iss-submit-wrap" style="display:none;">', 1)  # submit gate
src = src.replace('<div data-scif="showNext">', '<div id="iss-next-wrap">', 1)
src = src.replace('<div data-scif="err">', '<div id="iss-err-wrap" style="display:none;margin-top:14px;font-size:13.5px;color:#E05C5C;font-weight:600;"><span id="iss-err-msg"></span>', 1)

# ---------------------------------------------------------------------------
# 5) Replace DCLogic script with vanilla runtime.
# ---------------------------------------------------------------------------
vanilla = r"""<script>
(function () {
  var accent = '#3DB088';
  var state = { step: 0, services: {}, leak: 1500, agents: null, clients: null, promo: null };
  var data = {};

  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function fmt(n) { return '$' + Math.round(n).toLocaleString('en-US'); }

  // --- text fields ---
  $all('[data-field]').forEach(function (el) {
    el.addEventListener('input', function () { data[el.name] = el.value; });
    el.addEventListener('change', function () { data[el.name] = el.value; });
  });

  // --- progress bars ---
  var bars = $all('#iss-form .iss-step').length ? null : null;
  function syncProgress() {
    var pbars = $all('[id^="iss-progress"]');
  }

  // progress bar elements (first 3 thin divs)
  var progressBars = $all('#iss-form > div > div[style*="height:5px"]');

  function setStepUI() {
    // step panels
    $all('.iss-stepwrap').forEach(function (w) {
      w.style.display = (Number(w.getAttribute('data-step')) === state.step) ? '' : 'none';
    });
    // progress
    if (progressBars.length === 3) {
      progressBars[0].style.background = state.step >= 0 ? accent : 'rgba(255,255,255,.1)';
      progressBars[1].style.background = state.step >= 1 ? accent : 'rgba(255,255,255,.1)';
      progressBars[2].style.background = state.step >= 2 ? accent : 'rgba(255,255,255,.1)';
    }
    // nav buttons
    var backWrap = $('#iss-back-wrap');
    var nextWrap = $('#iss-next-wrap');
    var submitWrap = $('#iss-submit-wrap');
    if (backWrap) backWrap.style.display = state.step > 0 ? '' : 'none';
    if (nextWrap) nextWrap.style.display = state.step < 2 ? '' : 'none';
    if (submitWrap) submitWrap.style.display = state.step === 2 ? '' : 'none';
  }

  function showErr(msg) {
    var w = $('#iss-err-wrap'), m = $('#iss-err-msg');
    if (msg) { if (m) m.textContent = msg; if (w) w.style.display = ''; }
    else { if (w) w.style.display = 'none'; }
  }

  // --- nav ---
  function next() {
    if (state.step === 0) {
      if (!data.name || !data.email || !data.phone) {
        showErr('Please add your name, email, and phone so we can reach you.');
        return;
      }
    }
    state.step = Math.min(state.step + 1, 2);
    showErr('');
    setStepUI();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  function back() {
    state.step = Math.max(state.step - 1, 0);
    showErr('');
    setStepUI();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
  if ($('#iss-next')) $('#iss-next').addEventListener('click', next);
  if ($('#iss-back')) $('#iss-back').addEventListener('click', back);

  // --- services toggle ---
  $all('.iss-svc').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var k = btn.getAttribute('data-key');
      state.services[k] = !state.services[k];
      var active = !!state.services[k];
      var box = btn.querySelector('.iss-svc-box');
      btn.style.background = active ? 'rgba(61,176,136,.12)' : '#16243a';
      btn.style.border = '1px solid ' + (active ? 'rgba(61,176,136,.5)' : 'rgba(255,255,255,.1)');
      if (box) {
        box.style.border = '2px solid ' + (active ? accent : 'rgba(255,255,255,.28)');
        box.style.background = active ? accent : 'transparent';
        box.textContent = active ? '\u2713' : '';
      }
    });
  });

  // --- yes/no toggles (agents/clients/promo) ---
  function styleToggle(btn, active) {
    btn.style.background = active ? accent : '#16243a';
    btn.style.color = active ? '#06241a' : '#A1A5B0';
    btn.style.border = '1px solid ' + (active ? accent : 'rgba(255,255,255,.12)');
  }
  $all('.iss-toggle').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var group = btn.getAttribute('data-group');
      var val = btn.getAttribute('data-val');
      state[group] = val;
      $all('.iss-toggle[data-group="' + group + '"]').forEach(function (b) {
        styleToggle(b, b.getAttribute('data-val') === val);
      });
      // reveal example field when "yes"
      if (group === 'agents' || group === 'clients') {
        var rev = $('.iss-reveal[data-reveal="' + group + '"]');
        if (rev) rev.style.display = (val === 'yes') ? '' : 'none';
      }
    });
  });

  // --- leak slider ---
  var leak = $('#iss-leak');
  var leakLabel = $('#iss-leak-label');
  var leakYear = $('#iss-leak-year');
  function leakTrack(v) {
    var pct = (v / 6000) * 100;
    return 'linear-gradient(to right,#F4C542 0%,#F4C542 ' + pct.toFixed(1) + '%,#0F1E35 ' + pct.toFixed(1) + '%,#0F1E35 100%)';
  }
  if (leak) {
    leak.addEventListener('input', function () {
      state.leak = Number(leak.value);
      if (leakLabel) leakLabel.textContent = fmt(state.leak);
      if (leakYear) leakYear.textContent = fmt(state.leak * 12);
      leak.style.background = leakTrack(state.leak);
    });
  }

  // --- submit ---
  function buildPayload() {
    return {
      name: data.name || '',
      company: data.company || '',
      email: data.email || '',
      phone: data.phone || '',
      area: data.area || '',
      volume: data.volume || '',
      website: data.website || '',
      services: Object.keys(state.services).filter(function (k) { return state.services[k]; }),
      leak: state.leak,
      emailsAgents: state.agents,
      agentsExample: data.agentsExample || '',
      emailsClients: state.clients,
      clientsExample: data.clientsExample || '',
      promoToday: data.promoToday || '',
      wantsPromoBuild: state.promo
    };
  }

  function showConfirm() {
    var nm = (data.name || '').trim().split(' ')[0];
    var nc = $('#iss-name-comma');
    if (nc) nc.textContent = nm ? ', ' + nm : '';
    var form = $('#iss-form'), confirm = $('#iss-confirm');
    if (form) form.style.display = 'none';
    if (confirm) confirm.style.display = '';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function submit() {
    var btn = $('#iss-submit');
    var payload = buildPayload();
    showErr('');
    if (btn) { btn.disabled = true; btn.textContent = 'Submitting…'; }
    fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false, error: 'Unexpected server response.' }; });
    }).then(function (res) {
      if (res && res.ok) {
        showConfirm();
      } else {
        if (btn) { btn.disabled = false; btn.textContent = 'Submit application \u2192'; }
        showErr((res && res.error) ? res.error : 'Something went wrong submitting your application. Please try again, or email john@inspectionsupportservices.com.');
      }
    }).catch(function () {
      if (btn) { btn.disabled = false; btn.textContent = 'Submit application \u2192'; }
      showErr('Could not reach the server. Please check your connection and try again.');
    });
  }
  if ($('#iss-submit')) $('#iss-submit').addEventListener('click', submit);

  // init
  setStepUI();
})();
</script>"""

src = re.sub(
    r"<script type=\"text/x-dc\"[^>]*>.*?</script>",
    lambda m: vanilla, src, flags=re.DOTALL,
)

# Remove DCLogic wrapper tags
src = src.replace("<x-dc>", "").replace("</x-dc>", "")
src = src.replace("<helmet>", "").replace("</helmet>", "")

leftover = re.findall(r"\{\{[^}]*\}\}", src)
if leftover:
    sys.stderr.write("LEFTOVER TOKENS: %r\n" % leftover[:30])

with open(OUT, "w", encoding="utf-8") as f:
    f.write(src)

print("Wrote %s (%d bytes). Leftover tokens: %d" % (OUT, len(src), len(leftover)))
