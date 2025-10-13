document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector(".topnav .nav-links");
  if (!nav) return;

  const highlight = nav.querySelector(".highlight");
  const links = Array.from(nav.querySelectorAll("a"));
  if (!highlight || links.length === 0) return;

  const getActive = () => nav.querySelector("a.active") || links[0];

  const moveTo = (el, { animate = true } = {}) => {
    const navBox = nav.getBoundingClientRect();
    const linkBox = el.getBoundingClientRect();
    const x = Math.round(linkBox.left - navBox.left);
    const w = Math.round(linkBox.width);

    if (!animate) {
      const prev = highlight.style.transition;
      highlight.style.transition = "none";
      highlight.style.width = `${w}px`;
      highlight.style.transform = `translateX(${x}px)`;
      void highlight.offsetHeight;
      highlight.style.transition = prev || "";
    } else {
      highlight.style.width = `${w}px`;
      highlight.style.transform = `translateX(${x}px)`;
    }
    highlight.style.opacity = "1";
  };

  moveTo(getActive(), { animate: false });

  links.forEach((link) => {
    link.addEventListener("mouseenter", () => moveTo(link));
    link.addEventListener("focus", () => moveTo(link));
    link.addEventListener("mouseleave", () => moveTo(getActive()));
    link.addEventListener("blur", () => moveTo(getActive()));
    link.addEventListener("click", () => moveTo(link));
  });

  window.addEventListener("resize", () => moveTo(getActive(), { animate: false }));
});

// ===== Minimal hamburger toggle (added) =====
document.addEventListener("DOMContentLoaded", () => {
  const topnav = document.querySelector(".topnav");
  const hamburger = document.querySelector(".hamburger");
  const mobileMenu = document.getElementById("mobile-menu");

  if (!topnav || !hamburger || !mobileMenu) return;

  const closeMenu = () => {
    topnav.classList.remove("mobile-open");
    hamburger.setAttribute("aria-expanded", "false");
    mobileMenu.setAttribute("hidden", "");
  };

  hamburger.addEventListener("click", () => {
    const nowOpen = !topnav.classList.contains("mobile-open");
    if (nowOpen) {
      topnav.classList.add("mobile-open");
      hamburger.setAttribute("aria-expanded", "true");
      mobileMenu.removeAttribute("hidden");
    } else {
      closeMenu();
    }
  });

  mobileMenu.querySelectorAll("a").forEach((a) => {
    a.addEventListener("click", closeMenu);
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 768) closeMenu();
  });

  document.addEventListener("click", (e) => {
    if (!topnav.classList.contains("mobile-open")) return;
    if (!topnav.contains(e.target)) closeMenu();
  });
});
