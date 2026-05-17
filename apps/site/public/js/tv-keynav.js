// TV remote / arrow-key navigation across .tv-card elements.
// Up/Down jumps a row (4-column grid); Left/Right within a row.
// Loaded synchronously so first arrow-press after page paint always works.
(function () {
  var cols = 4;
  function cards() { return Array.from(document.querySelectorAll('.tv-card')); }
  function idx() { return cards().findIndex(function (c) { return c === document.activeElement; }); }
  function focus(n) {
    var all = cards();
    if (!all.length) return;
    var next = Math.max(0, Math.min(all.length - 1, n));
    all[next].focus();
    all[next].scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
  document.addEventListener('keydown', function (e) {
    var i = idx();
    if (i < 0) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowRight') focus(0);
      return;
    }
    switch (e.key) {
      case 'ArrowRight': e.preventDefault(); focus(i + 1); break;
      case 'ArrowLeft':  e.preventDefault(); focus(i - 1); break;
      case 'ArrowDown':  e.preventDefault(); focus(i + cols); break;
      case 'ArrowUp':    e.preventDefault(); focus(i - cols); break;
    }
  });
  window.addEventListener('load', function () {
    var first = cards()[0];
    if (first) first.focus({ preventScroll: true });
  });
})();
