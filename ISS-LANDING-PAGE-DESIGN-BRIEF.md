# ISS Landing Page — Design Brief
**For:** Claude interactive design session  
**Date:** 2026-06-20  
**Owner:** Arlo / Stirling Integrated Solutions  
**Status:** Ready for design phase. DO NOT build until design is approved by John.

---

## What This Page Is

A partner recruitment landing page for **Inspection Support Services (ISS)** — a white-label ancillary inspection service for Arizona home inspectors. Inspectors offer add-on services (radon, air quality, sewer scope, solar) under their own brand. ISS does the work. The inspector keeps the spread.

**The audience is a licensed Arizona home inspector.** Probably solo or small team. Probably seeing 8–15 jobs/week. Skeptical of marketing claims. Motivated by money they're currently leaving on the table.

**The one job of this page:** Get qualified inspectors to click Apply. That's it.

---

## What Already Exists

An HTML landing page was previously built (`landing-page/index.html`). It has solid copy and good bones but was built without a design phase first. This redesign should start from visual first principles, then use the copy from that file as the content source.

**Existing sections to carry forward (mapped by ID):**
1. `#top` — Hero: *"Stop Referring Business Away."*
2. `#problem` — *"What You're Giving Away Every Week"* (the revenue math)
3. `#how-it-works` — *"Three Steps. That's It."*
4. `#services` — *"What ISS Offers — and What You Keep"* (pricing table)
5. `#perks` — *"What You Get When You're Approved"* (co-branded reports, scripts, marketing infra, welcome call)
6. `#who` — *"Who the ISS Network Is Built For"* (qualifying criteria)
7. `#faq` — FAQ section
8. `#faq-1` — Application CTA: *"Apply to Join the ISS Partner Network"*

The copy in those sections is usable. Design pass should focus on **layout, visual hierarchy, section pacing, and component design** — not rewriting every word.

---

## Brand

### ISS Identity
- **Company name:** Inspection Support Services (ISS)
- **Tagline:** "The Ancillary Team Inspectors Trust"
- **Logo to use:** `iss-logo-v5-minimal-primary.jpg` (clean shield, "ISS" centered, navy/orange, no tagline — most professional for B2B)
- **Backup/full variant:** `iss-logo-v3-ancillary-team-PRIMARY.jpg` (includes tagline, use in footer or secondary placements)

### Color Palette
From the existing page — proven and on-brand:
```
--bg:           #0F1E35   (deep navy, page background)
--panel:        #1A2E4A   (card backgrounds)
--panel-light:  #1E3455   (lighter panel variant)
--accent:       #3DB088   (teal/green — primary CTA, highlight color)
--accent-dark:  #2E9070   (hover state for accent)
--text-primary: #F5F5F7   (near-white)
--text-secondary: #A1A5B0
--text-dim:     #6B7280
--success:      #4ADE80
--warning:      #FBBF24
```

**Note:** The ISS logo itself uses navy + orange. The page uses navy + teal. This contrast — orange in the logo, teal for CTAs — works because they don't compete. Keep this balance. Don't introduce orange as a page accent.

### Typography
- **Headings:** Playfair Display (serif) — authoritative, not corporate
- **Body:** Inter (sans-serif) — clean, readable at small sizes
- Both are already loaded in the existing page via Google Fonts.

---

## Design Direction

### Tone and Vibe
Professional services, not consumer home services. The inspectors seeing this page are licensed professionals with business costs and margins in mind. The design should feel like a financial services partner or a trades B2B brand — not a home services franchise.

Think: **clean, dense with value, zero decoration for its own sake.** Every visual element should earn its place by making the offer clearer or the value more tangible.

### What Works in the Existing Page
- Dark navy background creates strong contrast and a premium feel
- Teal accent pops well against the dark panels
- The section structure (problem → solution → how it works → services → CTA) is solid direct-response architecture
- The pricing table section is doing real work — it shows the math

