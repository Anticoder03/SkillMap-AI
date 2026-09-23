/* CareerPath AI — shared JavaScript */
(function () {
  'use strict';

  // Theme toggle
  const themeToggle = document.getElementById('theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', function () {
      const root = document.documentElement;
      const dark = root.classList.toggle('dark');
      localStorage.setItem('careerpath-theme', dark ? 'dark' : 'light');
    });
  }

  // Mobile menu toggle
  const mobileBtn = document.getElementById('mobile-menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  if (mobileBtn && mobileMenu) {
    mobileBtn.addEventListener('click', function () {
      mobileMenu.classList.toggle('hidden');
    });
  }
})();