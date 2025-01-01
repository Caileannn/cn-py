// script.js
document.addEventListener("DOMContentLoaded", () => {
    const menuToggle = document.querySelector("#menu-btn");
    const hiddenMenu = document.querySelector("#nav-menu");
  
    menuToggle.addEventListener("click", () => {
      hiddenMenu.classList.toggle("show");
    });
  });
  