### What Needs Improvement
- **Visual hierarchy is flat.** Too many sections have similar visual weight. The hero, the revenue math, and the CTA need to feel distinctly more important than the interior sections.
- **The hero lacks a visual anchor.** Currently text-heavy. Needs something — a mockup, a stat block, a revenue calculator hint — that stops the scroll.
- **Section spacing is uniform and slightly dull.** Alternating dark/slightly-less-dark panels works but doesn't create momentum. Consider more deliberate use of full-bleed sections vs. contained cards.
- **The CTA section is buried.** "Apply to Join the ISS Partner Network" needs to feel like a destination, not an afterthought. It should feel like crossing a threshold.

### Design Goals for This Pass
1. **Hero section:** Strong headline, immediate revenue hook, one clear CTA button. Consider a stat block or "what you could be making" visual on the right column.
2. **The revenue math section:** This is the emotional trigger. It should hit harder visually — big numbers, clear contrast, maybe a simple before/after layout.
3. **Services + pricing section:** This is the rational justification. Clean table, clear spreads, nothing buried.
4. **The application CTA:** Feels like an invitation to a network, not a generic form. Maybe a card-style treatment with the logo and one sentence of what happens after you apply.
5. **Mobile-first thinking:** Inspectors will likely see this on a phone. Every section needs to look intentional at 390px wide.

---

## Page Goals and Conversion Logic

**Primary CTA:** Apply to Join the ISS Partner Network  
**Secondary CTA:** None — single-focus page, don't split attention  

**What a qualified applicant looks like:**
- Licensed Arizona home inspector (AZBTR)
- Doing residential inspections, not commercial-only
- Currently passing on or referring out radon, sewer scope, air quality, or solar
- Looking to increase per-job revenue without adding overhead

**Disqualifying criteria to surface:**
- Commercial-only inspectors (ISS serves residential)
- Inspectors outside Arizona (for now)
- Inspectors who want to do the ancillary work themselves

The FAQ section handles objections. The "Who This Is For" section handles qualification.

---

## Reference Sites to Pull DNA From

Before starting the design, ask Claude to pull design DNA from 1–2 of these:

- **[Linear.app](https://linear.app)** — B2B SaaS, dark mode, strong typographic hierarchy. Reference for clean section pacing and stat treatment.
- **[Stripe.com](https://stripe.com)** — Trust signals in a financial-adjacent brand. Reference for how to make "you handle the work, we handle the infrastructure" feel premium.
- **[Notion.so](https://notion.so)** — Reference for feature grids and "what's included" section design.
- **[Lasso.io](https://lasso.io)** or **[Pitch.com](https://pitch.com)** — Reference for application/partner page design patterns.

Not looking to copy. Looking to extract: **how do premium B2B brands lay out a problem/solution/CTA page on a dark background?**

---

## Copy Source

All copy lives in the existing HTML file:  
`/mnt/c/Users/Admin/Dropbox/Stirling Ecosystem/Inspection Support Services/landing-page/index.html`

The design session should use that as the copy source. If copy needs to change based on layout decisions, note it — but don't rewrite sections wholesale without flagging.

For pricing specifics, source of truth is:  
`/mnt/c/Users/Admin/Dropbox/Stirling Ecosystem/Inspection Support Services/ISS-STRATEGY.md`

---

## Deliverable

A **reviewed and approved design** that includes:
- Layout decisions for each section (column structure, visual anchors, spacing logic)
- Typography scale (which headings use Playfair vs. Inter, sizes, weights)
- CTA button treatment and placement
- Mobile breakpoint notes
- Any copy changes flagged

Once John signs off on the design, this brief plus the design output goes to Mason (Claude Code) for the build.

---

## What Mason Gets After Design

Mason's build brief will reference:
- This design brief
- The approved design output (from the Claude session)
- The existing `index.html` (copy source)
- The ISS logo files in `landing-page/` and `brand/`
- `ISS-STRATEGY.md` for any pricing or copy accuracy checks
- Deployment target: Vercel (existing `vercel.json` in `landing-page/`)
