# Chronos — UI Design Brief (for a Claude.ai design session)

> **Use this document by:**
> 1. Open a new chat on **claude.ai** (web or desktop app).
> 2. Paste section 1 ("Context") and section 2 ("Constraints") first to load the project.
> 3. Then paste one screen prompt at a time from section 5. Ask Claude to produce a clickable HTML artifact (or React if you prefer).
> 4. Iterate on each screen. When happy, copy the final visual tokens (colours, fonts, spacing) into section 6 of this brief and hand it back to the developer (in this Claude Code session).

---

## 1. Context

**Project:** Chronos — an interactive Bible & world history timeline.

A self-hosted website where children browse a horizontal swim-lane timeline of biblical history (Creation → Christ → Reformation → today), with toggleable parallel lanes for civilisations like Egypt and Rome. Each timeline entry (a person, event, period, or prophecy) is a hub for curated learning resources: PDFs to print, videos to watch, images to view, audio to play.

**Audiences:**
- **Kids aged 5–13** — primary users. They browse the timeline, tap entries, watch videos, view PDFs. No login. They use the site on tablets, phones, and (in future) smart TVs.
- **Homeschool mothers** — drop files into a shared folder; never edit the site directly.
- **Admin (the developer)** — uses a protected review queue to approve AI-suggested file-to-entry links and AI-drafted Afrikaans translations.

**Tone:** scholarly but warm. Conservative Protestant orientation. Classical Conversations curriculum context. South African (English + Afrikaans). Not "kiddy" — kids respect a serious-looking interface more than a cartoony one. Inspired by the aesthetic of an illuminated manuscript or a museum exhibit, modernised.

---

## 2. Constraints (non-negotiable)

- **Bilingual from day one.** English and Afrikaans. Every screen needs to work in both. Afrikaans is often ~15% longer than English — labels must accommodate that without breaking layout.
- **Three viewports, equal polish:**
  - **Desktop** (≥ 1024px) — horizontal timeline canvas.
  - **Mobile** (< 768px) — vertical accordion grouped by era.
  - **TV lean-back** (`/tv` route, or `?tv=1`) — large fonts, generous spacing, arrow-key navigation only, no hover dependencies.
- **Accessibility:** every interactive element keyboard-reachable (arrow keys + Enter), visible focus rings, screen-reader-friendly. There is also a parallel `<table>` view of any timeline data — kids using assistive tech aren't second-class.
- **No third-party fonts loaded from CDN.** Self-host (or use system fonts).
- **No tracking, no analytics scripts.** Privacy-clean.
- **Dates can be BC.** Years format as `1010 BC` / `AD 30` (English) and `1010 v.C.` / `n.C. 30` (Afrikaans).
- **Static-first.** The interactive timeline canvas is one island; everything else is server-rendered HTML.

---

## 3. Aesthetic direction (starting point — refine in design)

The developer's first instinct (open to revision based on your mockups):

- **Palette:**
  - Background "parchment": warm cream `#F5EFE0`
  - Heading deep navy: `#1F3A5F`
  - Accent muted gold: `#B8860B`
  - Lane colours: earth tones (forest green, clay red, mustard, slate, plum, terracotta) — not saturated UI primaries.
- **Type:**
  - Body: a humanist serif — Lora or Crimson Pro candidates.
  - UI chrome (nav, buttons): a humanist sans — Inter or Source Sans 3.
  - Date axis: tabular figures.
- **Iconography:** simple line icons (Lucide).
- **References for mood:** an old wall-mounted school history chart; the typography of a Penguin Classics paperback; a museum interpretive panel. **Avoid:** flat-design pastel, generic SaaS, gamified-kids-app look.

If a different palette/type direction serves the audience better, propose it with reasoning.

---

## 4. Information architecture

```
/                       Language picker (one-time)
/en/                    Home — featured eras, recent additions
/en/timeline            The big interactive canvas (or mobile accordion)
/en/era/[slug]          Period landing (e.g. Patriarchs, Kingdoms, Reformation)
/en/lane/[slug]         All entries in one lane (e.g. Egypt)
/en/entry/[slug]        Single entry — wiki + resources + scripture + cross-links
/en/about
/admin/review           Admin: files + translations awaiting review
/tv                     TV lean-back home

(Mirrored under /af/ for Afrikaans)
```

**Lane groups** (drives sidebar grouping):
- Biblical (base, always on): Bible Events, Bible People
- Empires: Egypt, Rome (Phase 1); later Assyria, Babylon, Persia, Greece, China
- Church history: Reformation, Councils, Missions (Phase 3)
- Science / invention (Phase 3)
- Arts / literature / music (Phase 3)

---

## 5. Screen prompts (paste one at a time)

Each prompt below is self-contained. Paste it, get an HTML artifact, iterate, then move on. The order is by priority — start at the top.

### 5.1 Timeline canvas — DESKTOP (the heart of the product)

