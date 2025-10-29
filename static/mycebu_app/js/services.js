document.addEventListener("DOMContentLoaded", () => {
  const stepItems = document.querySelectorAll(".step-item");
  
  stepItems.forEach(item => {
    item.addEventListener("click", () => {
      item.classList.toggle("active");
    });
  });
});
