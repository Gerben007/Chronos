# Chronos — Locked Design Tokens

Source: Claude.ai design session, handed back 2026-05-17. Token names match the
prototype CSS variables 1:1, so the Phase 1 stylesheet can lift them straight
in. Companion to `docs/design-brief.md`.

Treat this file as **canonical**. Do not redefine these values elsewhere — the
Tailwind config and any global stylesheet must reference these names.

---

## Palette

```
Background paper:     #F4ECD8   (--paper)
Background secondary: #EFE5CC   (--paper-2)   — sidebar / hero band / cards
                      #E7DBBE   (--paper-3)   — input chrome, hover wash
                      #D9CBA8   (--paper-edge)— card edges
Text body:            #2F3A55   (--ink-2)     — body copy in long-form prose
                      #1F2A44   (--ink)       — strong / headings
Text heading:         #1F2A44   (--ink)
Text mute:            #5A607A   (--ink-mute)  — meta, captions
Text faint:           #8A8775   (--ink-faint) — disabled, hint chips
Rule:                 #CDBE99   (--rule)      — borders, hairlines
                      #DDCFA9   (--rule-soft) — secondary dividers

Accent primary:       #B8860B   (--gold)      — focus, links, decorative rules
Accent secondary:     #C9A227   (--gold-2)    — hover, illuminated-cap colour
Accent soft:          #E9D58A   (--gold-soft) — highlight wash, <mark>
Focus ring:           #B8860B   (--gold) at 2px, 2–3px offset
```

### Lane colours (label + soft-bg pair)

| Lane              | Label    | Soft bg  |
|-------------------|----------|----------|
| Bible Events      | #1F2A44  | #DAD4BE  |
| Bible People      | #1F2A44  | #DAD4BE  | *(same lane as Events — use prefix tag to distinguish)*
| Egypt             | #A88E3A  | #E8DCB2  |
| Rome              | #8B3A1F  | #E4C8B8  |
| Church history    | #5B4A6E  | #DCD2E0  | *(reserved — next)*
| Science           | #4F7A3E  | #DDE5CC  | *(reserved)*
| Arts              | #9A4225  | #ECD4C4  | *(reserved — close to Rome, pair with stronger stripe)*
| Reformation       | #2F5A6B  | #CDD9DD  | *(reserved)*

### Status (admin only)

| State              | Fg       | Bg       |
|--------------------|----------|----------|
| Ok / approved      | #4F7A3E  | #DFE7CC  |
| Warn / pending     | #B07B11  | #F2E5BC  |
| Danger / virus     | #9B2C1E  | #EFD0C9  |
| AI suggestion fill | #E9D58A  | #FBF6E8  |

### TV-gamma offset (only on `/tv` route)

```
--paper -2L · --ink +1L · --gold +6L  → roughly #EBE0C0 / #1B2336 / #D4A745
```

---

## Typography

```
Body serif:           Lora
                      weights: 400, 500, 600, 700 + italic 400, 500
                      self-host woff2
                      used for: H1–H4, article body, dates, blockquote,
                                lane band-labels
UI sans:              Inter
                      weights: 400, 500, 600, 700
                      self-host woff2
                      used for: nav, eyebrows/all-caps labels, meta rows,
                                buttons, counts/badges, axis tick labels
Mono (admin only):    JetBrains Mono, 400/500/600
                      for filenames, SHAs, breadcrumbs, tabular numbers
```

### Base sizes

| Surface  | Body | Title                |
|----------|------|----------------------|
| Mobile   | 14px | 17px (entry-card)    |
| Desktop  | 14px UI / 18px article body |  |
| TV       | 24px body / 28px row title  | 104px hero h1 (≥ 24px minimum enforced) |

### Scale

```
Scale ratio:          1.25 (major third); rounded to nearest px
Mobile / desktop:     11 · 12 · 14 · 16 · 18 · 22 · 26 · 32 · 40 · 84
TV:                   14 · 18 · 22 · 28 · 36 · 60 · 104 · 144 (hero only)

Tabular figures:      ON for years/dates/counts everywhere
                      (font-variant-numeric: tabular-nums)
                      --serif uses lining figures ("lnum") for H1 dates

Italic usage:         restrict to: dates, scripture, photo captions,
                                   era subtitles, AI "reasoning" prose,
                                   "we'll remember your choice" line,
                                   hover-revealed metadata.
                      Do NOT italicise body sentences.
```

