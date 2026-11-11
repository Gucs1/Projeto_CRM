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
