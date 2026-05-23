import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  X,
  Settings,
  Info,
  Calendar,
  Filter,
  Database,
  Eye,
  EyeOff,
  Check,
  ChevronRight,
  ShieldCheck,
  Rss,
  Globe,
  CloudRain,
  Bell,
  Share2,
  Layers,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface EventSource {
  id: string;
  name: string;
  type: "api" | "rss" | "scrape";
  eventCount: number;
  enabled: boolean;
  exemptFromLimit: boolean;
  icon?: string;
}

interface GearSettings {
  maxEventsPerDayPerSource: number;
  exemptEventbrite: boolean;
  showSourceBadges: boolean;
  groupByDate: boolean;
  deduplicate: boolean;
  sources: EventSource[];
  calendarExportFormat: "ical" | "google" | "both";
}

interface GearSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  isLoggedIn: boolean;
  initialSettings?: Partial<GearSettings>;
  onSettingsChange?: (settings: GearSettings) => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Default Sources (mirrors current + planned sources)
// ─────────────────────────────────────────────────────────────────────────────

const DEFAULT_SOURCES: EventSource[] = [
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

const DEFAULT_SETTINGS: GearSettings = {
  maxEventsPerDayPerSource: 3,
  exemptEventbrite: true,
  showSourceBadges: true,
  groupByDate: false,
  deduplicate: true,
  sources: DEFAULT_SOURCES,
  calendarExportFormat: "both",
};

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function useLocalStorage<T>(key: string, initial: T): [T, (v: T) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });

  const setStored = useCallback(
    (v: T) => {
      setValue(v);
      try {
        localStorage.setItem(key, JSON.stringify(v));
      } catch {
        // Silently fail if localStorage is unavailable (private mode)
      }
    },
    [key]
  );

  return [value, setStored];
}

