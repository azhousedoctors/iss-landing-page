#!/usr/bin/env python3
"""
Resolve ISS-Partner-Landing-CLEAN.html (Claude Design DCLogic export) into a
static, deployable index.html. Mirrors the renderVals() logic from the export's
<script type="text/x-dc"> block. Preserves all inlined data-URI lines untouched.
"""
import re, sys, html

SRC = "ISS-Partner-Landing-CLEAN.html"
OUT = "index.html"

with open(SRC, "r", encoding="utf-8") as f:
    src = f.read()

# ---------------------------------------------------------------------------
# Data mirrored from the export's renderVals()
# ---------------------------------------------------------------------------
services = [
    {"name": "Solar + energy audit", "cost": "from $247", "charge": "$325\u2013395", "keep": "$78\u2013148"},
    {"name": "Radon (single)",       "cost": "from $225", "charge": "$295\u2013350", "keep": "$70\u2013125"},
    {"name": "Sewer scope",          "cost": "$225 / $195 founding", "charge": "$325",  "keep": "$100 / $130"},
    {"name": "Air quality",          "cost": "from $80/pod", "charge": "$125\u2013150/pod", "keep": "$45\u201370/pod"},
    {"name": "Mold (tape / swab)",   "cost": "from $70/sample", "charge": "$125/sample", "keep": "$55/sample"},
]
faqData = [
    {"q": "Aren’t you my competitor?", "a": "Partly, yes, and we’d rather say it than have you find it on Google. Konnor runs his own inspection company in the East Valley. So the partner agreement carries a written non-solicit from us to you: we do not market to, contact, or accept general inspection work from any client or agent we meet on your job. If one of them calls us anyway, we send them back to you. No Breathe Easy cards, signs, or shirts on your jobs. Break that and you can terminate the same day. Our business only works if yours grows."},
    {"q": "Whose paperwork does my client sign?", "a": "Yours. We give you a one-paragraph addendum that names Inspection Support Services as the independent third-party provider and extends your agreement’s limitations to us. Drop it into the agreement your software already sends. If you’d rather we send our own white-label agreement under your brand, we can do that instead. Your call, once, at onboarding."},
    {"q": "Whose insurance is on the hook?", "a": "Ours. ISS carries its own general liability and E&O through OREP on every service we deliver. The report is co-branded, but the findings are ours and the liability is ours. A certificate of insurance is in your onboarding packet. This is not you subcontracting a guy under your license."},
    {"q": "How fast do reports come back?", "a": "Sewer scope: same day. Solar: within 24 hours, co-branded with SPRK Pro. Air quality: 24 hours from the lab. Radon: the report goes out the day the 48-hour test ends. Your deals live inside inspection periods; we don’t sit on finished reports."},
    {"q": "How do I pay you?", "a": "You pay when the report is delivered, not before. We invoice your card on delivery, and after the first job it’s saved so you never think about it again. No monthly fee, no setup fee."},
    {"q": "Whose brand is on the report?", "a": "Yours. Every report, every email, every piece of promo carries your logo and your name. To your client and their agent, this is a service you offer. We stay behind the scenes."},
    {"q": "Do I need to buy equipment or get certified?", "a": "No. ISS handles the service delivery and the reporting. You add the service to your quote. We do the work. That is the whole point of a white-label partner."},
    {"q": "What does it cost to join?", "a": "Nothing to apply and nothing to be a partner. You pay a flat partner rate per service you order, and you keep the spread between that and what you charge your client."},
    {"q": "How fast can I start offering services?", "a": "You’re set up within a week of approval. After your welcome call you have co-branded reports and the scripts ready to go."},
    {"q": "I am outside the Phoenix area. Can I still join?", "a": "Not yet. ISS currently serves the Greater Phoenix area. Tell us where you are anyway, so we can reach out when we expand."},
]

# ---------------------------------------------------------------------------
# 1) Remove the design-review compare switcher (Hero Opportunity/Loss control)
#    It's a dev artifact, not production UI.
# ---------------------------------------------------------------------------
# The switcher is a single <div ...> wrapping a <span> + two <button>s, closed
# by exactly ONE </div>. Match the comment + that div precisely.
m = re.search(r"<!-- \u2591\u2591 COMPARE SWITCHER.*?-->", src, flags=re.DOTALL)
if m:
    start = m.start()
    # find the opening fixed-position div after the comment
    div_open = src.find('<div style="position:fixed;bottom:18px', m.end())
    # walk to its matching close: this block has no nested <div>, only span/button
    div_close = src.find("</div>", div_open)
    end = div_close + len("</div>")
    # consume trailing whitespace
    while end < len(src) and src[end] in " \n\r\t":
        end += 1
    src = src[:start] + src[end:]

