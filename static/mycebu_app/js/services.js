document.addEventListener("click", function (event) {
  const item = event.target.closest(".step-item");
  if (!item) return;
  item.classList.toggle("active");
});