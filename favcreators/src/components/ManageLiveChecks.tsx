import { useState, useMemo } from "react";
import type { Creator, Platform } from "../types";

interface ManageLiveChecksProps {
  creators: Creator[];
  /** User's default live platforms (used for backward compat defaults). Falls back to ["tiktok"]. */
  defaultLivePlatforms?: Platform[];
  onSave: (updates: { creatorId: string; isLiveStreamer: boolean; checkLiveAccounts: { accountId: string; checkLive: boolean }[] }[]) => void;
  onClose: () => void;
}

const PLATFORM_ICONS: Record<string, string> = {
  kick: "⚡",
  twitch: "🎮",
  tiktok: "📱",
  youtube: "▶️",
  instagram: "📷",
  spotify: "🎵",
  twitter: "🐦",
  other: "🌐",
};

const LIVE_CAPABLE_PLATFORMS: Platform[] = ["kick", "twitch", "tiktok", "youtube", "instagram"];

/**
 * State uses array indices (not account IDs) to avoid duplicate-ID bugs.
 * accountChecks[i] corresponds to creator.accounts[i].
 */
interface CreatorLocalState {
  isLiveStreamer: boolean;
  accountChecks: boolean[]; // parallel to creator.accounts
}

export default function ManageLiveChecks({ creators, defaultLivePlatforms, onSave, onClose }: ManageLiveChecksProps) {
  const livePlats = defaultLivePlatforms ?? ["tiktok"];

  // Snapshot creators at mount so indices stay stable
  const [creatorsSnapshot] = useState(() => creators);

  const [localState, setLocalState] = useState<Record<string, CreatorLocalState>>(() => {
    const state: Record<string, CreatorLocalState> = {};
    for (const c of creatorsSnapshot) {
      const hasDefaultLivePlatform = c.accounts.some((a) => livePlats.includes(a.platform));
      const isStreamer = c.isLiveStreamer ?? hasDefaultLivePlatform;
      state[c.id] = {
        isLiveStreamer: isStreamer,
        accountChecks: c.accounts.map((a) =>
          a.checkLive ?? (isStreamer ? livePlats.includes(a.platform) : false)
        ),
      };
    }
    return state;
  });

  const [searchFilter, setSearchFilter] = useState("");
  const [showOnlyEnabled, setShowOnlyEnabled] = useState(false);
  const [expandedCreator, setExpandedCreator] = useState<string | null>(null);

  // Platform filter checkboxes for bulk actions
  const [bulkPlatforms, setBulkPlatforms] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (const p of LIVE_CAPABLE_PLATFORMS) init[p] = true;
    return init;
  });

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    action: "enable" | "disable";
    platforms: string[];
    affectedCount: number;
  } | null>(null);

  // Sort: enabled first, then alphabetical
  const sortedCreators = useMemo(() => {
    let filtered = [...creatorsSnapshot];
    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.accounts.some((a) => a.username.toLowerCase().includes(q) || a.platform.toLowerCase().includes(q))
      );
    }
    if (showOnlyEnabled) {
      filtered = filtered.filter((c) => localState[c.id]?.isLiveStreamer);
    }
    return filtered.sort((a, b) => {
      const aEnabled = localState[a.id]?.isLiveStreamer ? 1 : 0;
      const bEnabled = localState[b.id]?.isLiveStreamer ? 1 : 0;
      if (aEnabled !== bEnabled) return bEnabled - aEnabled;
      return a.name.localeCompare(b.name);
    });
  }, [creatorsSnapshot, searchFilter, showOnlyEnabled, localState]);

  const enabledCount = Object.values(localState).filter((s) => s.isLiveStreamer).length;
  const totalCount = creatorsSnapshot.length;

  const toggleCreator = (creatorId: string) => {
    setLocalState((prev) => ({
      ...prev,
      [creatorId]: {
        ...prev[creatorId],
        isLiveStreamer: !prev[creatorId].isLiveStreamer,
      },
    }));
  };

  /** Toggle a single account by its array index (not by ID — avoids duplicate-ID bugs) */
  const toggleAccount = (creatorId: string, accountIdx: number) => {
    setLocalState((prev) => ({
      ...prev,
      [creatorId]: {
        ...prev[creatorId],
        accountChecks: prev[creatorId].accountChecks.map((v, i) => (i === accountIdx ? !v : v)),
      },
    }));
  };

  const selectedBulkPlatforms = LIVE_CAPABLE_PLATFORMS.filter((p) => bulkPlatforms[p]);

  const getAffectedCreators = (action: "enable" | "disable") => {
    return creatorsSnapshot.filter((c) => {
      const ls = localState[c.id];
      if (!ls) return false;
      const hasPlatform = c.accounts.some((a) => selectedBulkPlatforms.includes(a.platform));
      if (!hasPlatform) return false;
      // For enable: only count currently-disabled ones; for disable: only currently-enabled
      return action === "enable" ? !ls.isLiveStreamer : ls.isLiveStreamer;
    });
  };

  const requestEnableAll = () => {
    if (selectedBulkPlatforms.length === 0) return;
    const affected = getAffectedCreators("enable");
    setConfirmDialog({ action: "enable", platforms: [...selectedBulkPlatforms], affectedCount: affected.length });
  };

  const requestDisableAll = () => {
    if (selectedBulkPlatforms.length === 0) return;
    const affected = getAffectedCreators("disable");
    setConfirmDialog({ action: "disable", platforms: [...selectedBulkPlatforms], affectedCount: affected.length });
  };

  const executeConfirmedBulk = () => {
    if (!confirmDialog) return;
    const { action, platforms } = confirmDialog;
    setLocalState((prev) => {
      const next = { ...prev };
      for (const c of creatorsSnapshot) {
        const hasPlatform = c.accounts.some((a) => platforms.includes(a.platform));
        if (!hasPlatform) continue;
        if (action === "enable") {
          // Enable the creator and check the selected platforms
          const newChecks = [...next[c.id].accountChecks];
          c.accounts.forEach((a, idx) => {
            if (platforms.includes(a.platform)) newChecks[idx] = true;
          });
          next[c.id] = { ...next[c.id], isLiveStreamer: true, accountChecks: newChecks };
        } else {
          // Uncheck the selected platforms; if none remain checked, disable creator entirely
          const newChecks = [...next[c.id].accountChecks];
          c.accounts.forEach((a, idx) => {
            if (platforms.includes(a.platform)) newChecks[idx] = false;
          });
          const anyStillChecked = newChecks.some((v) => v);
          next[c.id] = { ...next[c.id], isLiveStreamer: anyStillChecked, accountChecks: newChecks };
        }
      }
      return next;
    });
    setConfirmDialog(null);
  };

  const handleSave = () => {
    const updates = Object.entries(localState).map(([creatorId, state]) => {
      const creator = creatorsSnapshot.find((c) => c.id === creatorId);
      return {
        creatorId,
        isLiveStreamer: state.isLiveStreamer,
        checkLiveAccounts: state.accountChecks.map((checkLive, idx) => ({
          accountId: creator?.accounts[idx]?.id ?? "",
          checkLive,
        })),
      };
    });
    onSave(updates);
    onClose();
  };

  // Count changes from original
  const changeCount = useMemo(() => {
    let count = 0;
    for (const c of creatorsSnapshot) {
      const ls = localState[c.id];
      if (!ls) continue;
      const hasDefaultLive = c.accounts.some((a) => livePlats.includes(a.platform));
      const origEnabled = c.isLiveStreamer ?? hasDefaultLive;
      if (ls.isLiveStreamer !== origEnabled) count++;
      for (let i = 0; i < c.accounts.length; i++) {
        const a = c.accounts[i];
        const origCheck = a.checkLive ?? (origEnabled ? livePlats.includes(a.platform) : false);
        if ((ls.accountChecks[i] ?? false) !== origCheck) count++;
      }
    }
    return count;
  }, [creatorsSnapshot, localState]);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.75)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 10000,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        style={{
          background: "var(--card-bg, #1a1a2e)",
          borderRadius: "16px",
          border: "1px solid rgba(255,255,255,0.15)",
          maxWidth: "640px",
          width: "95%",
          maxHeight: "85vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          position: "relative",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px 16px",
            borderBottom: "1px solid rgba(255,255,255,0.1)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
            <h2 style={{ margin: 0, fontSize: "1.25rem", display: "flex", alignItems: "center", gap: "8px" }}>
              <span>📡</span> Manage Live Checks
            </h2>
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                color: "var(--text-muted)",
                fontSize: "1.5rem",
                cursor: "pointer",
                padding: "4px",
                lineHeight: 1,
              }}
            >
              &times;
            </button>
          </div>
          <p style={{ margin: "0 0 12px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
            Toggle which creators get checked for live status. Disabling creators you don't need to track will <strong style={{ color: "#86efac" }}>speed up your live check times</strong>.
          </p>

          {/* Stats bar */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "16px",
              padding: "8px 12px",
              background: "rgba(34, 197, 94, 0.1)",
              borderRadius: "8px",
              fontSize: "0.85rem",
              marginBottom: "12px",
            }}
          >
            <span style={{ color: "#86efac", fontWeight: 600 }}>
              {enabledCount} / {totalCount} enabled
            </span>
            <span style={{ color: "var(--text-muted)" }}>
              ~{Math.ceil(enabledCount * 0.5)}s estimated check time
            </span>
            {changeCount > 0 && (
              <span style={{ color: "#fcd34d", marginLeft: "auto" }}>
                {changeCount} unsaved change{changeCount !== 1 ? "s" : ""}
              </span>
            )}
          </div>

          {/* Search and filter */}
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <input
              type="text"
              placeholder="Search creators..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              style={{
                flex: 1,
                padding: "8px 12px",
                background: "rgba(255,255,255,0.06)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: "8px",
                color: "inherit",
                fontSize: "0.9rem",
              }}
            />
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                fontSize: "0.8rem",
                color: "var(--text-muted)",
                cursor: "pointer",
                whiteSpace: "nowrap",
              }}
            >
              <input
                type="checkbox"
                checked={showOnlyEnabled}
                onChange={(e) => setShowOnlyEnabled(e.target.checked)}
                style={{ width: "14px", height: "14px" }}
              />
              Enabled only
            </label>
          </div>

          {/* Platform filter checkboxes */}
          <div style={{ marginTop: "10px" }}>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: "6px" }}>
              Select platforms for bulk actions:
            </div>
            <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "8px" }}>
              {LIVE_CAPABLE_PLATFORMS.map((p) => (
                <label
                  key={p}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    padding: "4px 10px",
                    borderRadius: "6px",
                    background: bulkPlatforms[p] ? "rgba(99,102,241,0.15)" : "rgba(255,255,255,0.04)",
                    border: `1px solid ${bulkPlatforms[p] ? "rgba(99,102,241,0.4)" : "rgba(255,255,255,0.1)"}`,
                    cursor: "pointer",
                    fontSize: "0.8rem",
                    transition: "all 0.15s",
                    userSelect: "none",
                  }}
                >
                  <input
                    type="checkbox"
                    checked={bulkPlatforms[p]}
                    onChange={(e) => setBulkPlatforms((prev) => ({ ...prev, [p]: e.target.checked }))}
                    style={{ width: "14px", height: "14px", cursor: "pointer" }}
                  />
                  <span>{PLATFORM_ICONS[p] || "🌐"}</span>
                  <span style={{ color: bulkPlatforms[p] ? "#c7d2fe" : "var(--text-muted)" }}>{p}</span>
                </label>
              ))}
            </div>

            {/* Bulk action buttons */}
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={requestEnableAll}
                disabled={selectedBulkPlatforms.length === 0}
                style={{
                  padding: "6px 12px",
                  background: selectedBulkPlatforms.length > 0 ? "rgba(34, 197, 94, 0.15)" : "rgba(255,255,255,0.04)",
                  border: `1px solid ${selectedBulkPlatforms.length > 0 ? "rgba(34, 197, 94, 0.3)" : "rgba(255,255,255,0.08)"}`,
                  borderRadius: "6px",
                  color: selectedBulkPlatforms.length > 0 ? "#86efac" : "var(--text-muted)",
                  cursor: selectedBulkPlatforms.length > 0 ? "pointer" : "not-allowed",
                  fontSize: "0.8rem",
                  fontWeight: 500,
                  opacity: selectedBulkPlatforms.length > 0 ? 1 : 0.5,
                }}
              >
                Enable All
              </button>
              <button
                onClick={requestDisableAll}
                disabled={selectedBulkPlatforms.length === 0}
                style={{
                  padding: "6px 12px",
                  background: selectedBulkPlatforms.length > 0 ? "rgba(239, 68, 68, 0.15)" : "rgba(255,255,255,0.04)",
                  border: `1px solid ${selectedBulkPlatforms.length > 0 ? "rgba(239, 68, 68, 0.3)" : "rgba(255,255,255,0.08)"}`,
                  borderRadius: "6px",
                  color: selectedBulkPlatforms.length > 0 ? "#fca5a5" : "var(--text-muted)",
                  cursor: selectedBulkPlatforms.length > 0 ? "pointer" : "not-allowed",
                  fontSize: "0.8rem",
                  fontWeight: 500,
                  opacity: selectedBulkPlatforms.length > 0 ? 1 : 0.5,
                }}
              >
                Disable All
              </button>
            </div>
          </div>
        </div>

        {/* Scrollable list */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "12px 24px",
          }}
        >
          {sortedCreators.length === 0 ? (
            <div style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)" }}>
              No creators match your search.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              {sortedCreators.map((c) => {
                const ls = localState[c.id];
                if (!ls) return null;
                const isExpanded = expandedCreator === c.id;

                // Build list with original indices so toggles target the right slot
                const liveCapableWithIdx = c.accounts
                  .map((a, idx) => ({ account: a, originalIdx: idx }))
                  .filter(({ account }) => LIVE_CAPABLE_PLATFORMS.includes(account.platform));

                const checkedAccountCount = liveCapableWithIdx.filter(
                  ({ originalIdx }) => ls.accountChecks[originalIdx]
                ).length;

                return (
                  <div key={c.id}>
                    {/* Creator row */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        padding: "10px 12px",
                        background: ls.isLiveStreamer ? "rgba(34, 197, 94, 0.08)" : "rgba(255,255,255,0.02)",
                        border: `1px solid ${ls.isLiveStreamer ? "rgba(34, 197, 94, 0.2)" : "rgba(255,255,255,0.06)"}`,
                        borderRadius: isExpanded ? "8px 8px 0 0" : "8px",
                        transition: "all 0.15s ease",
                        cursor: "pointer",
                      }}
                      onClick={() => setExpandedCreator(isExpanded ? null : c.id)}
                    >
                      {/* Toggle */}
                      <div
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleCreator(c.id);
                        }}
                        style={{
                          width: "44px",
                          height: "24px",
                          borderRadius: "12px",
                          background: ls.isLiveStreamer ? "#22c55e" : "rgba(255,255,255,0.15)",
                          position: "relative",
                          cursor: "pointer",
                          transition: "background 0.2s",
                          flexShrink: 0,
                        }}
                      >
                        <div
                          style={{
                            position: "absolute",
                            top: "2px",
                            left: ls.isLiveStreamer ? "22px" : "2px",
                            width: "20px",
                            height: "20px",
                            borderRadius: "50%",
                            background: "white",
                            transition: "left 0.2s",
                            boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
                          }}
                        />
                      </div>

                      {/* Avatar */}
                      <img
                        src={
                          c.avatarUrl ||
                          `https://ui-avatars.com/api/?name=${encodeURIComponent(c.name)}&background=random&size=32`
                        }
                        alt={c.name}
                        style={{
                          width: "32px",
                          height: "32px",
                          borderRadius: "50%",
                          objectFit: "cover",
                          flexShrink: 0,
                        }}
                        onError={(e) => {
                          e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(c.name)}&background=random&size=32`;
                        }}
                      />

                      {/* Name and platforms */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontWeight: 500,
                            fontSize: "0.95rem",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                          }}
                        >
                          {c.name}
                        </div>
                        <div style={{ display: "flex", gap: "4px", flexWrap: "wrap", marginTop: "2px" }}>
                          {c.accounts.map((a, idx) =>
                            a.url ? (
                              <a
                                key={`${idx}_${a.platform}_${a.username}`}
                                href={a.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                title={`Open @${a.username} on ${a.platform}`}
                                style={{
                                  fontSize: "0.7rem",
                                  padding: "1px 5px",
                                  borderRadius: "4px",
                                  textDecoration: "none",
                                  background: ls.isLiveStreamer && ls.accountChecks[idx]
                                    ? "rgba(34, 197, 94, 0.2)"
                                    : "rgba(255,255,255,0.06)",
                                  color: ls.isLiveStreamer && ls.accountChecks[idx]
                                    ? "#86efac"
                                    : "var(--text-muted)",
                                  transition: "filter 0.15s",
                                }}
                                onMouseEnter={(e) => { e.currentTarget.style.filter = "brightness(1.3)"; }}
                                onMouseLeave={(e) => { e.currentTarget.style.filter = ""; }}
                              >
                                {PLATFORM_ICONS[a.platform] || "🌐"} {a.platform}
                              </a>
                            ) : (
                              <span
                                key={`${idx}_${a.platform}_${a.username}`}
                                style={{
                                  fontSize: "0.7rem",
                                  padding: "1px 5px",
                                  borderRadius: "4px",
                                  background: ls.isLiveStreamer && ls.accountChecks[idx]
                                    ? "rgba(34, 197, 94, 0.2)"
                                    : "rgba(255,255,255,0.06)",
                                  color: ls.isLiveStreamer && ls.accountChecks[idx]
                                    ? "#86efac"
                                    : "var(--text-muted)",
                                }}
                              >
                                {PLATFORM_ICONS[a.platform] || "🌐"} {a.platform}
                              </span>
                            )
                          )}
                        </div>
                      </div>

                      {/* Quick info */}
                      <div style={{ textAlign: "right", flexShrink: 0 }}>
                        {ls.isLiveStreamer && liveCapableWithIdx.length > 0 && (
                          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                            {checkedAccountCount}/{liveCapableWithIdx.length} platforms
                          </div>
                        )}
                      </div>

                      {/* Expand arrow */}
                      {liveCapableWithIdx.length > 0 && ls.isLiveStreamer && (
                        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", flexShrink: 0 }}>
                          {isExpanded ? "▲" : "▼"}
                        </span>
                      )}
                    </div>

                    {/* Expanded: per-account checkboxes */}
                    {isExpanded && ls.isLiveStreamer && liveCapableWithIdx.length > 0 && (
                      <div
                        style={{
                          padding: "8px 12px 12px 68px",
                          background: "rgba(34, 197, 94, 0.04)",
                          border: "1px solid rgba(34, 197, 94, 0.2)",
                          borderTop: "none",
                          borderRadius: "0 0 8px 8px",
                        }}
                      >
                        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "8px" }}>
                          Select which platforms to check for live:
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                          {liveCapableWithIdx.map(({ account: a, originalIdx }) => (
                            <div
                              key={`${originalIdx}_${a.platform}_${a.username}`}
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                                padding: "4px 8px",
                                borderRadius: "6px",
                                background: ls.accountChecks[originalIdx] ? "rgba(34, 197, 94, 0.1)" : "transparent",
                                transition: "background 0.15s",
                              }}
                            >
                              <input
                                type="checkbox"
                                checked={ls.accountChecks[originalIdx] ?? false}
                                onChange={() => toggleAccount(c.id, originalIdx)}
                                style={{ width: "16px", height: "16px", cursor: "pointer" }}
                              />
                              <span style={{ fontSize: "0.9rem" }}>
                                {PLATFORM_ICONS[a.platform] || "🌐"} {a.platform}
                              </span>
                              {a.url ? (
                                <a
                                  href={a.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  onClick={(e) => e.stopPropagation()}
                                  style={{
                                    fontSize: "0.8rem",
                                    color: "#93c5fd",
                                    textDecoration: "none",
                                    borderBottom: "1px dashed rgba(147, 197, 253, 0.4)",
                                    transition: "color 0.15s, border-color 0.15s",
                                  }}
                                  onMouseEnter={(e) => {
                                    e.currentTarget.style.color = "#bfdbfe";
                                    e.currentTarget.style.borderBottomColor = "rgba(191, 219, 254, 0.7)";
                                  }}
                                  onMouseLeave={(e) => {
                                    e.currentTarget.style.color = "#93c5fd";
                                    e.currentTarget.style.borderBottomColor = "rgba(147, 197, 253, 0.4)";
                                  }}
                                  title={`Open ${a.url} in new tab to verify`}
                                >
                                  @{a.username} ↗
                                </a>
                              ) : (
                                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                                  @{a.username}
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Confirmation dialog overlay */}
        {confirmDialog && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: "rgba(0,0,0,0.7)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 10,
              borderRadius: "16px",
            }}
            onClick={() => setConfirmDialog(null)}
          >
            <div
              style={{
                background: "var(--card-bg, #1a1a2e)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: "12px",
                padding: "24px",
                maxWidth: "420px",
                width: "90%",
                boxShadow: "0 25px 50px rgba(0,0,0,0.5)",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <h3 style={{ margin: "0 0 12px", fontSize: "1.1rem" }}>
                {confirmDialog.action === "enable" ? "Enable" : "Disable"} creators?
              </h3>
              <p style={{ margin: "0 0 12px", fontSize: "0.9rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
                This will <strong style={{ color: confirmDialog.action === "enable" ? "#86efac" : "#fca5a5" }}>
                  {confirmDialog.action}
                </strong> live checks for{" "}
                <strong>{confirmDialog.affectedCount} creator{confirmDialog.affectedCount !== 1 ? "s" : ""}</strong> who have accounts on:
              </p>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginBottom: "16px" }}>
                {confirmDialog.platforms.map((p) => (
                  <span
                    key={p}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      padding: "4px 10px",
                      borderRadius: "6px",
                      background: confirmDialog.action === "enable" ? "rgba(34,197,94,0.15)" : "rgba(239,68,68,0.15)",
                      border: `1px solid ${confirmDialog.action === "enable" ? "rgba(34,197,94,0.3)" : "rgba(239,68,68,0.3)"}`,
                      fontSize: "0.85rem",
                      fontWeight: 500,
                    }}
                  >
                    {PLATFORM_ICONS[p] || "🌐"} {p}
                  </span>
                ))}
              </div>
              {confirmDialog.affectedCount === 0 && (
                <p style={{ margin: "0 0 12px", fontSize: "0.85rem", color: "#fcd34d" }}>
                  No creators will be affected — they are already {confirmDialog.action === "enable" ? "enabled" : "disabled"}.
                </p>
              )}
              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
                <button
                  onClick={() => setConfirmDialog(null)}
                  style={{
                    padding: "8px 16px",
                    background: "rgba(255,255,255,0.1)",
                    border: "1px solid rgba(255,255,255,0.2)",
                    borderRadius: "8px",
                    color: "white",
                    cursor: "pointer",
                    fontSize: "0.85rem",
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={executeConfirmedBulk}
                  disabled={confirmDialog.affectedCount === 0}
                  style={{
                    padding: "8px 20px",
                    background: confirmDialog.action === "enable"
                      ? (confirmDialog.affectedCount > 0 ? "rgba(34,197,94,0.3)" : "rgba(34,197,94,0.1)")
                      : (confirmDialog.affectedCount > 0 ? "rgba(239,68,68,0.3)" : "rgba(239,68,68,0.1)"),
                    border: `1px solid ${confirmDialog.action === "enable" ? "rgba(34,197,94,0.5)" : "rgba(239,68,68,0.5)"}`,
                    borderRadius: "8px",
                    color: confirmDialog.action === "enable" ? "#86efac" : "#fca5a5",
                    cursor: confirmDialog.affectedCount > 0 ? "pointer" : "not-allowed",
                    fontSize: "0.85rem",
                    fontWeight: 600,
                    opacity: confirmDialog.affectedCount > 0 ? 1 : 0.5,
                  }}
                >
                  Yes, {confirmDialog.action === "enable" ? "Enable" : "Disable"} {confirmDialog.affectedCount > 0 ? `(${confirmDialog.affectedCount})` : ""}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid rgba(255,255,255,0.1)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            {enabledCount} creator{enabledCount !== 1 ? "s" : ""} will be checked for live status
          </span>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              onClick={onClose}
              style={{
                padding: "8px 16px",
                background: "rgba(255,255,255,0.1)",
                border: "1px solid rgba(255,255,255,0.2)",
                borderRadius: "8px",
                color: "white",
                cursor: "pointer",
                fontSize: "0.9rem",
              }}
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              style={{
                padding: "8px 20px",
                background: changeCount > 0 ? "rgba(34, 197, 94, 0.3)" : "rgba(34, 197, 94, 0.15)",
                border: `1px solid ${changeCount > 0 ? "rgba(34, 197, 94, 0.6)" : "rgba(34, 197, 94, 0.3)"}`,
                borderRadius: "8px",
                color: "#86efac",
                cursor: "pointer",
                fontSize: "0.9rem",
                fontWeight: 600,
              }}
            >
              Save Changes{changeCount > 0 ? ` (${changeCount})` : ""}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
