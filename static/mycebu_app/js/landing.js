document.addEventListener("DOMContentLoaded", () => {
  const nav = document.querySelector(".nav-links");
  const links = document.querySelectorAll(".nav-links a");

  const highlight = document.createElement("span");
  highlight.classList.add("highlight");
  nav.appendChild(highlight);

  function moveHighlight(link) {
    const { offsetLeft, offsetWidth } = link;
    highlight.style.left = offsetLeft + "px";
    highlight.style.width = offsetWidth + "px";

    // update active styles
    links.forEach(l => l.classList.remove("active"));
    link.classList.add("active");
  }

  // default active
  const activeLink = document.querySelector(".nav-links a.active") || links[0];
  moveHighlight(activeLink);

  // move highlight on click
  links.forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      moveHighlight(link);
    });
  });
});