---

## Spacing scale (px)

```
2 · 4 · 6 · 8 · 10 · 12 · 14 · 16 · 22 · 28 · 36 · 48 · 64 · 80 · 100
```

Denser than a pure 4/8 scale because the parchment aesthetic uses small odd
values (1px rules, 2px swatches, 6/14/22 paddings on cards). Snap to the
nearest value above.

---

## Border radius

```
sm:   3px   — chips, badges, swatches, dashed-corner "AI suggestion" callouts
md:   6px   — cards, inputs, sections
lg:   10px  — large cards, era-foot, mobile sheet
              (use 22px on the very top of bottom sheets only)
pill: 999px — language switch, era chips, lane swatches
```

---

## Shadow tokens

```
--shadow-paper:    0 1px 0 rgba(31,42,68,.04) inset, 0 8px 24px -16px rgba(31,42,68,.18)
--shadow-card:     0 1px 2px rgba(31,42,68,.06),     0 6px 18px -12px rgba(31,42,68,.18)
--shadow-hover:    0 1px 2px rgba(31,42,68,.06),     0 14px 28px -16px rgba(31,42,68,.28)
--shadow-tooltip:  0 8px 24px -12px rgba(31,42,68,.6)     (dark navy tooltip only)
--shadow-tv-focus: 0 0 0 4px #15110a, 0 0 0 8px #E9C462, 0 20px 50px rgba(0,0,0,.55)
                                                          (TV card focus only)
```

Never stack Material-style elevation; one shadow at a time. The "gold hairline
under the topbar" is a 1px linear-gradient, not a shadow.

---

## Components confirmed

- **Timeline marker** — three variants:
  - `.point` — dot, label rotates through 4 vertical positions
  - `.period` — bar with serif label + italic date
  - `.period.narrow` — solid coloured tick when visible width < 26px
- **Lane toggle row** — swatch + label + sublabel + eye icon; switch variant in the mobile sheet
- **Era jump button** — serif text, hover gold underline rule
- **Entry card (mobile)** — left lane stripe, title row (title + italic date), one-line blurb, resource icons + favourite, chevron
- **Resource item** — typed thumb (PDF / video / image / audio palette), title (2-line clamp), meta row, optional gold "Recommended" / grey "AI-suggested" badge
- **Scripture quote block** — `.scripture`: 2px gold left rule, italic serif, smaller than body, gold superscript verse numbers, all-caps citation foot
- **Cross-link card** — small kind label with swatch, serif title, italic date, blurb, gold "Open →" footer
- **Admin review row + detail pane** — left list with confidence chips (mini bar), right pane with file preview, AI reasoning, suggested-link rows with Confirm/Reject + autocomplete

---

## Decisions taken

- **Palette** — cream / navy / muted-gold direction kept. Earth-tone lane palette added (ochre Egypt, terracotta Rome). Four more lanes reserved. Status colours admin-only, sparingly applied.
- **Type pair** — Lora (serif) + Inter (sans). Lora for everything reading-like; Inter for UI chrome. JetBrains Mono on the admin route only.
- **Mobile chrome** — hamburger (left of wordmark) opens a bottom-sheet for lane controls. No bottom tab bar. Wordmark stays centred.
- **TV** — 2 rows visible with peek of a 3rd; card aspect 300×248 ≈ 1.21:1 (1.05× scale on focus, 1.08× lift). Hero band 568px tall.
- **Iconography** — custom inline SVG, stroke 1.6, rounded line caps, 24-viewBox default. No icon library — keeps the parchment aesthetic consistent and zero JS dependencies.

### Locked icon set

chevron · eye / eyeOff · lock · search · heart · plus · minus · fit · arrowL / arrowR · star (filled + outline) · pdf · video · image · audio · clock (small) · checkmark · x · refresh · ai-sun · external-link · download · trash · pencil · info-circle · warning-triangle · lock-shield (Cloudflare-style)

---

## Rejected directions (do not re-litigate)

