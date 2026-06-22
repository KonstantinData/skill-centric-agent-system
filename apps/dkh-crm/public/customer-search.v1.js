(() => {
  const root = document.querySelector("[data-customer-search-first]");
  let controller = null;
  let lastQuery = "";
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

  const setResults = (items) => {
    const results = root.querySelector("[data-customer-search-results]");
    const emptyState = root.querySelector("[data-customer-search-empty]");
    const hint = root.querySelector("[data-customer-search-hint]");
    const createPanel = document.querySelector("[data-customer-create-panel]");
    results.innerHTML = "";
    if (!items.length) {
      results.hidden = true;
      emptyState.hidden = false;
      if (createPanel) createPanel.hidden = false;
      hint.textContent = "Kein Treffer. Jetzt kann ein neuer Kunde angelegt werden.";
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
    emptyState.hidden = items.length > 0;
    if (createPanel) createPanel.hidden = true;
    hint.textContent = items.length > 0
      ? items.length + " Treffer gefunden."
      : "Kein Treffer. Jetzt kann ein neuer Kunde angelegt werden.";
  };

  if (!root) return;

  const input = root.querySelector("[data-customer-search-input]");
  const results = root.querySelector("[data-customer-search-results]");
  const emptyState = root.querySelector("[data-customer-search-empty]");
  const hint = root.querySelector("[data-customer-search-hint]");
  const createPanel = document.querySelector("[data-customer-create-panel]");

  const resetSearch = () => {
    results.hidden = true;
    results.innerHTML = "";
    emptyState.hidden = true;
    if (createPanel) createPanel.hidden = true;
    hint.textContent = "Geben Sie mindestens drei Zeichen ein.";
  };

  const runSearch = async () => {
    const query = input.value.trim();
    lastQuery = query;
    if (query.length < 3) {
      if (controller) controller.abort();
      resetSearch();
      return;
    }
    if (controller) controller.abort();
    controller = new AbortController();
    hint.textContent = "Suche läuft...";
    try {
      const response = await fetch("/api/kunden/search?q=" + encodeURIComponent(query), {
        headers: { accept: "application/json" },
        signal: controller.signal,
      });
      if (!response.ok) throw new Error("search_failed");
      const payload = await response.json();
      if (input.value.trim() !== lastQuery) return;
      const items = Array.isArray(payload.customers) ? payload.customers : [];
      setResults(items);
    } catch (error) {
      if (error.name === "AbortError") return;
      results.hidden = true;
      emptyState.hidden = true;
      if (createPanel) createPanel.hidden = true;
      hint.textContent = "Suche aktuell nicht verfügbar.";
    }
  };

  input.addEventListener("input", runSearch);
})();
