// Reveal-on-scroll animation
document.addEventListener('DOMContentLoaded', () => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        // read optional per-element delay (ms) or use default
        const configured = entry.target.dataset.revealDelay;
        const baseDelay = configured ? parseInt(configured, 10) : 150;
        
        setTimeout(() => {
          entry.target.classList.add('reveal-active');
        }, baseDelay);
        
        observer.unobserve(entry.target);
      }
    });
  }, { 
    threshold: 0.15,
    rootMargin: '0px 0px -50px 0px' // trigger slightly before element enters viewport
  });

  // Observe all elements with the reveal-card class
  document.querySelectorAll('.reveal-card').forEach((el, idx) => {
    // If author hasn't set a data-reveal-delay, add auto-stagger
    if (!el.hasAttribute('data-reveal-delay')) {
      el.dataset.revealDelay = 100 + (idx * 120);
    }
    observer.observe(el);
  });
});
