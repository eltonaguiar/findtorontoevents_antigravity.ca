import React, { useEffect, useMemo, useRef, useState } from "react";
import type { Creator, SocialAccount } from "../types";
import { buildAvatarCandidates, buildFallbackAvatar } from "../utils/avatar";
import { fetchSocialSummary } from "../utils/socialSummary";

interface CreatorCardProps {
  creator: Creator;
  onToggleFavorite: (id: string) => void;
  onDelete: (id: string) => void;
  onRemoveAccount: (creatorId: string, accountId: string) => void;
  onCheckStatus: (id: string) => Promise<void>;
  onTogglePin: (id: string) => void;
  onUpdateNote: (id: string, note: string) => void;
  onSaveNote?: (id: string, note: string) => void;
  onUpdateSecondaryNote?: (id: string, secondaryNote: string) => void;
  onSaveSecondaryNote?: (id: string, secondaryNote: string) => void;
  onRefreshAvatar: (id: string) => Promise<void>;
  onEditCreator?: (creator: Creator) => void;
  autoExpandSecondaryNotes?: boolean;
  // Discord notification props
  discordLinked?: boolean;
  notifyEnabled?: boolean;
  onToggleNotify?: (id: string, enabled: boolean) => void;
  // Post count data from creator_status_updates + creator_mentions
  postCounts?: { total: number; recent: number } | null;
}

const formatRelativeTime = (timestamp?: number) => {
  if (!timestamp) return "Not checked yet";
  const diffMs = Date.now() - timestamp;
  const diffMinutes = Math.round(diffMs / 60000);

  if (diffMinutes < 1) return "Checked just now";
  if (diffMinutes < 60) return `Checked ${diffMinutes}m ago`;

  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `Checked ${diffHours}h ago`;

  return `Checked ${new Date(timestamp).toLocaleDateString()}`;
};

const parseFollowersCount = (followers?: string) => {
  if (!followers) return 0;
  const normalized = followers.replace(/,/g, "").trim().toLowerCase();
  const numberMatch = normalized.match(/[\d.]+/);
  if (!numberMatch) return 0;

  let value = parseFloat(numberMatch[0]);
  if (normalized.includes("m")) value *= 1_000_000;
  else if (normalized.includes("k")) value *= 1_000;

  return isFinite(value) ? value : 0;
};

const computeHealthScore = (creator: Creator) => {
  const followerSum = creator.accounts.reduce(
    (sum, acc) => sum + parseFollowersCount(acc.followers),
    0,
  );
  const base = Math.min(80, (followerSum / 1_000_000) * 10);
  let score = base;
  if (creator.isLive) score += 10;
  if (creator.isPinned) score += 5;
  if (creator.isFavorite) score += 5;
  return Math.min(100, Math.max(10, Math.round(score)));
};

type SummaryEntry = {
  status: "idle" | "loading" | "done" | "error";
  text?: string;
};

/** Helper to detect if text is a URL */
const isUrl = (text: string): boolean => {
  try {
    const trimmed = text.trim();
    if (!trimmed) return false;
    new URL(trimmed);
    return /^https?:\/\//i.test(trimmed);
  } catch {
    return false;
  }
};