> Mock a desktop view of an interactive horizontal timeline at `/en/timeline`. Layout:
>
> - Top bar (height ~64px): Chronos wordmark left; centre = era jump buttons (Patriarchs, Kingdoms, Christ, Reformation, All history); right = language switch (EN/AF), favourites, search icon.
> - Left sidebar (width ~280px): collapsible groups of lane toggles. Groups: "Biblical (base — always on, locked)", "Empires", "Church history", "Science", "Arts". In Phase 1 only Biblical + Empires (Egypt, Rome) are populated. Each lane row shows its colour swatch + label + visibility eye icon.
> - Main canvas: horizontal swim-lane timeline spanning ~4000 BC to AD 2100. Each lane is a horizontal row, colour-coded. Entries appear as pill-shaped markers (point events) or bars (periods). Hover/focus a marker shows a tooltip with title + dates. Click navigates to the entry page.
> - Bottom: a slim mini-map overview showing the visible time range, draggable.
> - At wide zoom, only "importance ≥ 4" entries show labels; the rest show as dots, with "+N more" pills where dense.
>
> Use the palette in section 3 (warm cream background, deep navy text, muted-gold accents, earth-tone lanes). Use Lora for any large display text and Inter for UI chrome. Show BC dates as e.g. "1010 BC" on the axis.
>
> Populate with sample data: Adam, Noah, Abraham, Joseph, Moses, David, Solomon, Babylonian Exile, Christ, Apostles — and parallel Egypt entries (Old Kingdom, Middle Kingdom, New Kingdom, Cleopatra) and Roman entries (Roman Republic, Julius Caesar, Augustus, Constantine).
>
> Make all keyboard-reachable; show focus rings on the lane toggles and one marker.

### 5.2 Entry page — DESKTOP

> Mock a desktop entry page at `/en/entry/abraham`. Layout:
>
> - Top nav same as the timeline page.
> - Hero band: title "Abraham" left; dates "c. 2166 – 1991 BC" below; lane badge ("Bible People" with its earth-tone colour); on the right, an artwork thumbnail (oil-painted look, attribution caption below).
> - Two-column body: left (60%) = wiki article in Markdown-rendered form (a few headings, paragraphs, a blockquote scripture passage shown inline with verse text in a slightly indented serif block, citation "Genesis 12:1-3 KJV"). Right (40%) = resources panel.
> - Resources panel: grouped by type (Videos, PDFs, Images, Audio). Each group shows a small icon + count. Each item: thumbnail (or type-icon) + title + duration/size + a small badge ("Recommended" gold, or "AI-suggested" subtle grey). Videos play inline when clicked; PDFs open in an embedded viewer; images open a lightbox.
> - Below the body: "Related" — horizontal scroll of related entries (e.g. Isaac, Sarah, Promised Land, Covenant). Cross-link cards.
> - Footer: prev/next within parent period ("← Patriarchs · Next: Isaac →").
>
> Keep the parchment-cream background, deep-navy headings, gold accents. Make the scripture quote visually distinctive but not loud — think slim left rule, italic, slightly smaller.

### 5.3 Mobile accordion view

> Mock a mobile view of `/en/timeline` (375px wide). The desktop canvas is replaced by a vertical accordion. Layout:
>
> - Sticky top bar: hamburger left (opens lane-toggle sheet), Chronos wordmark centre, language toggle right.
> - Below: era chips horizontally scrollable (Patriarchs, Kingdoms, Christ, Reformation, All).
> - Main: vertical list grouped by era. Each era is a collapsible section. Within an era, each entry is a card showing: lane colour stripe on left, title, dates, one-line summary, "→" chevron. Tap navigates to entry page.
> - Lane-toggle sheet (when hamburger tapped): full-screen modal with grouped lane toggles, same groups as desktop.
>
> Same palette + type. Touch targets at least 44px tall. No pinch-zoom inside any region.

### 5.4 TV lean-back home (`/tv`)

> Mock a "sofa view" home page designed for a smart TV (1920×1080) browsed with arrow keys + Enter on a remote. Layout:
>
> - Full-bleed era hero at top: large background artwork (e.g. illuminated manuscript style), era name in very large serif ("The Patriarchs"), a one-line description, large "Explore →" button.
> - Below: horizontal carousel rows, Netflix-style: "Featured Bible People", "Featured Bible Events", "Egypt", "Rome". Each row has 4-5 large cards visible. Cards: artwork top, title + dates below.
> - Focus state: the currently focused card grows slightly (1.05x), shows a thick gold focus ring, and reveals the entry summary. Adjacent cards dim.
> - Top right corner: small clock + language indicator. No mouse hover effects, ever.
>
> Fonts must be readable from 3 metres on a 50-inch TV. Treat body text as ≥ 24px equivalent. Generous spacing. Same parchment-warm palette but a touch darker to handle TV gamma.

### 5.5 Language picker landing (`/`)

