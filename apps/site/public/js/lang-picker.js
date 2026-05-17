// Language-picker landing. If a preference already exists, redirect
// immediately; otherwise record the user's pick when they click EN/AF.
(function () {
  try {
    var saved = localStorage.getItem('chronos.lang');
    if (saved === 'en' || saved === 'af') {
      location.replace('/' + saved + '/');
      return;
    }
  } catch (_) { /* show picker */ }

  function remember(lang) {
    try { localStorage.setItem('chronos.lang', lang); } catch (_) {}
  }
  document.addEventListener('DOMContentLoaded', function () {
    var en = document.getElementById('pick-en');
    var af = document.getElementById('pick-af');
    if (en) en.addEventListener('click', function () { remember('en'); });
    if (af) af.addEventListener('click', function () { remember('af'); });
  });
})();
