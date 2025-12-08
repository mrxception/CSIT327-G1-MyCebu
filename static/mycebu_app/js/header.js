document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector(".topnav .nav-links");
  if (nav) {
    const highlight = nav.querySelector(".highlight");
    const links = Array.from(nav.querySelectorAll("a"));
    if (highlight && links.length > 0) {
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
    }
  }

  const body = document.body;
  const btn = document.getElementById("hamburger");
  const drawer = document.getElementById("mobile-drawer");
  const overlay = document.getElementById("mobile-overlay");
  const closeBtn = document.getElementById("drawer-close");

  if (btn && drawer && overlay && closeBtn) {
    const open = () => {
      body.classList.add("menu-open");
      btn.setAttribute("aria-expanded", "true");
      drawer.setAttribute("aria-hidden", "false");
    };
    const close = () => {
      body.classList.remove("menu-open");
      btn.setAttribute("aria-expanded", "false");
      drawer.setAttribute("aria-hidden", "true");
    };

    btn.addEventListener("click", () =>
      body.classList.contains("menu-open") ? close() : open()
    );
    overlay.addEventListener("click", close);
    closeBtn.addEventListener("click", close);
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") close();
    });

    drawer.querySelectorAll("a").forEach((a) => {
      a.addEventListener("click", close);
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 768) close();
    });
  }

  // Profile dropdown functionality
  const profileDropdown = document.querySelector('.profile-dropdown');
  const avatarButton = document.querySelector('.avatar-button');

  if (profileDropdown && avatarButton) {
    const toggleDropdown = () => {
      profileDropdown.classList.toggle('active');
    };

    const closeDropdown = () => {
      profileDropdown.classList.remove('active');
    };

    avatarButton.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleDropdown();
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
      if (!profileDropdown.contains(e.target)) {
        closeDropdown();
      }
    });

    // Close dropdown when clicking on menu items
    const dropdownMenu = profileDropdown.querySelector('.dropdown-menu');
    if (dropdownMenu) {
      dropdownMenu.addEventListener('click', (e) => {
        if (e.target.tagName === 'A') {
          closeDropdown();
        }
      });
    }

    // Close dropdown on escape key
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeDropdown();
      }
    });
  }
});