> Mock the one-time landing page at `/`. Centred card on a warm-cream full-screen background. Card contents:
>
> - Small Chronos wordmark at top.
> - Heading: "Choose your language / Kies jou taal".
> - Two large buttons side by side: "English" and "Afrikaans" — each shows its flag (UK + ZA) and the language name.
> - Below buttons: small text "We'll remember your choice."
> - Subtle decorative motif (a thin gold flourish or a small illuminated initial) so it doesn't feel like a tech form.
>
> No nav, no footer. Single decision, then redirect.

### 5.6 Admin review queue (`/admin/review`)

> Mock the admin review queue, behind Cloudflare Access. This is a tool, not a public-facing page — it can be denser. Tabs at top: "Files (12)", "Translations (4)", "Quarantine (1)".
>
> Files tab layout:
> - Two-column. Left (40%): list of files needing link review, each row = thumbnail + filename + AI summary first line + confidence badge. Selected row highlighted.
> - Right (60%): selected file detail. Inline preview (PDF embed / image / video player). Below: AI's reasoning ("Likely about Moses because: …"). Below: AI's suggested entry links, each with confidence, "Confirm" / "Reject" buttons, plus a "Link to other entry…" autocomplete.
>
> Translations tab: same two-column. Left = entries with AI-drafted Afrikaans pending review. Right = side-by-side diff: English source on the left, Afrikaans draft on the right, editable. Buttons: "Approve & publish", "Save edits", "Reject (regenerate)".
>
> Quarantine tab: file thumbnail + scan reason (ClamAV signature or AI moderation flag). "Release" / "Delete permanently" actions.
>
> Visually utilitarian — closer to GitHub's review UI than to the public site. Keep the cream / navy / gold palette but use it more sparingly. Dense data tables OK here.

### 5.7 Era / lane landing (lower priority)

> Mock `/en/era/patriarchs`. Hero with era name, dates, brief description, key figures listed. Below: a focused mini-timeline of just this era + a grid of entry cards in chronological order. Pattern should extend naturally to `/en/lane/egypt`.

### 5.8 Search results (Phase 3 — mock to validate pattern)

> Mock `/en/search?q=Moses`. Results in two groups: "Entries" (top, with lane + dates), "Files" (below, with type icon + parent entry). Each result shows a snippet with the search term highlighted. Filters in left rail: by lane, by type (entry vs file), by era.

---

## 6. What to hand back

When you've locked the visual direction, fill in the values below and paste this section back into the Claude Code session:

```
## Locked design tokens

Palette:
  Background paper:     #______
  Background secondary: #______
  Text body:            #______
  Text heading:         #______
  Accent primary:       #______
  Accent secondary:     #______
  Focus ring:           #______
  Lane colours:
    Bible Events:       #______
    Bible People:       #______
    Egypt:              #______
    Rome:               #______
    [reserved slots for future lanes: ______]

Typography:
  Body serif:           ______ (weights: ______)
  UI sans:              ______ (weights: ______)
  Base size mobile:     ______px
  Base size desktop:    ______px
  Base size TV:         ______px
  Scale ratio:          ______
  Tabular figures on:   [ ] yes / [ ] no

Spacing scale (px):    4, 8, 12, 16, 24, 32, 48, 64, 96  (or custom: ______)
Border radius:          sm ______px / md ______px / lg ______px
Shadow tokens:          (describe or paste)

Components confirmed:
  [ ] Timeline marker (pill, bar, dot variants)
  [ ] Lane toggle row
  [ ] Era jump button
  [ ] Entry card (mobile)
  [ ] Resource item (with type icon + badge)
  [ ] Scripture quote block
  [ ] Cross-link card
  [ ] Admin review row + detail pane

Decisions taken:
  [ ] Keep / adjust palette direction in section 3 — note any changes
  [ ] Keep / replace type pair — note final choice
  [ ] Mobile chrome: hamburger vs bottom-tab — chose: ______
  [ ] TV row count and card aspect ratio: ______
  [ ] Iconography library: Lucide / Phosphor / custom — chose: ______
```

Also hand back:
- One screenshot per locked screen (drop them into a `mockups/` folder if you want them version-controlled).
- Any rejected directions worth recording (so we don't re-litigate later).
- Any new constraints the design surfaced (e.g. "lane labels need a 2-line variant").

---

## 7. Out of scope for this design session

- Authoring tools (Google Sheet UI lives outside the site in Phase 1–2; admin web UI deferred to Phase 3).
- Email templates (no email is sent).
- Marketing site / landing page for public launch — different brief.
- Logo / wordmark beyond a wordmark text treatment — a real mark can come later.
- Kodi addon UI — that's a separate brief when Phase 3 arrives.

---

## 8. One last thing

Push back if any of section 3 (palette, type) feels wrong for the audience. The developer cares more about the result than about defending the initial direction. If you propose a change, give the one-sentence reason; if it's good, it'll stick.