# ---------------------------------------------------------------------------
# 2) Resolve hero sc-if blocks: keep Loss (isLoss=true), drop Opportunity.
#    Loss-framed hero converts better (loss aversion > gain framing).
#    <sc-if value="{{ isLoss }}" ...> ... </sc-if>  -> inner kept
#    <sc-if value="{{ isOpp }}" ...> ... </sc-if> -> removed
# ---------------------------------------------------------------------------
def strip_scif(m):
    """Keep inner content (unwrap)."""
    return m.group(1)

# isLoss -> keep inner
src = re.sub(
    r"<sc-if value=\"\{\{ isLoss \}\}\"[^>]*>(.*?)</sc-if>",
    strip_scif, src, flags=re.DOTALL,
)
# isOpp -> drop entirely
src = re.sub(
    r"<sc-if value=\"\{\{ isOpp \}\}\"[^>]*>.*?</sc-if>",
    "", src, flags=re.DOTALL,
)

# ---------------------------------------------------------------------------
# 3) Resolve the services table sc-for into static rows.
# ---------------------------------------------------------------------------
row_tpl = (
    '        <div style="display:grid;grid-template-columns:1.6fr 1fr 1fr 1fr;gap:0;padding:18px 26px;border-bottom:1px solid rgba(255,255,255,.05);align-items:center;">\n'
    '          <span style="font-size:15.5px;font-weight:600;color:#F5F5F7;">{name}</span>\n'
    '          <span style="text-align:right;font-size:15px;color:#A1A5B0;">{cost}</span>\n'
    '          <span style="text-align:right;font-size:15px;color:#A1A5B0;">{charge}</span>\n'
    '          <span style="text-align:right;font-size:15.5px;font-weight:800;color:#F4C542;">{keep}</span>\n'
    '        </div>'
)
services_rows = "\n".join(
    row_tpl.format(
        name=html.escape(s["name"]), cost=html.escape(s["cost"]),
        charge=html.escape(s["charge"]), keep=html.escape(s["keep"]),
    ) for s in services
)
src = re.sub(
    r"<sc-for list=\"\{\{ services \}\}\"[^>]*>.*?</sc-for>",
    lambda m: services_rows, src, flags=re.DOTALL,
)

# ---------------------------------------------------------------------------
# 4) Resolve the FAQ sc-for into static accordion items (closed by default,
#    matching openFaq behavior -> all closed, vanilla JS toggles).
# ---------------------------------------------------------------------------
faq_item_tpl = (
    '          <div class="iss-faq" style="background:#1A2E4A;border:1px solid rgba(255,255,255,.07);border-radius:12px;overflow:hidden;">\n'
    '            <button type="button" class="iss-faq-btn" aria-expanded="false" style="width:100%;display:flex;justify-content:space-between;align-items:center;gap:16px;padding:21px 24px;background:none;border:none;cursor:pointer;text-align:left;color:#F5F5F7;font-family:\'Montserrat\';">\n'
    '              <span style="font-size:16.5px;font-weight:600;">{q}</span>\n'
    '              <span class="iss-faq-sign" style="font-size:22px;color:#3DB088;flex:none;line-height:1;">+</span>\n'
    '            </button>\n'
    '            <div class="iss-faq-ans" hidden style="padding:0 24px 22px;font-size:15.5px;line-height:1.62;color:#A1A5B0;">{a}</div>\n'
    '          </div>'
)
faq_items = "\n".join(
    faq_item_tpl.format(q=html.escape(f["q"]), a=html.escape(f["a"])) for f in faqData
)
src = re.sub(
    r"<sc-for list=\"\{\{ faqs \}\}\"[^>]*>.*?</sc-for>",
    lambda m: faq_items, src, flags=re.DOTALL,
)

# ---------------------------------------------------------------------------
# 5) Route CTAs to /apply. The export linked the final CTA button to
#    "ISS Partner Application.dc.html"; nav + hero used #apply anchor.
#    Two-route site: primary "apply" CTAs -> /apply. Keep in-page anchor
#    links (#apply, #calculator) as-is for on-page nav, EXCEPT convert the
#    nav + hero "Apply to Partner" buttons and footer link to /apply so the
#    user can always reach the form route.
# ---------------------------------------------------------------------------
# Final CTA button (explicit file link) -> /apply
src = src.replace('href="ISS Partner Application.dc.html"', 'href="/apply"')
# Nav, hero, footer "#apply" anchors -> /apply (route to the form page)
src = src.replace('href="#apply"', 'href="/apply"')