- **TV carousel hero with rotating eras** — single static "Featured era" with decorative pagination dots wins; advancing is user-driven (d-pad/arrow keys only). Auto-rotation fails accessibility for kids.
- **Bible Events vs Bible People as separate lanes** — Phase 1 keeps them in the `bible` lane with a `BIBLE · PERSON` / `BIBLE · EVENT` prefix on cards. Splitting would force the mom-uploader to make a categorisation call she shouldn't have to.
- **Drop-cap on every paragraph** of `entry.html` — one drop-cap at the start of the entry only. Illuminated manuscripts don't drop-cap every paragraph.
- **Point labels at every importance level at default zoom** — labels render only when `importance ≥ threshold` (computed from span). Lower-importance entries get a "+N more" cluster instead.
- **Tabs on `entry.html` (Article / Resources / Related)** — 60/40 single-page layout reads as a museum label, not a SaaS dashboard. Tabs would hide content the kid might otherwise stumble into.
- **TV hover effects** — focus only; cards never react to a phantom cursor.
- **Inter for everything (no serif)** — serifs are essential to the illuminated-manuscript aesthetic and make dates feel historical rather than transactional.
- **Mobile bottom-tab bar** — see Decisions above.
- **Background-tint variant** (`rgb(209, 245, 238)` inline experiment on index) — flagged, not adopted. Inline override left in the prototype until decided.

---

## New constraints the design surfaced

1. **Afrikaans is ~15–25% longer than English in practice**, not 15%. "Babiloniese Ballingskap" vs "Babylonian Exile" is 23%; "Bybelse geskiedenis" vs "Biblical history" is 35%. Lane-toggle rows and entry-card titles need a confirmed 2-line variant; timeline period bars need ellipsis on either language without changing height.
2. **Period bars below ~26px visible width** need a solid-colour tick variant (not just a thin border), or they disappear into the parchment. Locked as `.period.narrow` — fill becomes the lane colour, no label.
3. **Lane "narrow" ticks at importance 5** need a gold ring so Christ's bar at full-history zoom remains the most prominent thing on the page — non-negotiable per the conservative-Protestant brief.
4. **Off-screen period bars must clamp their label to the visible left edge** (dynamic `padding-left`). Otherwise the kid sees a half-bar with the title's last letters mid-word.
5. **Tooltip default behaviour**: hover OR keyboard-focus-in-canvas only. Never auto-showing on load — overwhelming on the timeline.
6. **Search highlighting must include the Afrikaans variant** (e.g. searching "Moses" should also surface AF body matches for "Moses"). The search bar carries an explicit "Search Afrikaans too →" affordance.
7. **Admin route palette** uses the same tokens but gold is restricted to: the bottom 2px rule under the admin bar, the focus ring, the "Recommended" badge, and the dashed border on AI-suggestion blocks. Anywhere else, navy/cream only.
8. **TV needs a darker palette offset** (~-2L on paper, +6L on gold) so warm cream doesn't bloom on consumer LCDs. Locked as the TV-gamma offset above.
9. **The illuminated-corner ornaments on `landing.html`** are SVG, scale with viewport, need min screen width ~720px or they crowd the centred card. Below that: `@media (max-width: 720px) { .corner { display: none; } }`.
10. **AI confidence is shown as a chip with a tiny progress bar** (high/mid/low buckets — green/amber/grey), not a raw percentage. A raw `94%` reads as false precision.

---

## Reference mockups (in Claude.ai design session)

The prototype HTML files and reference screenshots live in the Claude.ai
design session, not this repo. Filenames captured for traceability:

```
screenshots/01-timeline-default.png        ← index.html @ -2500..600
screenshots/02-timeline-all-history.png    ← index.html with All-history era jumped
screenshots/03-timeline-patriarchs-af.png  ← Afrikaans switch on Patriarchs era
screenshots/04-entry-abraham-hero.png      ← entry.html top fold
screenshots/05-entry-abraham-bottom.png    ← entry.html article + resources + related
screenshots/06-mobile.png                  ← mobile.html (both phones)
screenshots/07-tv.png                      ← tv.html with Abraham focused
screenshots/08-landing.png                 ← landing.html
screenshots/09-admin-files.png             ← admin.html Files tab
screenshots/10-admin-translations.png      ← admin.html Translations tab
screenshots/11-admin-quarantine.png        ← admin.html Quarantine tab
screenshots/12-era-patriarchs.png          ← era.html
screenshots/13-search-moses.png            ← search.html
```

If we need a different state of any screen, re-capture in the design session.
