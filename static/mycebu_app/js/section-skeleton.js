document.addEventListener("DOMContentLoaded", () => {
  const sections = [...document.querySelectorAll("[data-skel]")];

  const preloadImages = (root) => {
    const imgs = [...root.querySelectorAll("img")];
    if (imgs.length === 0) return Promise.resolve();

    const loaders = imgs.map((img) => {
      if (img.complete) return Promise.resolve();

      const src = img.currentSrc || img.getAttribute("src");
      if (!src) return Promise.resolve();

      return new Promise((res) => {
        const probe = new Image();
        probe.onload = probe.onerror = () => res();
        const co = img.getAttribute("crossorigin");
        if (co) probe.crossOrigin = co;
        probe.src = src;
      });
    });

    return Promise.allSettled(loaders);
  };

  const withTimeout = (p, ms = 1500) =>
    Promise.race([
      p,
      new Promise((res) => setTimeout(res, ms))
    ]);

  const reveal = async (sec) => {
    if (sec.dataset.loaded === "true") return;
    const content = sec.querySelector(".section-content");
    await withTimeout(preloadImages(content), 1800);
    setTimeout(() => {
      sec.dataset.loading = "false";
      sec.dataset.loaded = "true";
    }, 120);
  };

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          reveal(e.target);
          io.unobserve(e.target);
        }
      });
    },
    { rootMargin: "200px" }
  );

  sections.forEach((sec) => {
    // Ensure required structure exists
    if (!sec.querySelector(".section-skeleton") || !sec.querySelector(".section-content")) return;
    sec.dataset.loading = "true";
    io.observe(sec);
  });
});
