// ...existing code...
if (window.__hh_upload_initialized) {
  console.warn('[upload.js] already initialized — skipping duplicate initialization');
} else {
  window.__hh_upload_initialized = true;

  // Original file contents below...
  document.addEventListener("DOMContentLoaded", () => {
    console.log('[upload.js] DOMContentLoaded — upload script initialized');
    // --- Form submit handler (populates structured results, typewriter) ---
    const form = document.getElementById("classify-form");
    const resultContainer = document.getElementById("result-container");
    const resultPlaceholder = document.getElementById("result-placeholder");
    const roleEl = document.getElementById('result-role');
    const badgeEl = document.getElementById('result-badge');
    const confEl = document.getElementById('result-confidence');
    const genaiText = document.getElementById('result-genai-text');
    const jdText = document.getElementById('result-jd-text');
    const improvementEl = document.getElementById('improvement-suggestions');

    function setBadge(badgeEl, prediction) {
      if (!badgeEl) return;
      badgeEl.innerHTML = '';
      const span = document.createElement('span');
      span.className = prediction === 'Select' ? 'badge-select' : 'badge-reject';
      span.textContent = prediction === 'Select' ? 'Select' : 'Reject';
      badgeEl.appendChild(span);
    }

    function typewriter(element, text, speed = 18) {
      if (!element) return Promise.resolve();
      element.textContent = '';
      let i = 0;
      return new Promise((resolve) => {
        const timer = setInterval(() => {
          element.textContent += text.charAt(i);
          i++;
          if (i >= text.length) {
            clearInterval(timer);
            resolve();
          }
        }, speed);
      });
    }

    if (form) {
      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (resultPlaceholder) resultPlaceholder.classList.add('d-none');
        if (improvementEl) improvementEl.textContent = '';

        const jobRole = document.getElementById('job-role').value;
        const jobDescription = document.getElementById('job-description').value;
        const resumeText = document.getElementById('resume-text').value;

        const payload = { job_role: jobRole, job_description: jobDescription, resume_text: resumeText };

        try {
          const response = await fetch('/classify', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
          });
          const result = await response.json();

          if (roleEl) roleEl.textContent = result.role || jobRole;
          setBadge(badgeEl, (result && result.ml_prediction) ? result.ml_prediction : 'Reject');
          if (confEl) confEl.textContent = `Confidence: ${result.ml_confidence || '--'}`;
          if (genaiText) genaiText.textContent = result.gen_ai_assessment || '';
          if (jdText) jdText.textContent = result.resume_jd_comparison || '';

          if (improvementEl) {
            const suggestions = result.improvement_suggestions || 'No suggestions available.';
            await typewriter(improvementEl, suggestions, 18);
          }

          if (resultContainer) resultContainer.classList.remove('d-none');
        } catch (err) {
          if (resultContainer) resultContainer.classList.remove('d-none');
          if (improvementEl) improvementEl.textContent = 'Error: Could not connect to server. Is app.py running?';
        }
      });
    }

    // --- Reveal-on-scroll using IntersectionObserver (toggle visibility on exit) ---
    // Wait until full page load (images/stylesheets) to start reveal animations to avoid layout jank
    
    window.addEventListener('load', () => {
      const POST_LOAD_DELAY = 500; // ms - small buffer after load
      setTimeout(() => {
        try {
          if (!('IntersectionObserver' in window)) {
            console.warn('[upload.js] IntersectionObserver not supported — revealing all elements immediately as a fallback');
            // Fallback: reveal everything with a small stagger
            document.querySelectorAll('[data-reveal], .reveal').forEach((el, idx) => {
              const delay = (el.dataset && el.dataset.revealDelay) ? parseInt(el.dataset.revealDelay, 10) : (90 + (idx * 25));
              setTimeout(() => el.classList.add('visible'), delay);
            });
            return;
          }

          const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
              const el = entry.target;
              const configured = el.dataset.revealDelay;
              const baseDelay = configured ? parseInt(configured, 10) : 100;
              const rect = el.getBoundingClientRect();
              const stagger = Math.min(Math.max(Math.round(rect.top / 100), 0), 6) * 30;

              if (entry.isIntersecting) {
                setTimeout(() => el.classList.add('visible'), baseDelay + stagger);
              } else {
                el.classList.remove('visible');
              }
            });
          }, { threshold: 0.35 });

          document.querySelectorAll('[data-reveal], .reveal').forEach((el, idx) => {
            if (!el.hasAttribute('data-reveal-delay')) el.dataset.revealDelay = 90 + (idx * 25);
            if (!el.classList.contains('reveal')) el.classList.add('reveal');
            observer.observe(el);
          });
        } catch (err) {
          console.error('[upload.js] Reveal initialization error:', err);
          document.querySelectorAll('[data-reveal], .reveal').forEach((el) => el.classList.add('visible'));
        }
      }, POST_LOAD_DELAY);
    });
    
  });
}
// ...existing code...