function classNames(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

const SectionHeader: React.FC<{ icon: React.ReactNode; label: string }> = ({ icon, label }) => (
  <div className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3 mt-6 first:mt-0">
    {icon}
    <span>{label}</span>
  </div>
);

const InfoTooltip: React.FC<{ text: string }> = ({ text }) => (
  <div className="group relative inline-block ml-1">
    <Info className="w-3.5 h-3.5 text-slate-400 cursor-help" />
    <div className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-56 rounded-md bg-slate-800 px-3 py-2 text-xs text-slate-100 opacity-0 transition-opacity group-hover:opacity-100 z-50 shadow-lg border border-slate-700">
      {text}
      <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-slate-800" />
    </div>
  </div>
);

const Toggle: React.FC<{
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
  info?: string;
  disabled?: boolean;
}> = ({ checked, onChange, label, description, info, disabled }) => (
  <div className={classNames("flex items-start justify-between py-2", disabled && "opacity-50")}>
    <div className="pr-4">
      <div className="flex items-center">
        <span className="text-sm font-medium text-slate-100">{label}</span>
        {info && <InfoTooltip text={info} />}
      </div>
      {description && <p className="text-xs text-slate-400 mt-0.5">{description}</p>}
    </div>
    <button
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={classNames(
        "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900",
        checked ? "bg-indigo-500" : "bg-slate-600"
      )}
    >
      <span
        className={classNames(
          "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition",
          checked ? "translate-x-5" : "translate-x-0"
        )}
      />
    </button>
  </div>
);

const SourceBadge: React.FC<{ type: EventSource["type"] }> = ({ type }) => {
  const styles =
    type === "api"
      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      : type === "rss"
      ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
      : "bg-rose-500/10 text-rose-400 border-rose-500/20";

  const label = type === "api" ? "Official API" : type === "rss" ? "RSS Feed" : "Scraped";
  const Icon = type === "api" ? ShieldCheck : type === "rss" ? Rss : Globe;

  return (
    <span className={classNames("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium", styles)}>
      <Icon className="w-3 h-3" />
      {label}
    </span>
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Main Modal Component
// ─────────────────────────────────────────────────────────────────────────────

export const GearSettingsModal: React.FC<GearSettingsModalProps> = ({
  isOpen,
  onClose,
  isLoggedIn,
  initialSettings,
  onSettingsChange,
}) => {
  const modalRef = useRef<HTMLDivElement>(null);
  const lastFocusedRef = useRef<HTMLElement | null>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  const STORAGE_KEY = isLoggedIn ? "fte_settings_v1" : "fte_settings_local_v1";
  const [persisted, setPersisted] = useLocalStorage<GearSettings>(STORAGE_KEY, {
    ...DEFAULT_SETTINGS,
    ...initialSettings,
  });

  const [settings, setSettings] = useState<GearSettings>(persisted);
  const [activeTab, setActiveTab] = useState<"display" | "sources" | "export" | "advanced">("display");
  const [showSaved, setShowSaved] = useState(false);

  // Focus trap + ESC handler
  useEffect(() => {
    if (!isOpen) return;

    lastFocusedRef.current = document.activeElement as HTMLElement;
    setTimeout(() => closeBtnRef.current?.focus(), 50);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        handleClose();
        return;
      }
      if (e.key !== "Tab" || !modalRef.current) return;

      const focusable = modalRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last?.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first?.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
      lastFocusedRef.current?.focus();
    };
  }, [isOpen]);

  const handleClose = useCallback(() => {
    // Persist before closing
    setPersisted(settings);
    onSettingsChange?.(settings);
    onClose();
  }, [settings, setPersisted, onSettingsChange, onClose]);

  const updateSetting = useCallback(<K extends keyof GearSettings>(key: K, value: GearSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
  }, []);

  const toggleSource = useCallback((sourceId: string) => {
    setSettings((prev) => ({
      ...prev,
      sources: prev.sources.map((s) => (s.id === sourceId ? { ...s, enabled: !s.enabled } : s)),
    }));
  }, []);

  const handleExport = useCallback(() => {
    const url = `/api/export/calendar?format=${settings.calendarExportFormat}&filters=active`;
    window.open(url, "_blank");
  }, [settings.calendarExportFormat]);

  const handleSaveNow = useCallback(() => {
    setPersisted(settings);
    onSettingsChange?.(settings);
    setShowSaved(true);
    setTimeout(() => setShowSaved(false), 2000);
  }, [settings, setPersisted, onSettingsChange]);

  if (!isOpen) return null;

  const totalEnabledEvents = settings.sources.filter((s) => s.enabled).reduce((sum, s) => sum + s.eventCount, 0);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="gear-settings-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      {/* Modal Sheet — full-screen on mobile, centered on desktop */}
      <div
        ref={modalRef}
        className="relative w-full sm:max-w-lg sm:rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl max-h-[90vh] sm:max-h-[85vh] flex flex-col overflow-hidden"
      >
        {/* ── Header ── */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700/50">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10">
              <Settings className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <h2 id="gear-settings-title" className="text-base font-semibold text-slate-100">
                Event Settings
              </h2>
              <p className="text-xs text-slate-400">
                {isLoggedIn ? "Settings saved to your account" : "Settings saved locally on this device"}
              </p>
            </div>
          </div>
          <button
            ref={closeBtnRef}
            onClick={handleClose}
            aria-label="Close settings"
            className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* ── Tabs ── */}
        <div className="flex gap-1 px-3 pt-2 pb-0 overflow-x-auto scrollbar-hide">
          {(
            [
              { key: "display", icon: <Filter className="w-3.5 h-3.5" />, label: "Display" },
              { key: "sources", icon: <Database className="w-3.5 h-3.5" />, label: "Sources" },
              { key: "export", icon: <Calendar className="w-3.5 h-3.5" />, label: "Export" },
              { key: "advanced", icon: <Layers className="w-3.5 h-3.5" />, label: "Advanced" },
            ] as const
          ).map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={classNames(
                "flex items-center gap-1.5 rounded-t-lg px-3 py-2 text-xs font-medium transition whitespace-nowrap",
                activeTab === tab.key
                  ? "bg-slate-800 text-indigo-300 border-t border-x border-slate-700/50"
                  : "text-slate-400 hover:text-slate-200"
              )}
              aria-selected={activeTab === tab.key}
              role="tab"
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── Content ── */}
        <div className="flex-1 overflow-y-auto px-5 py-4 bg-slate-800/50 border-t border-slate-700/50">
          {/* ── TAB: Display ── */}
          {activeTab === "display" && (
            <div>
              <SectionHeader icon={<Filter className="w-4 h-4" />} label="Display Preferences" />

              {/* Max events per day slider */}
              <div className="mb-5 p-3 rounded-xl bg-slate-700/30 border border-slate-700/50">
                <div className="flex items-center justify-between mb-2">
                  <label htmlFor="max-events-slider" className="text-sm font-medium text-slate-100">
                    Max events per day per source
                  </label>
                  <span className="inline-flex items-center justify-center h-7 min-w-[2rem] rounded-md bg-indigo-500/10 px-2 text-sm font-bold text-indigo-300">
                    {settings.maxEventsPerDayPerSource}
                  </span>
                </div>
                <input
                  id="max-events-slider"
                  type="range"
                  min={1}
                  max={10}
                  step={1}
                  value={settings.maxEventsPerDayPerSource}
                  onChange={(e) => updateSetting("maxEventsPerDayPerSource", parseInt(e.target.value, 10))}
                  className="w-full h-2 rounded-lg appearance-none cursor-pointer bg-slate-600 accent-indigo-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
                  aria-valuemin={1}
                  aria-valuemax={10}
                  aria-valuenow={settings.maxEventsPerDayPerSource}
                  aria-label="Maximum events per day per source"
                />
                <div className="flex justify-between mt-1 text-[10px] text-slate-500 font-medium">
                  <span>1</span>
                  <span>5</span>
                  <span>10</span>
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  Limits how many events from a single source appear on any given day. Set to 10 to show all.
                </p>
              </div>

              <Toggle
                checked={settings.exemptEventbrite}
                onChange={(v) => updateSetting("exemptEventbrite", v)}
                label="Exempt Eventbrite from limit"
                description="Eventbrite is a major source with high-quality listings. Keep unlimited."
                info="Eventbrite typically provides 40-60% of Toronto events. Exempting ensures comprehensive coverage."
              />

              <Toggle
                checked={settings.showSourceBadges}
                onChange={(v) => updateSetting("showSourceBadges", v)}
                label="Show source badges on event cards"
                description="Display a small icon indicating which source each event came from."
              />

              <Toggle
                checked={settings.groupByDate}
                onChange={(v) => updateSetting("groupByDate", v)}
                label="Group events by date"
                description="Organize events into date sections (Today, Tomorrow, etc.) instead of a flat grid."
              />
            </div>
          )}

          {/* ── TAB: Sources ── */}
          {activeTab === "sources" && (
            <div>
              <SectionHeader icon={<Database className="w-4 h-4" />} label="Data Sources" />

              <div className="mb-3 flex items-center justify-between">
                <span className="text-xs text-slate-400">
                  {settings.sources.filter((s) => s.enabled).length} of {settings.sources.length} active
                </span>
                <span className="text-xs text-slate-400">
                  <span className="text-slate-200 font-medium">{totalEnabledEvents.toLocaleString()}</span> events enabled
                </span>
              </div>

              <div className="space-y-1.5">
                {settings.sources.map((source) => (
                  <div
                    key={source.id}
                    className={classNames(
                      "flex items-center justify-between rounded-lg border px-3 py-2.5 transition",
                      source.enabled
                        ? "bg-slate-700/20 border-slate-600/30"
                        : "bg-slate-800/40 border-slate-700/20 opacity-60"
                    )}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <button
                        onClick={() => toggleSource(source.id)}
                        aria-label={`${source.enabled ? "Disable" : "Enable"} ${source.name}`}
                        className={classNames(
                          "flex h-6 w-6 shrink-0 items-center justify-center rounded-md border transition",
                          source.enabled
                            ? "border-indigo-500/50 bg-indigo-500/10 text-indigo-400"
                            : "border-slate-600 bg-slate-700/50 text-slate-500"
                        )}
                      >
                        {source.enabled ? <Check className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
                      </button>

                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-slate-100 truncate">{source.name}</span>
                          <SourceBadge type={source.type} />
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-xs text-slate-400">
                            {source.eventCount > 0 ? `${source.eventCount.toLocaleString()} events` : "Not yet synced"}
                          </span>
                          {source.exemptFromLimit && (
                            <span className="text-[10px] text-indigo-300 bg-indigo-500/10 px-1.5 py-0.5 rounded">
                              Exempt from limit
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    <ChevronRight className="w-4 h-4 text-slate-600 shrink-0" />
                  </div>
                ))}
              </div>

              <div className="mt-4 p-3 rounded-lg bg-slate-700/20 border border-slate-700/30">
                <p className="text-xs text-slate-300">
                  <strong className="text-slate-100">Pro tip:</strong> Disabling sources reduces duplicates but may hide unique niche events. We recommend keeping all API sources enabled.
                </p>
              </div>
            </div>
          )}

          {/* ── TAB: Export ── */}
          {activeTab === "export" && (
            <div>
              <SectionHeader icon={<Calendar className="w-4 h-4" />} label="Calendar Export" />

              <div className="p-3 rounded-xl bg-slate-700/30 border border-slate-700/50 mb-4">
                <p className="text-sm text-slate-300 mb-3">
                  Export the currently filtered events to your preferred calendar app. Updates hourly.
                </p>

                <div className="flex gap-2 mb-3">
                  {(["ical", "google", "both"] as const).map((fmt) => (
                    <button
                      key={fmt}
                      onClick={() => updateSetting("calendarExportFormat", fmt)}
                      className={classNames(
                        "flex-1 rounded-lg px-3 py-2 text-xs font-medium transition border",
                        settings.calendarExportFormat === fmt
                          ? "bg-indigo-500/10 border-indigo-500/30 text-indigo-300"
                          : "bg-slate-700/30 border-slate-600/30 text-slate-400 hover:text-slate-200"
                      )}
                    >
                      {fmt === "ical" && "iCal (.ics)"}
                      {fmt === "google" && "Google Calendar"}
                      {fmt === "both" && "Both"}
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleExport}
                  className="w-full flex items-center justify-center gap-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
                >
                  <Share2 className="w-4 h-4" />
                  Export My Filtered View
                </button>

                <p className="text-[10px] text-slate-500 mt-2 text-center">
                  Generates a downloadable .ics file and/or Google Calendar subscription URL.
                </p>
              </div>

              <SectionHeader icon={<Bell className="w-4 h-4" />} label="Notification Preferences" />
              <div className="p-3 rounded-lg bg-slate-700/10 border border-slate-700/20 opacity-60">
                <p className="text-xs text-slate-400">
                  <strong className="text-slate-300">Coming soon:</strong> Get notified when new events match your saved filters. Requires sign-in.
                </p>
              </div>
            </div>
          )}

          {/* ── TAB: Advanced ── */}
          {activeTab === "advanced" && (
            <div>
              <SectionHeader icon={<Layers className="w-4 h-4" />} label="Smart Deduplication" />

              <Toggle
                checked={settings.deduplicate}
                onChange={(v) => updateSetting("deduplicate", v)}
                label="Hide likely duplicates across sources"
                description="When the same event is found on multiple platforms, only show the best-quality listing."
                info="Matches on title similarity + venue + date. Prefers API sources with full descriptions and images."
              />

              {settings.deduplicate && (
                <div className="mt-2 mb-4 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                  <div className="flex items-start gap-2">
                    <ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs font-medium text-emerald-300">Deduplication active</p>
                      <p className="text-xs text-emerald-400/70 mt-0.5">
                        We compare title (80% match), venue name, and date within a 2-hour window. The listing with the most metadata wins.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <SectionHeader icon={<CloudRain className="w-4 h-4" />} label="Weather-Aware Filtering" />
              <div className="p-3 rounded-lg bg-slate-700/10 border border-slate-700/20 opacity-60">
                <p className="text-xs text-slate-400">
                  <strong className="text-slate-300">Future:</strong> Automatically deprioritize outdoor events when rain is forecasted. Toggle will appear here when enabled.
                </p>
              </div>

              <SectionHeader icon={<Database className="w-4 h-4" />} label="Data Quality" />
              <div className="p-3 rounded-lg bg-slate-700/20 border border-slate-700/30">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-slate-300">Events with missing dates</span>
                  <span className="text-xs font-medium text-amber-300">49 events</span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-slate-600 overflow-hidden">
                  <div className="h-full rounded-full bg-amber-400" style={{ width: "4.9%" }} />
                </div>
                <p className="text-[10px] text-slate-400 mt-1.5">
                  These events are shown anyway — they may have date ranges like "Summer 2026" or ongoing recurrences.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* ── Footer ── */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-slate-700/50 bg-slate-800/30">
          <div className="flex items-center gap-1.5">
            {showSaved ? (
              <span className="flex items-center gap-1 text-xs text-emerald-400 animate-pulse">
                <Check className="w-3.5 h-3.5" /> Saved
              </span>
            ) : (
              <span className="text-xs text-slate-500">Changes auto-save</span>
            )}
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleSaveNow}
              className="rounded-lg px-3 py-1.5 text-xs font-medium bg-slate-700 hover:bg-slate-600 text-slate-200 transition"
            >
              Save Now
            </button>
            <button
              onClick={handleClose}
              className="rounded-lg px-4 py-1.5 text-xs font-medium bg-indigo-600 hover:bg-indigo-500 text-white transition"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GearSettingsModal;
