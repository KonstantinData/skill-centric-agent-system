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
    const createChoice = root.querySelector("[data-customer-create-choice]");
    results.innerHTML = "";
    if (!items.length) {
      results.hidden = true;
      if (createChoice) createChoice.hidden = !options.openCreateModal;
      hint.textContent = options.openCreateModal
        ? "Kein Treffer. Wählen Sie Leadanlage oder Kundenanlage."
        : "Kein Treffer.";
      if (options.openCreateModal && createModal) createModal.hidden = true;
      return;
    }
    if (createChoice) createChoice.hidden = true;
    const list = document.createElement("div");
    list.className = "suggest-list";
    for (const item of items) {
      const isLead = item.record_type === "lead";
      const row = document.createElement("article");
      row.className = "suggest-row";
      row.tabIndex = 0;
      row.title = isLead ? "Doppelklick öffnet die Leadakte" : "Doppelklick öffnet die Kundenakte";
      const href = isLead
        ? "/kunden/leads/" + encodeURIComponent(item.lead_id)
        : "/kunden/" + encodeURIComponent(item.customer_id);
      row.addEventListener("dblclick", () => {
        if (isLead) window.location.href = href;
        else openCustomerFile(href, item.customer_id);
      });
      row.addEventListener("keydown", (event) => {
        if (event.key !== "Enter") return;
        if (isLead) window.location.href = href;
        else openCustomerFile(href, item.customer_id);
      });

      const copy = document.createElement("div");
      copy.className = "suggest-copy";
      const title = document.createElement("strong");
      title.textContent = item.display_name || (isLead ? "Unbenannter Lead" : "Unbenannter Kunde");
      const meta = document.createElement("span");
      const type = isLead ? "Lead" : item.customer_type === "company" ? "Firma" : "Privat";
      const location = [item.postal_code, item.city].filter(Boolean).join(" ");
      const caseLabel = item.case_number ? "Vorgang " + item.case_number : null;
      const caratLabel = item.carat_order_number ? "CARAT " + item.carat_order_number : null;
      meta.textContent = [
        type,
        isLead ? item.source : null,
        caseLabel,
        caratLabel,
        location,
        item.primary_email || item.primary_phone,
      ].filter(Boolean).join(" · ");
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = isLead ? "Lead" : "Kunde";
      copy.append(title, meta, badge);

      const action = document.createElement("a");
      action.className = "btn btn-secondary";
      action.href = href;
      if (!isLead) {
        action.target = "_blank";
        action.rel = "noopener";
        action.setAttribute("data-customer-file-link", "");
        action.setAttribute("data-customer-id", String(item.customer_id));
      }
      action.textContent = isLead ? "Leadakte öffnen" : "Kundenakte öffnen";

      row.append(copy, action);
      list.append(row);
    }
    results.append(list);
    results.hidden = false;
    if (options.openCreateModal && createModal) createModal.hidden = true;
    hint.textContent = items.length + " Treffer gefunden.";
  };

  const createModal = document.querySelector("[data-customer-create-modal]");
  const leadCreateModal = document.querySelector("[data-lead-create-modal]");
  const leadCreateForm = document.querySelector("[data-lead-create-form]");
  const createCaseToggle = document.querySelector("[data-customer-create-case-toggle]");
  const caseDetails = document.querySelector("[data-customer-case-details]");
  const createForm = document.querySelector("[data-customer-create-form]");
  const customerTypeSelect = document.querySelector("[data-customer-type-select]");
  const customerMasterModal = document.querySelector("[data-customer-master-modal]");
  const customerMasterTypeSelect = document.querySelector("[data-customer-master-type-select]");
  const documentUploadModal = document.querySelector("[data-document-upload-modal]");
  const caseArchiveModals = document.querySelectorAll("[data-case-archive-modal]");
  const customerCustomVat = document.querySelector("[data-customer-custom-vat]");
  const customerCustomVatFlag = document.querySelector("[data-customer-custom-vat-flag]");
  const customerCustomVatRate = document.querySelector("[data-customer-custom-vat-rate]");
  const customerCustomVatLabel = document.querySelector("[data-customer-custom-vat-label]");
  const customerTaxTreatment = document.querySelector('select[name="tax_treatment"]');
  const customerMasterCustomVat = document.querySelector("[data-customer-master-custom-vat]");
  const customerMasterCustomVatFlag = document.querySelector("[data-customer-master-custom-vat-flag]");
  const customerMasterCustomVatRate = document.querySelector("[data-customer-master-custom-vat-rate]");
  const customerMasterCustomVatLabel = document.querySelector("[data-customer-master-custom-vat-label]");
  const customerMasterTaxTreatment = document.querySelector("[data-customer-master-tax-treatment]");
  const emailDuplicateModal = document.querySelector("[data-customer-email-duplicate-modal]");
  const emailDuplicateResults = document.querySelector("[data-customer-email-duplicate-results]");
  const emailDuplicateConfirm = document.querySelector("[data-customer-email-duplicate-confirm]");
  const projectObjectOther = document.querySelector("[data-project-object-other]");
  const projectObjectOtherNote = document.querySelector("[data-project-object-other-note]");
  const budgetRangeSelect = document.querySelector("[data-budget-range-select]");
  const budgetRangeOtherNote = document.querySelector("[data-budget-range-other-note]");
  const projectBasicsPanel = document.querySelector("[data-project-basics-panel]");
  const projectBasicsEdit = document.querySelector("[data-project-basics-edit]");
  const projectBasicsStatus = document.querySelector("[data-project-basics-status]");
  const projectBasicsLockedNote = document.querySelector("[data-project-basics-locked-note]");
  const projectBasicsSave = document.querySelector("[data-project-basics-save]");
  let pendingDuplicateFormData = null;

  const closeCreateModal = () => {
    pendingDuplicateFormData = null;
    if (emailDuplicateResults) emailDuplicateResults.innerHTML = "";
    if (emailDuplicateModal) emailDuplicateModal.hidden = true;
    if (createForm) createForm.reset();
    syncCustomerTypeSections();
    syncCaseDetails();
    if (createModal) createModal.hidden = true;
  };

  const closeLeadCreateModal = () => {
    if (leadCreateForm) leadCreateForm.reset();
    if (leadCreateModal) leadCreateModal.hidden = true;
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

  const syncProjectObjectOtherNote = () => {
    if (!projectObjectOther || !projectObjectOtherNote) return;
    projectObjectOtherNote.hidden = !projectObjectOther.checked;
  };

  const syncBudgetRangeOtherNote = () => {
    if (!budgetRangeSelect || !budgetRangeOtherNote) return;
    budgetRangeOtherNote.hidden = budgetRangeSelect.value !== "other";
  };

  const setProjectBasicsEditing = (editing) => {
    if (!projectBasicsPanel) return;
    projectBasicsPanel.setAttribute(
      "data-project-basics-state",
      editing ? "editing" : "locked",
    );
    projectBasicsPanel.style.boxShadow = editing ? "0 0 0 2px var(--accent)" : "";
    for (const fieldset of projectBasicsPanel.querySelectorAll("[data-project-basics-fields]")) {
      fieldset.disabled = !editing;
    }
    if (projectBasicsSave) projectBasicsSave.disabled = !editing;
    if (projectBasicsEdit) projectBasicsEdit.hidden = editing;
    if (projectBasicsStatus) {
      projectBasicsStatus.textContent = editing ? "Bearbeitung aktiv" : "Gesperrt";
      projectBasicsStatus.style.borderColor = editing ? "var(--accent)" : "";
      projectBasicsStatus.style.color = editing ? "var(--accent-strong)" : "";
    }
    if (projectBasicsLockedNote) {
      projectBasicsLockedNote.hidden = editing;
    }
  };

  const activeCustomerCountrySelect = () => {
    const selectedType = customerTypeSelect ? customerTypeSelect.value || "private" : "private";
    return document.querySelector(
      `[data-customer-type-section="${selectedType}"] [data-customer-country-select]`,
    );
  };

  const syncCustomVat = () => {
    if (!customerCustomVat || !customerCustomVatFlag || !customerCustomVatRate) return;
    const countrySelect = activeCustomerCountrySelect();
    const country = countrySelect ? countrySelect.value : "DE";
    const treatment = customerTaxTreatment ? customerTaxTreatment.value : "standard_de";
    const enabled = country === "CH" || treatment === "custom" || treatment === "switzerland_export";
    customerCustomVat.hidden = !enabled;
    customerCustomVatFlag.value = enabled ? "true" : "false";
    customerCustomVatRate.disabled = !enabled;
    if (customerCustomVatLabel) customerCustomVatLabel.disabled = !enabled;
    if (!enabled) {
      customerCustomVatRate.value = "";
      if (customerCustomVatLabel) customerCustomVatLabel.value = "";
      return;
    }
    if (country === "CH" && !customerCustomVatRate.value) {
      customerCustomVatRate.value = "8.10";
      if (customerCustomVatLabel && !customerCustomVatLabel.value) {
        customerCustomVatLabel.value = "Schweiz Normalsatz";
      }
    }
  };

  const activeCustomerMasterCountrySelect = () => {
    const selectedType = customerMasterTypeSelect ? customerMasterTypeSelect.value || "private" : "private";
    return document.querySelector(
      `[data-customer-master-type-section="${selectedType}"] [data-customer-master-country-select]`,
    );
  };

  const syncCustomerMasterCustomVat = () => {
    if (!customerMasterCustomVat || !customerMasterCustomVatFlag || !customerMasterCustomVatRate) return;
    const countrySelect = activeCustomerMasterCountrySelect();
    const country = countrySelect ? countrySelect.value : "DE";
    const treatment = customerMasterTaxTreatment ? customerMasterTaxTreatment.value : "standard_de";
    const hasStoredCustomVat = customerMasterCustomVatFlag.value === "true" && !!customerMasterCustomVatRate.value;
    const enabled = country === "CH" || treatment === "custom" || treatment === "switzerland_export" || hasStoredCustomVat;
    customerMasterCustomVat.hidden = !enabled;
    customerMasterCustomVatFlag.value = enabled ? "true" : "false";
    customerMasterCustomVatRate.disabled = !enabled;
    if (customerMasterCustomVatLabel) customerMasterCustomVatLabel.disabled = !enabled;
    if (!enabled) {
      customerMasterCustomVatRate.value = "";
      if (customerMasterCustomVatLabel) customerMasterCustomVatLabel.value = "";
      return;
    }
    if (country === "CH" && !customerMasterCustomVatRate.value) {
      customerMasterCustomVatRate.value = "8.10";
      if (customerMasterCustomVatLabel && !customerMasterCustomVatLabel.value) {
        customerMasterCustomVatLabel.value = "Schweiz Normalsatz";
      }
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
    syncCustomVat();
  };

  const closeCustomerMasterModal = () => {
    if (customerMasterModal) customerMasterModal.hidden = true;
  };

  const openDocumentUploadModal = () => {
    if (!documentUploadModal) return;
    documentUploadModal.hidden = false;
    const firstField = documentUploadModal.querySelector("input, select, textarea, button");
    if (firstField instanceof HTMLElement) firstField.focus();
  };

  const closeDocumentUploadModal = () => {
    if (documentUploadModal) documentUploadModal.hidden = true;
  };

  const openCaseArchiveModal = (target) => {
    const modal = Array.from(caseArchiveModals).find(
      (candidate) => candidate.getAttribute("data-case-archive-modal") === target,
    );
    if (!modal) return;
    modal.hidden = false;
    const firstField = modal.querySelector("textarea, button");
    if (firstField instanceof HTMLElement) firstField.focus();
  };

  const closeCaseArchiveModals = () => {
    for (const modal of caseArchiveModals) {
      modal.hidden = true;
    }
  };

  const syncCustomerMasterTypeSections = () => {
    if (!customerMasterTypeSelect) return;
    const selectedType = customerMasterTypeSelect.value || "private";
    for (const section of document.querySelectorAll("[data-customer-master-type-section]")) {
      const enabled = section.getAttribute("data-customer-master-type-section") === selectedType;
      section.hidden = !enabled;
      for (const field of section.querySelectorAll("input, select, textarea")) {
        if (!field.name) continue;
        field.disabled = !enabled;
      }
    }
    syncCustomerMasterCustomVat();
  };

  const resetSearch = (root, options) => {
    const results = root.querySelector("[data-customer-search-results]");
    const hint = root.querySelector("[data-customer-search-hint]");
    results.hidden = true;
    results.innerHTML = "";
    const createChoice = root.querySelector("[data-customer-create-choice]");
    if (createChoice) createChoice.hidden = true;
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
      const customerItems = Array.isArray(payload.customers)
        ? payload.customers.map((customer) => ({ ...customer, record_type: "customer" }))
        : [];
      const leadItems = Array.isArray(payload.leads) ? payload.leads : [];
      const items = [...customerItems, ...leadItems];
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

  if (leadCreateModal) {
    leadCreateModal.addEventListener("click", (event) => {
      if (event.target === leadCreateModal) closeLeadCreateModal();
      const closeButton = event.target instanceof Element
        ? event.target.closest("[data-lead-create-close]")
        : null;
      if (closeButton) closeLeadCreateModal();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeLeadCreateModal();
    });
  }

  document.addEventListener("click", (event) => {
    const leadOpen = event.target instanceof Element
      ? event.target.closest("[data-lead-create-open]")
      : null;
    if (leadOpen && leadCreateModal) {
      leadCreateModal.hidden = false;
      const firstField = leadCreateModal.querySelector("input, select, textarea, button");
      if (firstField instanceof HTMLElement) firstField.focus();
      return;
    }
    const customerOpen = event.target instanceof Element
      ? event.target.closest("[data-customer-create-open]")
      : null;
    if (customerOpen && createModal) {
      createModal.hidden = false;
      const firstField = createModal.querySelector("input, select, textarea, button");
      if (firstField instanceof HTMLElement) firstField.focus();
    }
  });

  if (customerMasterModal) {
    document.addEventListener("click", (event) => {
      const openButton = event.target instanceof Element
        ? event.target.closest("[data-customer-master-open]")
        : null;
      if (openButton) {
        customerMasterModal.hidden = false;
        syncCustomerMasterTypeSections();
        return;
      }
      if (event.target === customerMasterModal) closeCustomerMasterModal();
      const closeButton = event.target instanceof Element
        ? event.target.closest("[data-customer-master-close]")
        : null;
      if (closeButton) closeCustomerMasterModal();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeCustomerMasterModal();
    });
  }

  if (documentUploadModal) {
    document.addEventListener("click", (event) => {
      const openButton = event.target instanceof Element
        ? event.target.closest("[data-document-upload-open]")
        : null;
      if (openButton) {
        openDocumentUploadModal();
        return;
      }
      const closeButton = event.target instanceof Element
        ? event.target.closest("[data-document-upload-close], [data-document-upload-backdrop]")
        : null;
      if (closeButton) closeDocumentUploadModal();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeDocumentUploadModal();
    });
  }

  if (caseArchiveModals.length > 0) {
    document.addEventListener("click", (event) => {
      const openButton = event.target instanceof Element
        ? event.target.closest("[data-case-archive-open]")
        : null;
      if (openButton) {
        const target = openButton.getAttribute("data-case-archive-target");
        if (target) openCaseArchiveModal(target);
        return;
      }
      const closeButton = event.target instanceof Element
        ? event.target.closest("[data-case-archive-close]")
        : null;
      if (closeButton) closeCaseArchiveModals();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeCaseArchiveModals();
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

  for (const countrySelect of document.querySelectorAll("[data-customer-country-select]")) {
    countrySelect.addEventListener("change", syncCustomVat);
  }

  if (customerTaxTreatment) {
    customerTaxTreatment.addEventListener("change", syncCustomVat);
  }

  if (customerMasterTypeSelect) {
    customerMasterTypeSelect.addEventListener("change", syncCustomerMasterTypeSections);
    syncCustomerMasterTypeSections();
  }

  for (const countrySelect of document.querySelectorAll("[data-customer-master-country-select]")) {
    countrySelect.addEventListener("change", syncCustomerMasterCustomVat);
  }

  if (customerMasterTaxTreatment) {
    customerMasterTaxTreatment.addEventListener("change", syncCustomerMasterCustomVat);
  }

  if (projectObjectOther) {
    projectObjectOther.addEventListener("change", syncProjectObjectOtherNote);
    syncProjectObjectOtherNote();
  }

  if (budgetRangeSelect) {
    budgetRangeSelect.addEventListener("change", syncBudgetRangeOtherNote);
    syncBudgetRangeOtherNote();
  }

  if (projectBasicsPanel) {
    setProjectBasicsEditing(false);
    if (projectBasicsEdit) {
      projectBasicsEdit.addEventListener("click", () => {
        setProjectBasicsEditing(true);
        const firstField = projectBasicsPanel.querySelector("input, select, textarea");
        if (firstField instanceof HTMLElement) firstField.focus();
      });
    }
  }

  if (createForm) {
    createForm.addEventListener("submit", (event) => {
      event.preventDefault();
      submitCreateForm(new FormData(createForm));
    });
  }

  if (leadCreateForm) {
    leadCreateForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const response = await fetch(leadCreateForm.action, {
        method: "POST",
        headers: { accept: "application/json" },
        body: new FormData(leadCreateForm),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        alert("Lead konnte nicht gespeichert werden.");
        return;
      }
      window.location.href = payload.lead_id
        ? "/kunden/leads/" + encodeURIComponent(payload.lead_id)
        : "/kunden";
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
  syncCustomVat();
  syncCustomerMasterCustomVat();
})();
