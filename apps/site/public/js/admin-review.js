// Admin review page client.
//
// Fetches the three queues from /admin/api/review/* and wires the
// approve/reject buttons. CF Access injects the Cf-Access-Jwt-Assertion
// header on every request; the backend verifies it on every endpoint.
// We rely on credentials: 'include' so the browser sends the CF Access
// session cookie back through the proxy.
(function () {
  const API = '/admin/api';

  const FETCH_OPTS = { credentials: 'include', cache: 'no-store' };

  whoami();
  loadQueue('files',        listFiles,      renderFileRow);
  loadQueue('quarantine',   listQuarantine, renderQuarantineRow);
  loadQueue('translations', listTranslations, renderTranslationRow);

  // ── Top-right user badge ─────────────────────────────────────────
  function whoami() {
    const el = document.querySelector('[data-whoami]');
    if (!el) return;
    fetch(API + '/whoami', FETCH_OPTS)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error('not signed in'))))
      .then((d) => { el.textContent = d.email; })
      .catch(() => { el.textContent = 'unauthenticated'; el.classList.add('text-status-danger-fg'); });
  }

  // ── Queue loader (generic) ───────────────────────────────────────
  function loadQueue(name, fetchFn, rowFn) {
    const section = document.querySelector(`[data-queue="${name}"]`);
    if (!section) return;
    const list = section.querySelector('[data-list]');
    fetchFn().then((items) => {
      list.innerHTML = '';
      if (items.length === 0) {
        const p = document.createElement('p');
        p.className = 'text-sm italic text-ink-faint';
        p.textContent = 'Nothing to review.';
        list.appendChild(p);
        return;
      }
      for (const it of items) list.appendChild(rowFn(it));
    }).catch((err) => {
      list.innerHTML = '';
      const p = document.createElement('p');
      p.className = 'text-sm text-status-danger-fg';
      p.textContent = 'Failed to load: ' + err.message;
      list.appendChild(p);
    });
  }

  function listFiles()        { return fetch(API + '/review/files',        FETCH_OPTS).then(asJson); }
  function listQuarantine()   { return fetch(API + '/review/quarantine',   FETCH_OPTS).then(asJson); }
  function listTranslations() { return fetch(API + '/review/translations', FETCH_OPTS).then(asJson); }
  function asJson(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }

  // ── Files row ────────────────────────────────────────────────────
  function renderFileRow(it) {
    // shape: { id, confidence, reason, created_at, file_title, public_url,
    //          file_type, entry_slug, entry_title_en }
    const card = card3();
    card.appendChild(rowHead(
      it.entry_title_en + ' ← ' + it.file_title,
      'confidence ' + Number(it.confidence).toFixed(2) + ' · ' + it.file_type,
    ));
    if (it.reason) card.appendChild(small(it.reason));
    if (it.public_url) {
      const a = document.createElement('a');
      a.href = it.public_url;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.className = 'mt-1 inline-block text-xs underline';
      a.textContent = 'open file ↗';
      card.appendChild(a);
    }
    card.appendChild(actions([
      { label: 'Confirm', kind: 'ok',  url: `${API}/review/files/${it.id}/confirm` },
      { label: 'Reject',  kind: 'bad', url: `${API}/review/files/${it.id}/reject`  },
    ], card));
    return card;
  }

  // ── Quarantine row ───────────────────────────────────────────────
  function renderQuarantineRow(it) {
    // shape: { id, nextcloud_path, title, file_type, scan_result,
    //          scan_signatures, moderation_flag, error_message }
    const card = card3();
    const tag = it.scan_result === 'infected'
      ? 'infected'
      : it.moderation_flag
        ? 'moderation'
        : (it.scan_result || 'suspicious');
    card.appendChild(rowHead(it.title, tag + ' · ' + it.file_type));
    card.appendChild(small(it.nextcloud_path));
    if (it.scan_signatures) card.appendChild(small('Signatures: ' + it.scan_signatures));
    if (it.error_message)   card.appendChild(small(it.error_message));
    card.appendChild(actions([
      { label: 'Release',  kind: 'ok',  url: `${API}/review/quarantine/${it.id}/release` },
      { label: 'Delete',   kind: 'bad', url: `${API}/review/quarantine/${it.id}/delete`,
        confirm: 'Permanently delete this file row?' },
    ], card));
    return card;
  }

  // ── Translation row ──────────────────────────────────────────────
  function renderTranslationRow(it) {
    // shape: { entry_id, lang, title, summary, wiki_md, translation_status,
    //          source_lang, ai_draft_at, slug }
    const card = card3();
    card.appendChild(rowHead(it.title + '  (' + it.lang + ')',
      'from ' + (it.source_lang || '?') + ' · ' + it.translation_status));
    card.appendChild(small(it.slug));
    if (it.summary) card.appendChild(small(it.summary));
    if (it.wiki_md) {
      const pre = document.createElement('pre');
      pre.className = 'mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap rounded-sm bg-paper-3 p-2 text-xs';
      pre.textContent = it.wiki_md;
      card.appendChild(pre);
    }
    card.appendChild(actions([
      { label: 'Approve & publish', kind: 'ok', url: `${API}/review/translations/${it.entry_id}/${it.lang}/approve`,
        body: { publish: true } },
      { label: 'Mark reviewed',     kind: 'ok', url: `${API}/review/translations/${it.entry_id}/${it.lang}/approve`,
        body: { publish: false } },
    ], card));
    return card;
  }

  // ── Helpers ──────────────────────────────────────────────────────
  function card3() {
    const d = document.createElement('article');
    d.className = 'rounded-md border border-rule bg-paper-2 p-3';
    return d;
  }
  function rowHead(title, sub) {
    const wrap = document.createElement('header');
    wrap.className = 'flex items-baseline justify-between gap-3';
    const h = document.createElement('h3');
    h.className = 'font-serif text-base text-ink leading-tight';
    h.textContent = title;
    const s = document.createElement('span');
    s.className = 'text-2xs font-sans uppercase tracking-widest text-ink-mute';
    s.textContent = sub;
    wrap.append(h, s);
    return wrap;
  }
  function small(text) {
    const p = document.createElement('p');
    p.className = 'mt-1 text-xs text-ink-mute leading-snug';
    p.textContent = text;
    return p;
  }
  function actions(defs, card) {
    const row = document.createElement('div');
    row.className = 'mt-3 flex gap-2';
    for (const def of defs) {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = def.label;
      b.className = def.kind === 'ok'
        ? 'rounded-sm border border-rule bg-paper px-3 py-1 text-xs font-sans uppercase tracking-widest text-ink hover:border-gold'
        : 'rounded-sm border border-status-danger-fg bg-status-danger-bg px-3 py-1 text-xs font-sans uppercase tracking-widest text-status-danger-fg hover:bg-status-danger-fg hover:text-paper';
      b.addEventListener('click', () => doAction(def, card, b));
      row.appendChild(b);
    }
    return row;
  }
  function doAction(def, card, btn) {
    if (def.confirm && !window.confirm(def.confirm)) return;
    btn.disabled = true;
    fetch(def.url, {
      ...FETCH_OPTS,
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(def.body || {}),
    }).then((r) => (r.ok ? r.json() : Promise.reject(new Error('HTTP ' + r.status))))
      .then((res) => { toast(def.label + ': ' + res.status); card.remove(); })
      .catch((err) => { toast('Failed: ' + err.message, true); btn.disabled = false; });
  }
  function toast(msg, isError) {
    const el = document.querySelector('[data-toast]');
    if (!el) return;
    el.textContent = msg;
    el.classList.remove('hidden');
    if (isError) el.classList.add('bg-status-danger-fg');
    else el.classList.remove('bg-status-danger-fg');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.add('hidden'), 3500);
  }
})();
