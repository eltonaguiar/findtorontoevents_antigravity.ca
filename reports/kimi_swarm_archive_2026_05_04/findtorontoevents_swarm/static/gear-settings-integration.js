/**
 * gear-settings-integration.js
 *
 * Vanilla JS module for integrating the Gear Settings modal into the
 * hand-coded HTML page at findtorontoevents.ca.
 *
 * Features:
 *   - Detects existing gear icon and attaches click handler
 *   - Renders a full modal UI matching GearSettingsModal.tsx design
 *   - Reads/writes settings to localStorage key "fte_gear_settings"
 *   - Syncs to /api/user-settings.php when user is logged in
 *   - Applies maxEventsPerDayPerSource + Eventbrite exemption to events
 *   - Focus trap, ESC to close, aria attributes
 *   - Mobile-responsive (full-screen sheet on <640px)
 */

(function (global) {
  "use strict";

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  Config                                                                    */
  /* ─────────────────────────────────────────────────────────────────────────── */

  const LOCAL_STORAGE_KEY = "fte_gear_settings";
  const API_BASE = "/api";
  const DEBOUNCE_MS = 400;
  const THROTTLE_MS = 200;

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  Default settings (mirrors GearSettingsModal.tsx defaults)                 */
  /* ─────────────────────────────────────────────────────────────────────────── */

  const DEFAULT_SOURCES = [
    { id: "eventbrite", name: "Eventbrite", type: "api", eventCount: 1240, enabled: true, exemptFromLimit: true },
    { id: "ticketmaster", name: "Ticketmaster", type: "api", eventCount: 310, enabled: true, exemptFromLimit: false },
    { id: "bandsintown", name: "Bandsintown", type: "api", eventCount: 185, enabled: true, exemptFromLimit: false },
    { id: "meetup", name: "Meetup", type: "api", eventCount: 92, enabled: true, exemptFromLimit: false },
    { id: "toronto_opendata", name: "Toronto Open Data", type: "api", eventCount: 64, enabled: true, exemptFromLimit: false },
    { id: "ago", name: "Art Gallery of Ontario", type: "api", eventCount: 28, enabled: true, exemptFromLimit: false },
    { id: "rom", name: "Royal Ontario Museum", type: "api", eventCount: 22, enabled: true, exemptFromLimit: false },
    { id: "harbourfront", name: "Harbourfront Centre", type: "rss", eventCount: 18, enabled: true, exemptFromLimit: false },
    { id: "tiff", name: "TIFF", type: "api", eventCount: 15, enabled: true, exemptFromLimit: false },
    { id: "sportsnet", name: "Sports Leagues", type: "scrape", eventCount: 45, enabled: true, exemptFromLimit: false },
    { id: "blogto", name: "BlogTO", type: "rss", eventCount: 56, enabled: true, exemptFromLimit: false },
    { id: "facebook", name: "Facebook Events", type: "api", eventCount: 0, enabled: false, exemptFromLimit: false },
  ];

  const DEFAULT_SETTINGS = {
    maxEventsPerDayPerSource: 3,
    exemptEventbrite: true,
    showSourceBadges: true,
    groupByDate: false,
    deduplicate: true,
    sources: DEFAULT_SOURCES,
    enabledSources: DEFAULT_SOURCES.filter((s) => s.enabled).map((s) => s.id),
    calendarExportFormat: "both",
  };

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  Utilities                                                                 */
  /* ─────────────────────────────────────────────────────────────────────────── */

  function debounce(fn, wait) {
    let t;
    return function (...args) {
      clearTimeout(t);
      t = setTimeout(() => fn.apply(this, args), wait);
    };
  }

  function throttle(fn, wait) {
    let last = 0;
    return function (...args) {
      const now = Date.now();
      if (now - last >= wait) {
        last = now;
        fn.apply(this, args);
      }
    };
  }

  function deepMerge(target, source) {
    const out = { ...target };
    for (const key in source) {
      if (source[key] !== null && typeof source[key] === "object" && !Array.isArray(source[key])) {
        out[key] = deepMerge(out[key] || {}, source[key]);
      } else {
        out[key] = source[key];
      }
    }
    return out;
  }

  function classNames(...classes) {
    return classes.filter(Boolean).join(" ");
  }

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  State                                                                     */
  /* ─────────────────────────────────────────────────────────────────────────── */

  let settings = loadSettingsFromLocalStorage();
  let isLoggedIn = false;
  let sessionChecked = false;
  let modalOpen = false;
  let modalEl = null;
  let lastFocusedEl = null;
  let saveTimeout = null;
  let currentTab = "display";

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  Persistence                                                               */
  /* ─────────────────────────────────────────────────────────────────────────── */

  function loadSettingsFromLocalStorage() {
    try {
      const raw = localStorage.getItem(LOCAL_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw);
        return deepMerge(DEFAULT_SETTINGS, parsed);
      }
    } catch (e) {
      console.warn("[GearSettings] Failed to parse localStorage:", e);
    }
    return { ...DEFAULT_SETTINGS };
  }

  function saveToLocalStorage() {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(settings));
    } catch (e) {
      console.warn("[GearSettings] localStorage write failed:", e);
    }
  }

  async function checkSession() {
    try {
      const res = await fetch(`${API_BASE}/check-session.php`, {
        method: "GET",
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (!res.ok) return false;
      const data = await res.json();
      isLoggedIn = !!data.loggedIn;
      sessionChecked = true;
      return isLoggedIn;
    } catch (e) {
      console.warn("[GearSettings] Session check failed:", e);
      return false;
    }
  }

  async function fetchSettingsFromBackend() {
    if (!isLoggedIn) return null;
    try {
      const res = await fetch(`${API_BASE}/user-settings.php`, {
        method: "GET",
        credentials: "include",
        headers: { Accept: "application/json" },
      });
      if (res.status === 401) {
        isLoggedIn = false;
        return null;
      }
      if (!res.ok) return null;
      const data = await res.json();
      if (data.success && data.data && data.data.settings) {
        return data.data.settings;
      }
    } catch (e) {
      console.warn("[GearSettings] Backend fetch failed:", e);
    }
    return null;
  }

  async function saveSettingsToBackend() {
    if (!isLoggedIn) return;
    try {
      const payload = {
        maxEventsPerDayPerSource: settings.maxEventsPerDayPerSource,
        exemptEventbrite: settings.exemptEventbrite,
        showSourceBadges: settings.showSourceBadges,
        groupByDate: settings.groupByDate,
        deduplicate: settings.deduplicate,
        enabledSources: settings.enabledSources || settings.sources.filter((s) => s.enabled).map((s) => s.id),
        calendarExportFormat: settings.calendarExportFormat,
      };

      const res = await fetch(`${API_BASE}/user-settings.php`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok && res.status !== 401) {
        console.warn("[GearSettings] Backend save failed:", res.status);
      }
    } catch (e) {
      console.warn("[GearSettings] Backend save error:", e);
    }
  }

  const debouncedBackendSave = debounce(saveSettingsToBackend, DEBOUNCE_MS);

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  Event Filtering                                                           */
  /* ─────────────────────────────────────────────────────────────────────────── */

  /**
   * Applies maxEventsPerDayPerSource filter to a list of events.
   * If exemptEventbrite is true, events with source === 'eventbrite'
   * are not counted toward the daily limit.
   *
   * @param {Array} events — each event should have { date, source }
   * @returns {Array} filtered events
   */
  function applyMaxEventsFilter(events) {
    if (!Array.isArray(events)) return events;
    const limit = settings.maxEventsPerDayPerSource;
    const exemptEventbrite = settings.exemptEventbrite;

    const counts = {};
    const enabledSet = new Set(
      settings.enabledSources || settings.sources.filter((s) => s.enabled).map((s) => s.id)
    );

    return events.filter((evt) => {
      const source = evt.source || evt.sourceId || "unknown";
      const date = evt.date || evt.startDate || evt.eventDate || "unknown";
      const key = `${date}__${source}`;

      // Skip disabled sources entirely
      if (!enabledSet.has(source)) return false;

      // Eventbrite exemption
      if (exemptEventbrite && source === "eventbrite") return true;

      counts[key] = (counts[key] || 0) + 1;
      return counts[key] <= limit;
    });
  }

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  DOM: Modal Construction                                                   */
  /* ─────────────────────────────────────────────────────────────────────────── */

  function createElement(tag, attrs = {}, children = []) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === "className") {
        el.className = v;
      } else if (k.startsWith("on") && typeof v === "function") {
        el.addEventListener(k.slice(2).toLowerCase(), v);
      } else if (k === "style" && typeof v === "object") {
        Object.assign(el.style, v);
      } else {
        el.setAttribute(k, v);
      }
    }
    children.forEach((c) => {
      if (typeof c === "string") el.appendChild(document.createTextNode(c));
      else if (c) el.appendChild(c);
    });
    return el;
  }

  function buildIcon(name, size = 16) {
    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("width", size);
    svg.setAttribute("height", size);
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "2");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");

    const paths = {
      settings: `<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.47a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>`,
      x: `<path d="M18 6 6 18"/><path d="m6 6 12 12"/>`,
      filter: `<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>`,
      database: `<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>`,
      calendar: `<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>`,
      layers: `<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>`,
      info: `<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>`,
      check: `<path d="M20 6 9 17l-5-5"/>`,
      eyeOff: `<path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/>`,
      share2: `<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/>`,
      bell: `<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>`,
      shieldCheck: `<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/>`,
      rss: `<path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/>`,
      globe: `<circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>`,
    };

    if (paths[name]) {
      svg.innerHTML = paths[name];
    }
    return svg;
  }

  function buildModal() {
    const isMobile = window.innerWidth < 640;

    /* ── Backdrop ── */
    const backdrop = createElement("div", {
      className: "fte-modal-backdrop",
      role: "dialog",
      "aria-modal": "true",
      "aria-labelledby": "fte-modal-title",
      onclick: (e) => {
        if (e.target === backdrop) closeModal();
      },
    });

    /* ── Modal Sheet ── */
    const sheet = createElement("div", {
      className: classNames(
        "fte-modal-sheet",
        isMobile ? "fte-modal-sheet--mobile" : "fte-modal-sheet--desktop"
      ),
    });

    /* ── Header ── */
    const header = createElement("div", { className: "fte-modal-header" }, [
      createElement("div", { className: "fte-modal-header-left" }, [
        createElement("div", { className: "fte-modal-icon-wrap" }, [buildIcon("settings", 20)]),
        createElement("div", {}, [
          createElement("h2", { id: "fte-modal-title", className: "fte-modal-title" }, ["Event Settings"]),
          createElement("p", { className: "fte-modal-subtitle" }, [
            isLoggedIn ? "Settings saved to your account" : "Settings saved locally on this device",
          ]),
        ]),
      ]),
      createElement("button", {
        className: "fte-modal-close-btn",
        "aria-label": "Close settings",
        onclick: closeModal,
      }, [buildIcon("x", 20)]),
    ]);

    /* ── Tabs ── */
    const tabDefs = [
      { key: "display", icon: "filter", label: "Display" },
      { key: "sources", icon: "database", label: "Sources" },
      { key: "export", icon: "calendar", label: "Export" },
      { key: "advanced", icon: "layers", label: "Advanced" },
    ];

    const tabsEl = createElement("div", { className: "fte-modal-tabs" });
    const tabButtons = {};

    tabDefs.forEach((tab) => {
      const btn = createElement("button", {
        className: classNames(
          "fte-modal-tab",
          currentTab === tab.key && "fte-modal-tab--active"
        ),
        role: "tab",
        "aria-selected": currentTab === tab.key ? "true" : "false",
        onclick: () => switchTab(tab.key),
      }, [
        buildIcon(tab.icon, 14),
        document.createTextNode(tab.label),
      ]);
      tabButtons[tab.key] = btn;
      tabsEl.appendChild(btn);
    });

    /* ── Content area ── */
    const contentEl = createElement("div", { className: "fte-modal-content" });
    const bodyEl = createElement("div", { className: "fte-modal-body" });
    contentEl.appendChild(bodyEl);

    /* ── Footer ── */
    const savedIndicator = createElement("span", { className: "fte-modal-saved-indicator fte-hidden" }, [
      buildIcon("check", 14),
      document.createTextNode(" Saved"),
    ]);

    const footer = createElement("div", { className: "fte-modal-footer" }, [
      savedIndicator,
      createElement("div", { className: "fte-modal-footer-btns" }, [
        createElement("button", {
          className: "fte-btn fte-btn--secondary",
          onclick: () => {
            saveToLocalStorage();
            if (isLoggedIn) saveSettingsToBackend();
            flashSaved(savedIndicator);
          },
        }, ["Save Now"]),
        createElement("button", {
          className: "fte-btn fte-btn--primary",
          onclick: closeModal,
        }, ["Done"]),
      ]),
    ]);

    /* ── Assemble ── */
    sheet.appendChild(header);
    sheet.appendChild(tabsEl);
    sheet.appendChild(contentEl);
    sheet.appendChild(footer);
    backdrop.appendChild(sheet);

    /* ── Render current tab ── */
    function switchTab(key) {
      currentTab = key;
      for (const [k, btn] of Object.entries(tabButtons)) {
        const active = k === key;
        btn.classList.toggle("fte-modal-tab--active", active);
        btn.setAttribute("aria-selected", active ? "true" : "false");
      }
      renderTabBody(bodyEl);
    }

    function renderTabBody(container) {
      container.innerHTML = "";
      if (currentTab === "display") {
        buildDisplayTab(container);
      } else if (currentTab === "sources") {
        buildSourcesTab(container);
      } else if (currentTab === "export") {
        buildExportTab(container);
      } else if (currentTab === "advanced") {
        buildAdvancedTab(container);
      }
    }

    switchTab(currentTab);

    /* ── Focus trap ── */
    sheet.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        closeModal();
        return;
      }
      if (e.key !== "Tab") return;
      const focusable = Array.from(
        sheet.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
      ).filter((el) => !el.disabled && el.offsetParent !== null);
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    });

    return backdrop;
  }

  /* ── Tab: Display ── */
  function buildDisplayTab(container) {
    const sectionHeader = (iconName, label) =>
      createElement("div", { className: "fte-section-header" }, [
        buildIcon(iconName, 16),
        document.createTextNode(label),
      ]);

    container.appendChild(sectionHeader("filter", "Display Preferences"));

    /* Slider card */
    const sliderValue = createElement("span", { className: "fte-slider-value" }, [
      String(settings.maxEventsPerDayPerSource),
    ]);

    const slider = createElement("input", {
      type: "range",
      min: 1,
      max: 10,
      step: 1,
      value: settings.maxEventsPerDayPerSource,
      className: "fte-slider",
      "aria-label": "Maximum events per day per source",
      oninput: (e) => {
        const val = parseInt(e.target.value, 10);
        settings.maxEventsPerDayPerSource = val;
        sliderValue.textContent = String(val);
        autoSave();
      },
    });

    const sliderCard = createElement("div", { className: "fte-card" }, [
      createElement("div", { className: "fte-slider-header" }, [
        createElement("label", { htmlFor: undefined, className: "fte-label" }, ["Max events per day per source"]),
        sliderValue,
      ]),
      slider,
      createElement("div", { className: "fte-slider-ticks" }, ["1", "5", "10"]),
      createElement("p", { className: "fte-help-text" }, [
        "Limits how many events from a single source appear on any given day. Set to 10 to show all.",
      ]),
    ]);
    container.appendChild(sliderCard);

    /* Toggles */
    container.appendChild(buildToggle("Exempt Eventbrite from limit", settings.exemptEventbrite, (v) => {
      settings.exemptEventbrite = v;
      autoSave();
    }, "Eventbrite is a major source with high-quality listings. Keep unlimited."));

    container.appendChild(buildToggle("Show source badges on event cards", settings.showSourceBadges, (v) => {
      settings.showSourceBadges = v;
      autoSave();
    }, "Display a small icon indicating which source each event came from."));

    container.appendChild(buildToggle("Group events by date", settings.groupByDate, (v) => {
      settings.groupByDate = v;
      autoSave();
    }, "Organize events into date sections (Today, Tomorrow, etc.) instead of a flat grid."));
  }

  /* ── Tab: Sources ── */
  function buildSourcesTab(container) {
    const sectionHeader = createElement("div", { className: "fte-section-header" }, [
      buildIcon("database", 16),
      document.createTextNode("Data Sources"),
    ]);
    container.appendChild(sectionHeader);

    const enabledCount = settings.sources.filter((s) => s.enabled).length;
    const totalEvents = settings.sources.filter((s) => s.enabled).reduce((sum, s) => sum + s.eventCount, 0);

    container.appendChild(
      createElement("div", { className: "fte-sources-meta" }, [
        createElement("span", {}, [`${enabledCount} of ${settings.sources.length} active`]),
        createElement("span", {}, [
          createElement("strong", {}, [totalEvents.toLocaleString()]),
          " events enabled",
        ]),
      ])
    );

    const list = createElement("div", { className: "fte-sources-list" });

    settings.sources.forEach((source) => {
      const isEnabled = source.enabled;
      const row = createElement("div", {
        className: classNames(
          "fte-source-row",
          !isEnabled && "fte-source-row--disabled"
        ),
      });

      const toggleBtn = createElement("button", {
        className: classNames(
          "fte-source-toggle",
          isEnabled ? "fte-source-toggle--on" : "fte-source-toggle--off"
        ),
        "aria-label": `${isEnabled ? "Disable" : "Enable"} ${source.name}`,
        onclick: () => {
          source.enabled = !source.enabled;
          settings.enabledSources = settings.sources.filter((s) => s.enabled).map((s) => s.id);
          autoSave();
          renderTabBody(container.parentElement.querySelector(".fte-modal-body"));
        },
      }, [buildIcon(isEnabled ? "check" : "eyeOff", 14)]);

      const badgeType = source.type === "api" ? "Official API" : source.type === "rss" ? "RSS Feed" : "Scraped";
      const badgeColor =
        source.type === "api"
          ? "fte-badge--api"
          : source.type === "rss"
          ? "fte-badge--rss"
          : "fte-badge--scrape";

      const badge = createElement("span", { className: classNames("fte-badge", badgeColor) }, [
        document.createTextNode(badgeType),
      ]);

      const infoCol = createElement("div", { className: "fte-source-info" }, [
        createElement("div", { className: "fte-source-name-line" }, [
          createElement("span", { className: "fte-source-name" }, [source.name]),
          badge,
        ]),
        createElement("div", { className: "fte-source-meta-line" }, [
          createElement("span", {}, [source.eventCount > 0 ? `${source.eventCount.toLocaleString()} events` : "Not yet synced"]),
          source.exemptFromLimit &&
            createElement("span", { className: "fte-exempt-tag" }, ["Exempt from limit"]),
        ]),
      ]);

      row.appendChild(toggleBtn);
      row.appendChild(infoCol);
      list.appendChild(row);
    });

    container.appendChild(list);

    container.appendChild(
      createElement("div", { className: "fte-tip-card" }, [
        createElement("p", {}, [
          createElement("strong", {}, ["Pro tip:"]),
          " Disabling sources reduces duplicates but may hide unique niche events. We recommend keeping all API sources enabled.",
        ]),
      ])
    );
  }

  /* ── Tab: Export ── */
  function buildExportTab(container) {
    container.appendChild(
      createElement("div", { className: "fte-section-header" }, [
        buildIcon("calendar", 16),
        document.createTextNode("Calendar Export"),
      ])
    );

    const formats = ["ical", "google", "both"];
    const formatLabels = { ical: "iCal (.ics)", google: "Google Calendar", both: "Both" };

    const formatButtons = createElement("div", { className: "fte-format-btns" });
    formats.forEach((fmt) => {
      const btn = createElement("button", {
        className: classNames(
          "fte-format-btn",
          settings.calendarExportFormat === fmt && "fte-format-btn--active"
        ),
        onclick: () => {
          settings.calendarExportFormat = fmt;
          autoSave();
          renderTabBody(container.parentElement.querySelector(".fte-modal-body"));
        },
      }, [formatLabels[fmt]]);
      formatButtons.appendChild(btn);
    });

    container.appendChild(
      createElement("div", { className: "fte-card" }, [
        createElement("p", { className: "fte-card-text" }, [
          "Export the currently filtered events to your preferred calendar app. Updates hourly.",
        ]),
        formatButtons,
        createElement("button", {
          className: "fte-btn fte-btn--primary fte-btn--full",
          onclick: () => {
            const url = `/api/export/calendar?format=${settings.calendarExportFormat}&filters=active`;
            window.open(url, "_blank");
          },
        }, [buildIcon("share2", 16), document.createTextNode(" Export My Filtered View")]),
        createElement("p", { className: "fte-help-text fte-text-center" }, [
          "Generates a downloadable .ics file and/or Google Calendar subscription URL.",
        ]),
      ])
    );

    container.appendChild(
      createElement("div", { className: "fte-section-header" }, [
        buildIcon("bell", 16),
        document.createTextNode("Notification Preferences"),
      ])
    );

    container.appendChild(
      createElement("div", { className: "fte-card fte-card--muted" }, [
        createElement("p", {}, [
          createElement("strong", {}, ["Coming soon:"]),
          " Get notified when new events match your saved filters. Requires sign-in.",
        ]),
      ])
    );
  }

  /* ── Tab: Advanced ── */
  function buildAdvancedTab(container) {
    container.appendChild(
      createElement("div", { className: "fte-section-header" }, [
        buildIcon("layers", 16),
        document.createTextNode("Smart Deduplication"),
      ])
    );

    container.appendChild(
      buildToggle("Hide likely duplicates across sources", settings.deduplicate, (v) => {
        settings.deduplicate = v;
        autoSave();
      }, "When the same event is found on multiple platforms, only show the best-quality listing.")
    );

    if (settings.deduplicate) {
      container.appendChild(
        createElement("div", { className: "fte-dedup-active" }, [
          createElement("div", { className: "fte-dedup-active-inner" }, [
            buildIcon("shieldCheck", 16),
            createElement("div", {}, [
              createElement("p", { className: "fte-dedup-title" }, ["Deduplication active"]),
              createElement("p", { className: "fte-dedup-desc" }, [
                "We compare title (80% match), venue name, and date within a 2-hour window. The listing with the most metadata wins.",
              ]),
            ]),
          ]),
        ])
      );
    }
  }

  /* ── Toggle component ── */
  function buildToggle(label, checked, onChange, description) {
    const row = createElement("div", { className: "fte-toggle-row" }, [
      createElement("div", { className: "fte-toggle-label-col" }, [
        createElement("div", { className: "fte-toggle-label" }, [label]),
        description && createElement("p", { className: "fte-toggle-desc" }, [description]),
      ]),
      createElement("button", {
        className: classNames("fte-toggle-switch", checked && "fte-toggle-switch--on"),
        role: "switch",
        "aria-checked": checked ? "true" : "false",
        onclick: () => {
          const newVal = !checked;
          onChange(newVal);
          renderTabBody(document.querySelector(".fte-modal-body"));
        },
      }, [
        createElement("span", {
          className: classNames("fte-toggle-knob", checked && "fte-toggle-knob--on"),
        }),
      ]),
    ]);
    return row;
  }

  function flashSaved(el) {
    el.classList.remove("fte-hidden");
    setTimeout(() => el.classList.add("fte-hidden"), 2000);
  }

  function autoSave() {
    saveToLocalStorage();
    if (isLoggedIn) debouncedBackendSave();
    // Also apply filters immediately if events are available
    applySettingsToPage();
  }

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  Modal open / close                                                        */
  /* ─────────────────────────────────────────────────────────────────────────── */

  function openModal() {
    if (modalOpen) return;
    modalOpen = true;
    lastFocusedEl = document.activeElement;

    modalEl = buildModal();
    document.body.appendChild(modalEl);
    document.body.style.overflow = "hidden";

    // Focus the close button after a tick
    requestAnimationFrame(() => {
      const closeBtn = modalEl.querySelector(".fte-modal-close-btn");
      closeBtn?.focus();
    });
  }

  function closeModal() {
    if (!modalOpen || !modalEl) return;
    modalOpen = false;
    modalEl.remove();
    modalEl = null;
    document.body.style.overflow = "";
    lastFocusedEl?.focus();
  }

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  Event filtering applied to page                                             */
  /* ─────────────────────────────────────────────────────────────────────────── */

  function applySettingsToPage() {
    // If the page exposes raw events, filter them before applyThumbnails() runs
    if (global.__RAW_EVENTS__ && Array.isArray(global.__RAW_EVENTS__)) {
      const filtered = applyMaxEventsFilter(global.__RAW_EVENTS__);
      global.__FILTERED_EVENTS__ = filtered;

      // If the page already rendered, re-render
      if (typeof global.applyThumbnails === "function") {
        try {
          global.applyThumbnails(filtered);
        } catch (e) {
          console.warn("[GearSettings] applyThumbnails re-render failed:", e);
        }
      }
    }

    // Toggle source badges visibility
    const badges = document.querySelectorAll(".fte-source-badge");
    badges.forEach((b) => {
      b.style.display = settings.showSourceBadges ? "" : "none";
    });
  }

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  Initialization                                                            */
  /* ─────────────────────────────────────────────────────────────────────────── */

  async function init() {
    // 1. Load from localStorage (already done at module load)
    // 2. Check session, then fetch backend settings if logged in
    const loggedIn = await checkSession();
    if (loggedIn) {
      const backendSettings = await fetchSettingsFromBackend();
      if (backendSettings) {
        // Backend wins: merge with defaults, override localStorage
        settings = deepMerge(DEFAULT_SETTINGS, backendSettings);
        // Ensure sources array stays intact even if backend only sends enabledSources
        if (backendSettings.enabledSources && Array.isArray(backendSettings.enabledSources)) {
          const enabledSet = new Set(backendSettings.enabledSources);
          settings.sources = settings.sources.map((s) => ({
            ...s,
            enabled: enabledSet.has(s.id),
          }));
        }
        saveToLocalStorage();
      }
    }

    // 3. If the page already has __RAW_EVENTS__, filter immediately
    if (global.__RAW_EVENTS__) {
      global.__FILTERED_EVENTS__ = applyMaxEventsFilter(global.__RAW_EVENTS__);
    }

    // 4. Hook into applyThumbnails if it exists
    if (typeof global.applyThumbnails === "function" && !global.__gearHooked__) {
      const original = global.applyThumbnails;
      global.applyThumbnails = function (events) {
        const input = events || global.__RAW_EVENTS__ || [];
        const filtered = applyMaxEventsFilter(input);
        return original.call(this, filtered);
      };
      global.__gearHooked__ = true;
    }

    // 5. Detect gear icon and attach click
    attachGearIconHandler();

    // 6. Apply source badges visibility
    applySettingsToPage();

    // 7. Listen for window resize to re-build modal if open (mobile/desktop toggle)
    window.addEventListener(
      "resize",
      throttle(() => {
        if (modalOpen && modalEl) {
          const sheet = modalEl.querySelector(".fte-modal-sheet");
          const isMobile = window.innerWidth < 640;
          if (sheet) {
            sheet.classList.toggle("fte-modal-sheet--mobile", isMobile);
            sheet.classList.toggle("fte-modal-sheet--desktop", !isMobile);
          }
        }
      }, THROTTLE_MS)
    );
  }

  function attachGearIconHandler() {
    // Try multiple selectors to find the gear/config icon
    const selectors = [
      '[data-testid="config-button"]',
      'button[aria-label*="settings" i]',
      'button[aria-label*="config" i]',
      'button[title*="settings" i]',
      'button[title*="config" i]',
      'button:has-text("⚙️")',
      'a:has-text("⚙️")',
      'button:has-text("Settings")',
      'button:has-text("Config")',
    ];

    let gearBtn = null;
    for (const sel of selectors) {
      try {
        gearBtn = document.querySelector(sel);
        if (gearBtn) break;
      } catch {
        // Some selectors may be invalid in old browsers (e.g. :has-text)
      }
    }

    // Fallback: if no gear button found, create one in the header
    if (!gearBtn) {
      const header = document.querySelector("header, nav, .header, #header");
      if (header) {
        gearBtn = createElement("button", {
          className: "fte-gear-icon-btn",
          "aria-label": "Open event settings",
          title: "Settings",
        }, ["⚙️"]);
        header.appendChild(gearBtn);
      }
    }

    if (gearBtn) {
      gearBtn.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        openModal();
      });
    }
  }

  /* ─────────────────────────────────────────────────────────────────────────── */
  /*  Expose public API                                                         */
  /* ─────────────────────────────────────────────────────────────────────────── */

  global.GearSettings = {
    open: openModal,
    close: closeModal,
    getSettings: () => ({ ...settings }),
    setSettings: (partial) => {
      settings = deepMerge(settings, partial);
      autoSave();
    },
    applyFilter: applyMaxEventsFilter,
    checkSession,
    refresh: init,
  };

  // Auto-init on DOM ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})(window);
