// JS for upload page: form submit + reveal-on-scroll
document.addEventListener("DOMContentLoaded", () => {
  console.log('[upload.js] DOMContentLoaded — upload script initialized');
  // --- Form submit handler ---
  const form = document.getElementById("classify-form");
  const resultContainer = document.getElementById("result-container");
  const resultJson = document.getElementById("result-json");

  if (form) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const jobRole = document.getElementById("job-role").value;
      const jobDescription = document.getElementById("job-description").value;
      const resumeText = document.getElementById("resume-text").value;

      const payload = { job_role: jobRole, job_description: jobDescription, resume_text: resumeText };

      try {
        const response = await fetch('/classify', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (resultJson) {
          resultJson.textContent = JSON.stringify(result, null, 2);
          resultJson.style.color = (result.prediction === 'Select') ? '#27ae60' : '#c0392b';
        }
        if (resultContainer) resultContainer.classList.remove('d-none');

      } catch (error) {
        if (resultJson) {
          resultJson.textContent = JSON.stringify({ error: "Could not connect to server. Is app.py running?" }, null, 2);
          resultJson.style.color = '#c0392b';
        }
        if (resultContainer) resultContainer.classList.remove('d-none');
      }
    });
  }

  // --- Reveal-on-scroll using IntersectionObserver ---
  // Wait until full page load (images/stylesheets) to start reveal animations to avoid layout jank
  window.addEventListener('load', () => {
    const POST_LOAD_DELAY = 1000; // ms - small buffer after load
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
            if (entry.isIntersecting) {
              // read optional per-element delay (ms) or use default
              const configured = entry.target.dataset.revealDelay;
              const baseDelay = configured ? parseInt(configured, 10) : 100;
              // Add a tiny stagger based on vertical position to make multiple items feel natural
              const rect = entry.target.getBoundingClientRect();
              const stagger = Math.min(Math.max(Math.round(rect.top / 100), 0), 6) * 30;
              setTimeout(() => {
                entry.target.classList.add('visible');
              }, baseDelay + stagger);
              observer.unobserve(entry.target);
            }
          });
        }, { threshold: 0.35 });

        document.querySelectorAll('[data-reveal], .reveal').forEach((el, idx) => {
          // If author hasn't set a data-reveal-delay, expose a small auto-stagger
          if (!el.hasAttribute('data-reveal-delay')) el.dataset.revealDelay = 90 + (idx * 25);
          // Ensure the element has the CSS class used for initial state
          if (!el.classList.contains('reveal')) el.classList.add('reveal');
          observer.observe(el);
        });
      } catch (err) {
        console.error('[upload.js] Reveal initialization error:', err);
        // Best-effort fallback: make everything visible
        document.querySelectorAll('[data-reveal], .reveal').forEach((el) => el.classList.add('visible'));
      }
    }, POST_LOAD_DELAY);
  });
});
