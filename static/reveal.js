// reveal.js - site-wide reveal-on-scroll logic
(function () {
  'use strict';
  function initReveal() {
    console.log('[reveal.js] initializing reveal animations');
    const POST_LOAD_DELAY = 90;
    try {
      if (!('IntersectionObserver' in window)) {
        console.warn('[reveal.js] IntersectionObserver not supported — revealing all elements immediately as a fallback');
        document.querySelectorAll('[data-reveal], .reveal').forEach((el, idx) => {
          const delay = (el.dataset && el.dataset.revealDelay) ? parseInt(el.dataset.revealDelay, 10) : (90 + (idx * 25));
          setTimeout(() => el.classList.add('visible'), delay);
        });
        return;
      }

      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const configured = entry.target.dataset.revealDelay;
            const baseDelay = configured ? parseInt(configured, 10) : 100;
            const rect = entry.target.getBoundingClientRect();
            const stagger = Math.min(Math.max(Math.round(rect.top / 100), 0), 6) * 30;
            setTimeout(() => entry.target.classList.add('visible'), baseDelay + stagger);
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.35 });

      document.querySelectorAll('[data-reveal], .reveal').forEach((el, idx) => {
        if (!el.hasAttribute('data-reveal-delay')) el.dataset.revealDelay = 90 + (idx * 25);
        if (!el.classList.contains('reveal')) el.classList.add('reveal');
        observer.observe(el);
      });
    } catch (err) {
      console.error('[reveal.js] error during reveal initialization', err);
      document.querySelectorAll('[data-reveal], .reveal').forEach((el) => el.classList.add('visible'));
    }
  }

  if (document.readyState === 'complete') {
    // page already loaded
    setTimeout(initReveal, 90);
  } else {
    window.addEventListener('load', () => setTimeout(initReveal, POST_LOAD_DELAY));
  }
})();