const CreatorCard: React.FC<CreatorCardProps> = ({
  creator,
  onToggleFavorite,
  onDelete,
  onRemoveAccount,
  onCheckStatus,
  onTogglePin,
  onUpdateNote,
  onSaveNote,
  onUpdateSecondaryNote,
  onSaveSecondaryNote,
  onRefreshAvatar,
  onEditCreator,
  autoExpandSecondaryNotes = false,
  discordLinked = false,
  notifyEnabled = false,
  onToggleNotify,
  postCounts,
}) => {
  if (typeof onRefreshAvatar !== "function") {
    throw new Error("onRefreshAvatar prop is required in CreatorCard");
  }
  const [checking, setChecking] = useState(false);
  const [accountSummaries, setAccountSummaries] = useState<Record<string, SummaryEntry>>({});
  const [secondaryNoteExpanded, setSecondaryNoteExpanded] = useState(autoExpandSecondaryNotes);
  const [editingSecondaryNote, setEditingSecondaryNote] = useState(false);
  const [localSecondaryNote, setLocalSecondaryNote] = useState(creator.secondaryNote || "");
  const [refreshingAvatar, setRefreshingAvatar] = useState(false);
  const handleRefreshAvatar = async () => {
    setRefreshingAvatar(true);
    await onRefreshAvatar(creator.id);
    setRefreshingAvatar(false);
  };
  const isMountedRef = useRef(true);

  const healthScore = useMemo(() => computeHealthScore(creator), [creator]);
  const avatarCandidates = useMemo(() => buildAvatarCandidates(creator), [creator]);
  const [avatarCandidateIndex, setAvatarCandidateIndex] = useState(0);

  useEffect(() => {
    queueMicrotask(() => setAvatarCandidateIndex(0));
  }, [creator.id, creator.avatarUrl]);

  const avatarSrc = useMemo(() => {
    return avatarCandidates[avatarCandidateIndex] || buildFallbackAvatar(creator);
  }, [avatarCandidates, avatarCandidateIndex, creator]);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const getPlatformIcon = (platform: string) => {
    switch (platform) {
      case "youtube":
        return (
          <svg
            viewBox="0 0 24 24"
            className="platform-icon"
            fill="currentColor"
          >
            <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
          </svg>
        );
      case "tiktok":
        return (
          <svg
            viewBox="0 0 24 24"
            className="platform-icon"
            fill="currentColor"
          >
            <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.59-1.01V14.5c.01 2.32-.6 4.67-2.12 6.44-1.56 1.82-3.86 2.89-6.24 2.92-2.45.02-4.85-.92-6.49-2.73-1.74-1.92-2.43-4.63-1.89-7.14.47-2.2 1.84-4.22 3.82-5.32 1.76-1.01 3.86-1.31 5.88-.81v4.3c-1.19-.38-2.52-.16-3.52.54-.92.64-1.47 1.75-1.46 2.88-.01 1.15.54 2.29 1.48 2.95.96.69 2.21.84 3.33.4.98-.38 1.7-1.32 1.74-2.37.04-3.14.01-6.28.02-9.42z" />
          </svg>
        );
      case "instagram":
        return (
          <svg
            viewBox="0 0 24 24"
            className="platform-icon"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
            <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
            <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
          </svg>
        );
      case "kick":
        return (
          <svg
            viewBox="0 0 24 24"
            className="platform-icon"
            fill="currentColor"
          >
            <path d="M11.666 4.333H7.011v15.334h4.655v-3.889l4.643 3.889h5.68l-6.38-5.352 6.38-5.353h-5.68l-4.643 3.89V4.333z" />
          </svg>
        );
      case "twitch":
        return (
          <svg
            viewBox="0 0 24 24"
            className="platform-icon"
            fill="currentColor"
          >
            <path d="M11.571 1.429 1.286 4v14.571h4.285V22.5l4.286-3.929h3.857l7.286-7.286V1.429h-9.429zm8.571 9.429-3.429 3.429h-4.714l-2.571 2.571v-2.571H6.429V4h11.571L20.142 6.143v4.715zM15 7.429h-1.714v4.286H15V7.429zm-4.714 0H8.571v4.286h1.715V7.429z" />
          </svg>
        );
      case "spotify":
        return (
          <svg
            viewBox="0 0 24 24"
            className="platform-icon"
            fill="currentColor"
          >
            <path d="M12 2.25a9.75 9.75 0 1 0 9.75 9.75A9.76 9.76 0 0 0 12 2.25zm4.2 13.15a.75.75 0 0 1-1.04.27c-2.54-1.55-5.74-1.7-8.32-.4a.75.75 0 0 1-.52-1.38c3.12-1.18 6.74-1 9.5.5a.75.75 0 0 1 .38 1.01zm1.08-2.68a.75.75 0 0 1-1.05.33c-3.24-1.9-8.03-1.88-11.14-.44a.75.75 0 0 1-.8-1.28c3.59-2.24 8.78-2.27 12.3.5a.75.75 0 0 1 .69 1.04zm0-2.72a.75.75 0 0 1-1.04.35c-3.73-2.21-9.66-2.22-12.8-.53a.75.75 0 1 1-.76-1.3c3.7-2.16 10.05-2.14 14 .57a.75.75 0 0 1 .6 1.1z" />
          </svg>
        );
      default:
        return (
          <svg
            viewBox="0 0 24 24"
            className="platform-icon"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
          </svg>
        );
    }
  };

  const handleCheckStatus = async () => {
    setChecking(true);
    await onCheckStatus(creator.id);
    setChecking(false);
  };

  const handleAccountHover = (account: SocialAccount) => {
    if (!account.url) return;
    const current = accountSummaries[account.id];
    if (current && (current.status === "loading" || current.status === "done")) {
      return;
    }
    setAccountSummaries((prev) => ({
      ...prev,
      [account.id]: { status: "loading", text: prev[account.id]?.text },
    }));
    fetchSocialSummary(account.url)
      .then((summary) => {
        if (!isMountedRef.current) return;
        setAccountSummaries((prev) => ({
          ...prev,
          [account.id]: {
            status: "done",
            text: summary ?? "No overview found yet.",
          },
        }));
      })
      .catch(() => {
        if (!isMountedRef.current) return;
        setAccountSummaries((prev) => ({
          ...prev,
          [account.id]: {
            status: "error",
            text: "Research unavailable right now.",
          },
        }));
      });
  };

  return (
    <div className="creator-card">
      {creator.isLive && (
        <div className="live-badge">
          <div className="live-dot"></div>
          Live
        </div>
      )}

      <div
        style={{
          position: "absolute",
          top: "15px",
          right: "15px",
          display: "flex",
          gap: "8px",
          alignItems: "center",
        }}
      >
        <button
          onClick={handleCheckStatus}
          disabled={checking}
          title="Check Live Status"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "1rem",
            opacity: checking ? 0.3 : 0.6,
          }}
        >
          {checking ? "⏳" : "📡"}
        </button>
        <button
          onClick={() => onTogglePin(creator.id)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "1.2rem",
          }}
          title={creator.isPinned ? "Unpin creator" : "Pin creator"}
        >
          {creator.isPinned ? "📌" : "📍"}
        </button>
        <button
          onClick={() => onToggleFavorite(creator.id)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "1.2rem",
          }}
        >
          {creator.isFavorite ? "⭐️" : "☆"}
        </button>
        {discordLinked && onToggleNotify && (
          <button
            onClick={() => {
              // If enabling for the first time, show privacy warning
              if (!notifyEnabled) {
                const confirmed = window.confirm(
                  "📢 Heads up!\n\n" +
                  "When this creator goes live, you'll be @mentioned in a SHARED Discord channel that other users can see.\n\n" +
                  "This means others may see which creators you follow.\n\n" +
                  "Enable notifications for this creator?"
                );
                if (!confirmed) return;
              }
              onToggleNotify(creator.id, !notifyEnabled);
            }}
            style={{
              background: notifyEnabled ? "rgba(88, 101, 242, 0.2)" : "none",
              border: notifyEnabled ? "1px solid rgba(88, 101, 242, 0.5)" : "none",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "1rem",
              padding: "2px 4px",
            }}
            title={notifyEnabled ? "Discord notifications ON - click to disable" : "Enable Discord notifications when live"}
          >
            {notifyEnabled ? "🔔" : "🔕"}
          </button>
        )}
        {onEditCreator && (
          <button
            onClick={() => onEditCreator(creator)}
            title="Edit category, note & links"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: "1rem",
              opacity: 0.7,
            }}
          >
            ✏️
          </button>
        )}
        <button
          onClick={() => onDelete(creator.id)}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "1rem",
            opacity: 0.5,
          }}
        >
          🗑️
        </button>

        <button
          onClick={handleRefreshAvatar}
          disabled={refreshingAvatar}
          title="Refresh avatar from social platforms"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "1rem",
            opacity: refreshingAvatar ? 0.3 : 0.6,
          }}
        >
          {refreshingAvatar ? "🔄" : "🖼️"}
        </button>
      </div>

      <img
        src={avatarSrc}
        alt={creator.name}
        className="creator-avatar"
        onError={() => {
          setAvatarCandidateIndex((prev) => {
            const next = prev + 1;
            if (next < avatarCandidates.length) return next;
            return prev;
          });
        }}
      />
      <h3 className="creator-name">{creator.name}</h3>
      {creator.category && (
        <div
          className="creator-category"
          style={{ fontSize: "0.9rem", color: "#7dd3fc", marginBottom: 4 }}
        >
          {creator.category}
        </div>
      )}
      {creator.tags && creator.tags.length > 0 && (
        <div className="tag-row">
          {creator.tags.map((tag) => (
            <span key={tag} className="tag-pill">
              {tag}
            </span>
          ))}
        </div>
      )}
      <p className="creator-bio">{creator.bio}</p>
      {creator.reason && (
        <div className="creator-reason">
          <span className="reason-label">Reason:</span> {creator.reason}
        </div>
      )}

      <div
        className="health-score"
        title="More followers/live + pinned boosts the score"
      >
        <span>Creator health</span>
        <div className="health-meter">
          <span style={{ width: `${healthScore}%` }} />
        </div>
        <span className="health-label">{healthScore}%</span>
      </div>

      {/* Post counts from creator_updates / creator_mentions */}
      {postCounts && postCounts.total > 0 && (
        <div
          style={{
            display: "flex",
            gap: "12px",
            marginTop: "0.5rem",
            marginBottom: "0.25rem",
            fontSize: "0.8rem",
          }}
        >
          <a
            href={`/fc/#/updates`}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "4px",
              padding: "3px 10px",
              borderRadius: "6px",
              background: "rgba(99, 102, 241, 0.12)",
              border: "1px solid rgba(99, 102, 241, 0.25)",
              color: "#a5b4fc",
              textDecoration: "none",
              fontWeight: 500,
              transition: "filter 0.15s",
            }}
            title="View all posts in Updates feed"
            onMouseEnter={(e) => { e.currentTarget.style.filter = "brightness(1.3)"; }}
            onMouseLeave={(e) => { e.currentTarget.style.filter = ""; }}
          >
            📝 {postCounts.total} post{postCounts.total !== 1 ? "s" : ""}
          </a>
          {postCounts.recent > 0 && (
            <a
              href={`/fc/creator_updates/`}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "3px 10px",
                borderRadius: "6px",
                background: "rgba(34, 197, 94, 0.12)",
                border: "1px solid rgba(34, 197, 94, 0.25)",
                color: "#86efac",
                textDecoration: "none",
                fontWeight: 500,
                transition: "filter 0.15s",
              }}
              title="View recent posts (last 7 days)"
              onMouseEnter={(e) => { e.currentTarget.style.filter = "brightness(1.3)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.filter = ""; }}
            >
              🔥 {postCounts.recent} recent
            </a>
          )}
        </div>
      )}

      <div className="creator-note-wrapper">
        <label htmlFor={`note-${creator.id}`}>Personal note</label>
        <textarea
          id={`note-${creator.id}`}
          className="creator-note"
          value={creator.note || ""}
          placeholder="Add context, reminders, or how you met them"
          onChange={(e) => onUpdateNote(creator.id, e.target.value)}
          rows={3}
        />
        {onSaveNote && (
          <button
            onClick={() => onSaveNote(creator.id, creator.note || "")}
            style={{
              marginTop: "0.5rem",
              padding: "0.4rem 0.8rem",
              fontSize: "0.8rem",
              backgroundColor: "rgba(255, 255, 255, 0.1)",
              border: "1px solid rgba(255, 255, 255, 0.2)",
              borderRadius: "6px",
              color: "white",
              cursor: "pointer",
            }}
          >
            💾 Save
          </button>
        )}
      </div>

      {/* Secondary Notes - Collapsible (Purple theme) */}
      <div
        className="creator-secondary-note-wrapper"
        style={{
          marginTop: "0.75rem",
          background: "rgba(147, 51, 234, 0.08)",
          borderRadius: "8px",
          border: "1px solid rgba(147, 51, 234, 0.25)",
          overflow: "hidden",
        }}
      >
        <button
          type="button"
          onClick={() => setSecondaryNoteExpanded((prev) => !prev)}
          style={{
            width: "100%",
            padding: "0.6rem 0.75rem",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(147, 51, 234, 0.1)",
            border: "none",
            color: "#c4b5fd",
            cursor: "pointer",
            fontSize: "0.85rem",
            fontWeight: 500,
          }}
        >
          <span>Extra notes / links</span>
          <span style={{ opacity: 0.6 }}>{secondaryNoteExpanded ? "▼" : "▶"}</span>
        </button>
        {secondaryNoteExpanded && (
          <div style={{ padding: "0 0.75rem 0.75rem" }}>
            {editingSecondaryNote ? (
              <>
                <textarea
                  value={localSecondaryNote}
                  onChange={(e) => setLocalSecondaryNote(e.target.value)}
                  placeholder="Save favorite content links, important clips, timestamps, etc."
                  rows={4}
                  style={{
                    width: "100%",
                    padding: "0.5rem",
                    background: "rgba(255, 255, 255, 0.05)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "inherit",
                    fontSize: "0.85rem",
                    resize: "vertical",
                  }}
                />
                <div style={{ display: "flex", gap: "8px", marginTop: "0.5rem" }}>
                  <button
                    type="button"
                    onClick={() => {
                      if (onUpdateSecondaryNote) onUpdateSecondaryNote(creator.id, localSecondaryNote);
                      if (onSaveSecondaryNote) onSaveSecondaryNote(creator.id, localSecondaryNote);
                      setEditingSecondaryNote(false);
                    }}
                    style={{
                      padding: "0.4rem 0.8rem",
                      fontSize: "0.8rem",
                      backgroundColor: "rgba(34, 197, 94, 0.2)",
                      border: "1px solid rgba(34, 197, 94, 0.4)",
                      borderRadius: "6px",
                      color: "#86efac",
                      cursor: "pointer",
                    }}
                  >
                    💾 Save
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setLocalSecondaryNote(creator.secondaryNote || "");
                      setEditingSecondaryNote(false);
                    }}
                    style={{
                      padding: "0.4rem 0.8rem",
                      fontSize: "0.8rem",
                      backgroundColor: "rgba(255, 255, 255, 0.1)",
                      border: "1px solid rgba(255, 255, 255, 0.2)",
                      borderRadius: "6px",
                      color: "white",
                      cursor: "pointer",
                    }}
                  >
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
                {creator.secondaryNote ? (
                  <div style={{ marginBottom: "0.5rem" }}>
                    {creator.secondaryNote.split(/\r?\n/).map((line, i) => {
                      const trimmed = line.trim();
                      if (isUrl(trimmed)) {
                        return (
                          <div key={i} style={{ marginBottom: "4px" }}>
                            <a
                              href={trimmed}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ color: "#a78bfa", wordBreak: "break-all" }}
                            >
                              {trimmed}
                            </a>
                          </div>
                        );
                      }
                      return trimmed ? (
                        <div key={i} style={{ marginBottom: "4px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                          {trimmed}
                        </div>
                      ) : null;
                    })}
                  </div>
                ) : (
                  <div style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "0.5rem" }}>
                    No extra notes yet.
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setLocalSecondaryNote(creator.secondaryNote || "");
                    setEditingSecondaryNote(true);
                  }}
                  style={{
                    padding: "0.4rem 0.8rem",
                    fontSize: "0.8rem",
                    backgroundColor: "rgba(255, 255, 255, 0.1)",
                    border: "1px solid rgba(255, 255, 255, 0.2)",
                    borderRadius: "6px",
                    color: "white",
                    cursor: "pointer",
                  }}
                >
                  ✏️ Edit
                </button>
              </>
            )}
          </div>
        )}
      </div>

      <div className="creator-last-checked">
        {formatRelativeTime(creator.lastChecked)}
      </div>

      <div className="accounts-list">
        {creator.accounts.map((account) => {
          const summaryEntry = accountSummaries[account.id];
          const tooltipMessage =
            summaryEntry?.status === "loading"
              ? "Gathering summary..."
              : summaryEntry?.text ||
              "Hover to fetch a brief public summary of this profile.";
          return (
            <div
              key={account.id}
              className={`account-link ${account.platform} ${account.accountStatus === 'not_found' || account.accountStatus === 'banned'
                  ? `status-${account.accountStatus}`
                  : ''
                }`}
              onMouseEnter={() => handleAccountHover(account)}
            >
              <a
                href={account.url}
                target="_blank"
                rel="noopener noreferrer"
                onFocus={() => handleAccountHover(account)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  textDecoration: "none",
                  color: "inherit",
                }}
              >
                {getPlatformIcon(account.platform)}
                <div className="account-info">
                  <div
                    style={{ display: "flex", alignItems: "center", gap: "4px" }}
                  >
                    <span>
                      {account.platform === "other"
                        ? account.username
                        : `@${account.username}`}
                    </span>
                    {account.isLive && <div className="account-live-dot"></div>}
                    {(account.accountStatus === 'not_found' ||
                      account.accountStatus === 'banned' ||
                      account.accountStatus === 'error') && (
                        <span className={`account-status-badge ${account.accountStatus}`}>
                          {account.accountStatus === 'not_found' ? '404' :
                            account.accountStatus === 'banned' ? 'BANNED' : 'ERROR'}
                        </span>
                      )}
                  </div>
                  {account.followers && (
                    <span className="follower-count">
                      {account.followers} followers
                    </span>
                  )}
                </div>
              </a>
              <button
                className="btn-remove-account"
                onClick={(e) => {
                  e.preventDefault();
                  onRemoveAccount(creator.id, account.id);
                }}
                title="Remove account"
              >
                ✕
              </button>
              <div
                className="account-summary-tooltip"
                data-state={summaryEntry?.status || "idle"}
              >
                {tooltipMessage}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CreatorCard;
