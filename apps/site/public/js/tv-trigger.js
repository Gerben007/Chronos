// TV-mode trigger. Loaded synchronously from BaseLayout <head> so the
// .tv class is applied before paint — avoids a flash of non-TV chrome.
// Honours: ?tv=1 / ?tv=0 (sticky), localStorage.tvMode, viewport hints.
(function () {
  try {
    var url = new URL(location.href);
    var param = url.searchParams.get('tv');
    if (param === '1') localStorage.setItem('tvMode', 'true');
    if (param === '0') localStorage.removeItem('tvMode');
    var saved = localStorage.getItem('tvMode') === 'true';
    var viewportHints = matchMedia('(min-width: 1280px) and (pointer: coarse)').matches;
    if (saved || param === '1' || viewportHints) {
      document.documentElement.classList.add('tv');
    }
  } catch (_) { /* private mode etc. */ }
})();
