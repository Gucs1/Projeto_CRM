(() => {
  const button = document.getElementById("menu-toggle");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");

  if (!button || !sidebar || !backdrop) return;

  const closeMenu = () => {
    sidebar.classList.add("-translate-x-full");
    sidebar.classList.remove("translate-x-0");
    backdrop.classList.add("hidden");
    button.setAttribute("aria-expanded", "false");
  };

  button.addEventListener("click", () => {
    const isOpen = button.getAttribute("aria-expanded") === "true";
    if (isOpen) {
      closeMenu();
      return;
    }
    sidebar.classList.remove("-translate-x-full");
    sidebar.classList.add("translate-x-0");
    backdrop.classList.remove("hidden");
    button.setAttribute("aria-expanded", "true");
  });

  backdrop.addEventListener("click", closeMenu);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeMenu();
  });
  window.addEventListener("resize", () => {
    if (window.innerWidth >= 1024) closeMenu();
  });

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
})();
