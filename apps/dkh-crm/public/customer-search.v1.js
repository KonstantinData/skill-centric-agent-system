(() => {
  const controllers = new WeakMap();
  const latestQueries = new WeakMap();
  const openFilesKey = "dkh.openCustomerFiles";
  const maxOpenFiles = 3;

  const readOpenFiles = () => {
    try {
      const parsed = JSON.parse(localStorage.getItem(openFilesKey) || "[]");
      return Array.isArray(parsed) ? parsed.filter(Boolean).slice(0, maxOpenFiles) : [];
    } catch {
      return [];
    }
  };

  const writeOpenFiles = (items) => {
    try {
      localStorage.setItem(openFilesKey, JSON.stringify(items.slice(0, maxOpenFiles)));
    } catch {
      // Continue without cross-window tracking when storage is unavailable.
    }
  };

  const trackCurrentFile = () => {
    const match = window.location.pathname.match(/^\/kunden\/([^/]+)/);
    const customerId = match ? decodeURIComponent(match[1]) : "";
    if (!customerId) return;
    const files = readOpenFiles().filter((id) => id !== customerId);
    files.push(customerId);
    writeOpenFiles(files);
    window.addEventListener("pagehide", () => {
      writeOpenFiles(readOpenFiles().filter((id) => id !== customerId));
    });
  };

  const openCustomerFile = (href, customerId) => {
    const id = String(customerId || "");
    const files = readOpenFiles().filter((entry) => entry !== id);
    if (id && files.length >= maxOpenFiles) {
      alert("Es können maximal drei Kundenakten parallel geöffnet werden.");
      return;
    }
    if (id) {
      files.push(id);
      writeOpenFiles(files);
    }
    const opened = window.open(href, id ? "kundenakte-" + id : "_blank", "noopener");
    if (opened) {
      opened.focus();
      return;
    }
    window.location.href = href;
  };

  trackCurrentFile();

  document.addEventListener("click", (event) => {
    const link = event.target instanceof Element
      ? event.target.closest("[data-customer-file-link]")
      : null;
    if (!link) return;
    event.preventDefault();
    openCustomerFile(link.href, link.getAttribute("data-customer-id"));
  });

  const setResults = (root, items, options) => {
    const results = root.querySelector("[data-customer-search-results]");
    const hint = root.querySelector("[data-customer-search-hint]");
    const createModal = document.querySelector("[data-customer-create-modal]");
    results.innerHTML = "";
    if (!items.length) {
      results.hidden = true;
      hint.textContent = options.openCreateModal
        ? "Kein Treffer. Jetzt kann ein neuer Kunde angelegt werden."
        : "Kein Treffer.";
      if (options.openCreateModal && createModal) createModal.hidden = false;
      return;
    }
    const list = document.createElement("div");
    list.className = "suggest-list";
    for (const customer of items) {
      const row = document.createElement("article");
      row.className = "suggest-row";
      row.tabIndex = 0;
      row.title = "Doppelklick öffnet die Kundenakte";
      const href = "/kunden/" + encodeURIComponent(customer.customer_id);
      row.addEventListener("dblclick", () => openCustomerFile(href, customer.customer_id));
      row.addEventListener("keydown", (event) => {
        if (event.key === "Enter") openCustomerFile(href, customer.customer_id);
      });

      const copy = document.createElement("div");
      copy.className = "suggest-copy";
      const title = document.createElement("strong");
      title.textContent = customer.display_name || "Unbenannter Kunde";
      const meta = document.createElement("span");
      const type = customer.customer_type === "company" ? "Firma" : "Privat";
      const location = [customer.postal_code, customer.city].filter(Boolean).join(" ");
      meta.textContent = [type, location, customer.primary_email].filter(Boolean).join(" · ");
      copy.append(title, meta);

      const action = document.createElement("a");
      action.className = "btn btn-secondary";
      action.href = href;
      action.target = "_blank";
      action.rel = "noopener";
      action.setAttribute("data-customer-file-link", "");
      action.setAttribute("data-customer-id", String(customer.customer_id));
      action.textContent = "Kundenakte öffnen";

      row.append(copy, action);
      list.append(row);
    }
    results.append(list);
    results.hidden = false;
    if (options.openCreateModal && createModal) createModal.hidden = true;
    hint.textContent = items.length + " Treffer gefunden.";
  };

  const createModal = document.querySelector("[data-customer-create-modal]");
  const createCaseToggle = document.querySelector("[data-customer-create-case-toggle]");
  const caseDetails = document.querySelector("[data-customer-case-details]");
  const createForm = document.querySelector("[data-customer-create-form]");
  const customerTypeSelect = document.querySelector("[data-customer-type-select]");
  const emailDuplicateModal = document.querySelector("[data-customer-email-duplicate-modal]");
  const emailDuplicateResults = document.querySelector("[data-customer-email-duplicate-results]");
  const emailDuplicateConfirm = document.querySelector("[data-customer-email-duplicate-confirm]");
  let pendingDuplicateFormData = null;

  const closeCreateModal = () => {
    if (createModal) createModal.hidden = true;
  };

  const syncCaseDetails = () => {
    if (!createCaseToggle || !caseDetails) return;
    const enabled = createCaseToggle.checked;
    caseDetails.hidden = !enabled;
    for (const field of caseDetails.querySelectorAll("input, select, textarea")) {
      if (!field.name) continue;
      field.disabled = !enabled;
    }
  };

  const syncCustomerTypeSections = () => {
    if (!customerTypeSelect) return;
    const selectedType = customerTypeSelect.value || "private";
    for (const section of document.querySelectorAll("[data-customer-type-section]")) {
      const enabled = section.getAttribute("data-customer-type-section") === selectedType;
      section.hidden = !enabled;
      for (const field of section.querySelectorAll("input, select, textarea")) {
        if (!field.name) continue;
        field.disabled = !enabled;
      }
    }
  };

  const resetSearch = (root, options) => {
    const results = root.querySelector("[data-customer-search-results]");
    const hint = root.querySelector("[data-customer-search-hint]");
    results.hidden = true;
    results.innerHTML = "";
    if (options.openCreateModal) closeCreateModal();
    hint.textContent = "Geben Sie mindestens drei Zeichen ein.";
  };

  const runSearch = async (root, options) => {
    const input = root.querySelector("[data-customer-search-input]");
    const results = root.querySelector("[data-customer-search-results]");
    const hint = root.querySelector("[data-customer-search-hint]");
    const filter = root.querySelector("[data-customer-status-filter]");
    const query = input.value.trim();
    const filterValue = filter && filter.value ? filter.value : "";
    const searchKey = query + "::" + filterValue;
    latestQueries.set(root, searchKey);
    if (query.length < 3) {
      const currentController = controllers.get(root);
      if (currentController) currentController.abort();
      resetSearch(root, options);
      return;
    }
    const currentController = controllers.get(root);
    if (currentController) currentController.abort();
    const controller = new AbortController();
    controllers.set(root, controller);
    hint.textContent = "Suche läuft...";
    try {
      const params = new URLSearchParams({ q: query });
      if (filterValue) params.set("status", filterValue);
      const response = await fetch("/api/kunden/search?" + params.toString(), {
        headers: { accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("search_failed");
      const payload = await response.json();
      if (input.value.trim() + "::" + filterValue !== latestQueries.get(root)) return;
      const items = Array.isArray(payload.customers) ? payload.customers : [];
      setResults(root, items, options);
    } catch (error) {
      if (error.name === "AbortError") return;
      results.hidden = true;
      if (options.openCreateModal) closeCreateModal();
      hint.textContent = "Suche aktuell nicht verfügbar.";
    }
  };

  const setupSearch = (root, options) => {
    if (!root) return;
    const input = root.querySelector("[data-customer-search-input]");
    const filter = root.querySelector("[data-customer-status-filter]");
    if (!input) return;
    input.addEventListener("input", () => runSearch(root, options));
    if (filter) {
      filter.addEventListener("change", () => runSearch(root, options));
    }
  };

  const closeEmailDuplicateModal = () => {
    pendingDuplicateFormData = null;
    if (emailDuplicateModal) emailDuplicateModal.hidden = true;
  };

  const renderDuplicateMatches = (matches) => {
    if (!emailDuplicateResults) return;
    emailDuplicateResults.innerHTML = "";
    for (const customer of matches) {
      const row = document.createElement("article");
      row.className = "rounded-lg border border-[var(--border)] bg-white p-4";

      const title = document.createElement("p");
      title.className = "font-bold";
      title.textContent = customer.display_name || "Unbenannter Kunde";

      const meta = document.createElement("p");
      meta.className = "text-sm text-[var(--muted)]";
      const location = [customer.postal_code, customer.city].filter(Boolean).join(" ");
      meta.textContent = [
        customer.customer_number || "Ohne Kundennummer",
        customer.primary_email,
        customer.primary_phone,
        location,
      ].filter(Boolean).join(" · ");

      const cases = document.createElement("p");
      cases.className = "mt-1 text-sm text-[var(--muted)]";
      cases.textContent = "Aktive Vorgänge: " + (customer.active_case_count || 0);

      const action = document.createElement("a");
      action.className = "btn btn-secondary mt-3";
      action.href = "/kunden/" + encodeURIComponent(customer.customer_id);
      action.target = "_blank";
      action.rel = "noopener";
      action.setAttribute("data-customer-file-link", "");
      action.setAttribute("data-customer-id", String(customer.customer_id));
      action.textContent = "Kundenakte öffnen";

      row.append(title, meta, cases, action);
      emailDuplicateResults.append(row);
    }
  };

  const submitCreateForm = async (formData) => {
    if (!createForm) return;
    const response = await fetch(createForm.action, {
      method: "POST",
      headers: { accept: "application/json" },
      body: formData,
    });
    const payload = await response.json().catch(() => ({}));
    if (response.status === 409 && payload.error === "customer_email_duplicate_found") {
      pendingDuplicateFormData = formData;
      renderDuplicateMatches(Array.isArray(payload.matches) ? payload.matches : []);
      if (emailDuplicateModal) emailDuplicateModal.hidden = false;
      return;
    }
    if (!response.ok || !payload.ok) {
      alert("Kunde konnte nicht gespeichert werden.");
      return;
    }
    window.location.href = payload.customer_id
      ? "/kunden/" + encodeURIComponent(payload.customer_id)
      : "/kunden";
  };

  if (createModal) {
    createModal.addEventListener("click", (event) => {
      if (event.target === createModal) closeCreateModal();
      const closeButton = event.target instanceof Element
        ? event.target.closest("[data-customer-create-close]")
        : null;
      if (closeButton) closeCreateModal();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeCreateModal();
    });
  }

  if (createCaseToggle) {
    createCaseToggle.addEventListener("change", syncCaseDetails);
    syncCaseDetails();
  }

  if (customerTypeSelect) {
    customerTypeSelect.addEventListener("change", syncCustomerTypeSections);
    syncCustomerTypeSections();
  }

  if (createForm) {
    createForm.addEventListener("submit", (event) => {
      event.preventDefault();
      submitCreateForm(new FormData(createForm));
    });
  }

  if (emailDuplicateModal) {
    emailDuplicateModal.addEventListener("click", (event) => {
      if (event.target === emailDuplicateModal) closeEmailDuplicateModal();
      const closeButton = event.target instanceof Element
        ? event.target.closest("[data-customer-email-duplicate-close]")
        : null;
      if (closeButton) closeEmailDuplicateModal();
    });
  }

  if (emailDuplicateConfirm) {
    emailDuplicateConfirm.addEventListener("click", () => {
      if (!pendingDuplicateFormData) return;
      const confirmedData = new FormData();
      for (const [key, value] of pendingDuplicateFormData.entries()) {
        confirmedData.append(key, value);
      }
      confirmedData.set("allow_duplicate_email", "true");
      if (emailDuplicateModal) emailDuplicateModal.hidden = true;
      submitCreateForm(confirmedData);
    });
  }

  setupSearch(document.querySelector("[data-customer-search-first]"), {
    openCreateModal: true,
  });
  setupSearch(document.querySelector("[data-customer-direct-search]"), {
    openCreateModal: false,
  });
})();