# ---------------------------------------------------------------------------
# 6) Replace the DCLogic <script type="text/x-dc"> block with a vanilla JS
#    runtime: scroll-reveal IntersectionObserver + FAQ accordion toggle.
# ---------------------------------------------------------------------------
vanilla_js = """<script>
(function () {
  // Scroll reveal
  var els = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    els.forEach(function (el) { io.observe(el); });
  } else {
    els.forEach(function (el) { el.classList.add('in'); });
  }

  // FAQ accordion (single-open behavior, matching the original openFaq state)
  var faqs = Array.prototype.slice.call(document.querySelectorAll('.iss-faq'));
  faqs.forEach(function (faq) {
    var btn = faq.querySelector('.iss-faq-btn');
    var ans = faq.querySelector('.iss-faq-ans');
    var sign = faq.querySelector('.iss-faq-sign');
    if (!btn || !ans || !sign) return;
    btn.addEventListener('click', function () {
      var isOpen = !ans.hidden;
      // close all
      faqs.forEach(function (other) {
        var oa = other.querySelector('.iss-faq-ans');
        var os = other.querySelector('.iss-faq-sign');
        var ob = other.querySelector('.iss-faq-btn');
        if (oa) oa.hidden = true;
        if (os) os.textContent = '+';
        if (ob) ob.setAttribute('aria-expanded', 'false');
      });
      // toggle this one
      if (!isOpen) {
        ans.hidden = false;
        sign.textContent = '\\u2212';
        btn.setAttribute('aria-expanded', 'true');
      }
    });
  });

  // Revenue calculator — multi-service chip model (works on touch + mouse)
  (function () {
    var jobs = document.getElementById('issJobs');
    var attach = document.getElementById('issAttach');
    var weeks = document.getElementById('issWeeks');
    if (!jobs || !attach || !weeks) return;
    var jobsV = document.getElementById('issJobsVal');
    var attachV = document.getElementById('issAttachVal');
    var weeksV = document.getElementById('issWeeksVal');
    var outMonth = document.getElementById('issOutMonth');
    var outYear = document.getElementById('issOutYear');
    var echo = document.getElementById('issEcho');
    var scalingCue = document.getElementById('issScalingCue');
    var chips = Array.prototype.slice.call(document.querySelectorAll('#issChipGrid .iss-chip'));

    function money(n) { return '$' + Math.round(n).toLocaleString('en-US'); }

    function getSpread() {
      var total = 0;
      chips.forEach(function (chip) {
        if (chip.classList.contains('active')) {
          total += parseInt(chip.getAttribute('data-val'), 10);
        }
      });
      return total;
    }

    function getActiveCount() {
      return chips.filter(function (c) { return c.classList.contains('active'); }).length;
    }

    function recalc() {
      var j = +jobs.value;
      var a = +attach.value / 100;
      var w = +weeks.value;
      var s = getSpread();
      var perYear = j * a * s * w;
      var perMonth = perYear / 12;
      jobsV.textContent = j;
      attachV.textContent = attach.value + '%';
      weeksV.textContent = w;
      outMonth.innerHTML = money(perMonth) + '<span class="suf">/mo</span>';
      outYear.innerHTML = money(perYear) + '<span class="suf">/yr</span>';
      var n = getActiveCount();
      var svcLabel = n === 1 ? '1 service' : n + ' services';
      echo.textContent = svcLabel + ', ' + j + ' jobs/week, ' + attach.value + '% attach';
      // 65% scaling cue
      if (scalingCue) {
        if (+attach.value >= 65) {
          scalingCue.classList.add('show');
          outYear.style.color = '#3DB088';
        } else {
          scalingCue.classList.remove('show');
          outYear.style.color = '';
        }
      }
    }

    // Chip toggle
    chips.forEach(function (chip) {
      chip.addEventListener('click', function () {
        var isActive = chip.classList.contains('active');
        chip.classList.toggle('active');
        chip.setAttribute('aria-pressed', !isActive ? 'true' : 'false');
        var box = chip.querySelector('.iss-chip-box');
        if (box) box.textContent = !isActive ? '\u2713' : '';
        recalc();
      });
    });

    [jobs, attach, weeks].forEach(function (el) {
      el.addEventListener('input', recalc);
      el.addEventListener('change', recalc);
    });
    recalc();
  })();
})();
</script>"""

src = re.sub(
    r"<script type=\"text/x-dc\"[^>]*>.*?</script>",
    lambda m: vanilla_js, src, flags=re.DOTALL,
)

# ---------------------------------------------------------------------------
# 7) Remove now-meaningless DCLogic wrapper tags (<x-dc>, <helmet>) but keep
#    their inner content. <helmet> wraps the <style>/<link> in <head>-ish area.
# ---------------------------------------------------------------------------
src = src.replace("<x-dc>", "").replace("</x-dc>", "")
src = src.replace("<helmet>", "").replace("</helmet>", "")

# Sanity: no template tokens should remain
leftover = re.findall(r"\{\{[^}]*\}\}", src)
if leftover:
    sys.stderr.write("LEFTOVER TOKENS: %r\n" % leftover[:20])

with open(OUT, "w", encoding="utf-8") as f:
    f.write(src)

print("Wrote %s (%d bytes). Leftover tokens: %d" % (OUT, len(src), len(leftover)))
