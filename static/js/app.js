(() => {
  const menuButton = document.getElementById("menu-toggle");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");

  if (menuButton && sidebar && backdrop) {
    const closeMenu = (restoreFocus = true) => {
      sidebar.classList.add("-translate-x-full");
      sidebar.classList.remove("translate-x-0");
      backdrop.classList.add("hidden");
      menuButton.setAttribute("aria-expanded", "false");
      sidebar.inert = window.innerWidth < 1024;
      if (restoreFocus && window.innerWidth < 1024) menuButton.focus();
    };
    menuButton.addEventListener("click", () => {
      const isOpen = menuButton.getAttribute("aria-expanded") === "true";
      sidebar.classList.toggle("-translate-x-full", isOpen);
      sidebar.classList.toggle("translate-x-0", !isOpen);
      backdrop.classList.toggle("hidden", isOpen);
      menuButton.setAttribute("aria-expanded", String(!isOpen));
      sidebar.inert = isOpen;
    });
    backdrop.addEventListener("click", closeMenu);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeMenu();
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth >= 1024) {
        sidebar.inert = false;
        closeMenu(false);
      } else {
        sidebar.inert = menuButton.getAttribute("aria-expanded") !== "true";
      }
    });
    sidebar.inert = window.innerWidth < 1024;
  }

  const desktopMenuButton = document.getElementById("sidebar-desktop-toggle");
  if (desktopMenuButton) {
    const applyCollapsed = (collapsed) => {
      document.body.classList.toggle("sidebar-collapsed", collapsed);
      desktopMenuButton.setAttribute("aria-expanded", String(!collapsed));
      desktopMenuButton.setAttribute("aria-label", collapsed ? "Expandir menu" : "Recolher menu");
      desktopMenuButton.title = collapsed ? "Expandir menu" : "Recolher menu";
      try { window.localStorage.setItem("nexo-sidebar-collapsed", String(collapsed)); } catch (_) {}
    };
    let savedState = false;
    try { savedState = window.localStorage.getItem("nexo-sidebar-collapsed") === "true"; } catch (_) {}
    applyCollapsed(savedState);
    desktopMenuButton.addEventListener("click", () => {
      applyCollapsed(!document.body.classList.contains("sidebar-collapsed"));
    });
  }

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });

  const authCard = document.getElementById("auth-card");
  if (authCard) {
    const setMode = (mode, updateUrl = false, focus = false) => {
      if (!new Set(["login", "register"]).has(mode)) return;
      authCard.dataset.mode = mode;
      document.querySelectorAll("[data-auth-switch]").forEach((tab) => {
        tab.setAttribute("aria-selected", String(tab.dataset.authSwitch === mode));
      });
      document.querySelectorAll("[data-auth-panel]").forEach((panel) => {
        const inactive = panel.dataset.authPanel !== mode;
        panel.setAttribute("aria-hidden", String(inactive));
        panel.inert = inactive;
      });
      if (updateUrl) {
        const target = document.querySelector(`[data-auth-switch="${mode}"]`);
        if (target) window.history.replaceState({}, "", target.href);
      }
      if (focus) {
        const field = document.querySelector(`[data-auth-panel="${mode}"] input:not([type="hidden"])`);
        if (field) field.focus({ preventScroll: true });
      }
    };
    document.querySelectorAll("[data-auth-switch]").forEach((tab) => {
      tab.addEventListener("click", (event) => {
        event.preventDefault();
        setMode(tab.dataset.authSwitch, true, true);
      });
      tab.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const nextMode = tab.dataset.authSwitch === "login" ? "register" : "login";
        setMode(nextMode, true, true);
      });
    });
    setMode(authCard.dataset.mode || "login");
  }

  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = button.parentElement?.querySelector("input");
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-label", show ? "Ocultar senha" : "Mostrar senha");
      input.focus({ preventScroll: true });
    });
  });

  document.querySelectorAll('form[method="post"]').forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (event.defaultPrevented || form.dataset.submitting === "true") return;
      form.dataset.submitting = "true";
      form.setAttribute("aria-busy", "true");
      form.querySelectorAll('button[type="submit"]').forEach((button) => {
        button.disabled = true;
        const label = button.dataset.loadingText || "Salvando…";
        const spinner = document.createElement("span");
        spinner.className = "loading-indicator";
        spinner.setAttribute("aria-hidden", "true");
        const labelNode = document.createElement("span");
        labelNode.textContent = label;
        button.replaceChildren(spinner, labelNode);
      });
    });
  });

  const registerForm = document.querySelector('form[action$="/register"]');
  if (registerForm) {
    const password = registerForm.querySelector('input[name="password"]');
    const confirmation = registerForm.querySelector('input[name="confirm_password"]');
    const validateConfirmation = () => {
      if (!password || !confirmation) return;
      confirmation.setCustomValidity(
        confirmation.value && confirmation.value !== password.value
          ? "As senhas não conferem."
          : "",
      );
    };
    password?.addEventListener("input", validateConfirmation);
    confirmation?.addEventListener("input", validateConfirmation);
  }

  const itemContainer = document.getElementById("quote-items");
  const addItemButton = document.getElementById("add-quote-item");
  const quoteTotal = document.getElementById("quote-total");
  if (!itemContainer || !addItemButton || !quoteTotal) return;

  const formatCents = (cents) => {
    const digits = cents.toString().padStart(3, "0");
    const whole = digits.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return `R$ ${whole},${digits.slice(-2)}`;
  };

  const updateQuoteTotal = () => {
    let total = 0n;
    let invalidQuantity = false;
    itemContainer.querySelectorAll(".quote-item-row").forEach((row) => {
      const select = row.querySelector(".quote-product");
      const quantityInput = row.querySelector(".quote-quantity");
      const subtotal = row.querySelector(".quote-line-total");
      const price = select.selectedOptions[0]?.dataset.priceCents || "0";
      const quantityText = quantityInput.value;
      if (!select.value) {
        subtotal.textContent = formatCents(0n);
        return;
      }
      if (!/^\d+$/.test(quantityText) || Number(quantityText) < 1 || Number(quantityText) > 1000000) {
        invalidQuantity = true;
        subtotal.textContent = "Verifique a quantidade";
        return;
      }
      const lineTotal = BigInt(price) * BigInt(quantityText);
      total += lineTotal;
      subtotal.textContent = formatCents(lineTotal);
    });
    quoteTotal.textContent = invalidQuantity ? "Verifique as quantidades" : formatCents(total);
  };

  const addItemRow = () => {
    const rows = itemContainer.querySelectorAll(".quote-item-row");
    if (rows.length >= 50) return;
    const newRow = rows[0].cloneNode(true);
    newRow.querySelector(".quote-product").value = "";
    newRow.querySelector(".quote-quantity").value = "1";
    itemContainer.appendChild(newRow);
    updateQuoteTotal();
    newRow.querySelector(".quote-product").focus();
  };

  addItemButton.addEventListener("click", addItemRow);
  itemContainer.addEventListener("input", updateQuoteTotal);
  itemContainer.addEventListener("change", updateQuoteTotal);
  itemContainer.addEventListener("click", (event) => {
    const removeButton = event.target.closest(".remove-quote-item");
    if (!removeButton) return;
    const row = removeButton.closest(".quote-item-row");
    if (itemContainer.querySelectorAll(".quote-item-row").length > 1) {
      row.remove();
      updateQuoteTotal();
    }
  });
  updateQuoteTotal();
})();
