// Live resources fetcher.
//
// On the entry page, this script fetches /data/resources.json (served from
// a shared volume the ingest container writes to) and replaces the server-
// rendered list. The baked-in list at build time acts as a fallback if
// the fetch fails or 404s.
(function () {
  const slug = (function () {
    // URL shape: /<lang>/entry/<slug>
    const parts = location.pathname.split('/').filter(Boolean);
    const i = parts.indexOf('entry');
    return i >= 0 && parts[i + 1] ? parts[i + 1] : null;
  })();
  if (!slug) return;

  const aside = document.querySelector('[data-resources-panel]');
  if (!aside) return;
  const lang = aside.getAttribute('data-lang') || 'en';

  fetch('/data/resources.json', { cache: 'no-store' })
    .then((r) => (r.ok ? r.json() : null))
    .then((data) => {
      if (!data) return;
      const items = data[slug] || [];
      render(aside, items, lang);
    })
    .catch(() => { /* keep server-rendered fallback */ });

  function render(host, items, lang) {
    if (!items.length) {
      host.querySelector('[data-resources-list]')?.remove();
      const empty = host.querySelector('[data-resources-empty]');
      if (!empty) {
        const p = document.createElement('p');
        p.setAttribute('data-resources-empty', '');
        p.className = 'mt-2 text-sm italic text-ink-faint';
        p.textContent = lang === 'af' ? 'Nog geen lêers gekoppel nie.' : 'No files linked yet.';
        host.appendChild(p);
      }
      return;
    }
    host.querySelector('[data-resources-empty]')?.remove();
    const ul = document.createElement('ul');
    ul.setAttribute('data-resources-list', '');
    ul.className = 'mt-3 space-y-3';
    for (const r of items) {
      ul.appendChild(buildRow(r, lang));
    }
    const existing = host.querySelector('[data-resources-list]');
    if (existing) existing.replaceWith(ul); else host.appendChild(ul);
  }

  function buildRow(r, lang) {
    const li = document.createElement('li');
    li.className = 'border-b border-rule-soft pb-3 last:border-b-0 last:pb-0';

    const a = document.createElement('a');
    a.href = r.public_url;
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
    a.className = 'font-serif text-sm text-ink hover:text-gold no-underline';
    a.textContent = r.title;
    li.appendChild(a);

    const meta = document.createElement('div');
    meta.className = 'mt-0.5 text-2xs font-sans uppercase tracking-widest text-ink-faint';
    const pieces = [r.file_type];
    if (r.cc_cycle != null) {
      pieces.push((lang === 'af' ? 'Siklus ' : 'Cycle ') + r.cc_cycle
        + (r.cc_week != null ? ' · Wk ' + r.cc_week : ''));
    }
    if (r.age_min != null && r.age_max != null) {
      pieces.push(r.age_min + '–' + r.age_max + ' ' + (lang === 'af' ? 'jr' : 'yr'));
    }
    meta.textContent = pieces.join(' · ');
    li.appendChild(meta);

    const summary = (lang === 'af' ? r.summary_af : r.summary_en) || r.summary_en;
    if (summary) {
      const p = document.createElement('p');
      p.className = 'mt-1 text-xs italic text-ink-mute leading-snug';
      p.textContent = summary;
      li.appendChild(p);
    }
    return li;
  }
})();
