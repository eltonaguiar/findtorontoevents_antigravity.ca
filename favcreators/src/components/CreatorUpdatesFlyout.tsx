import React, { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import {
  getStatusUpdates,
  formatContentAge,
  getPlatformDisplayName,
  getUpdateTypeLabel,
  type CreatorStatusUpdate,
} from "../utils/statusUpdates";

interface CreatorUpdatesFlyoutProps {
  creatorId: string;
  creatorName: string;
  anchorRect: DOMRect | null;
  onClose: () => void;
}

const platformEmoji: Record<string, string> = {
  youtube: "\u{1F4FA}",
  tiktok: "\u{1F3B5}",
  twitter: "\u{1F426}",
  instagram: "\u{1F4F7}",
  twitch: "\u{1F3AE}",
  kick: "\u{1F3AE}",
  reddit: "\u{1F4AC}",
  spotify: "\u{1F3A7}",
};

const CreatorUpdatesFlyout: React.FC<CreatorUpdatesFlyoutProps> = ({
  creatorId,
  creatorName,
  anchorRect,
  onClose,
}) => {
  const [updates, setUpdates] = useState<CreatorStatusUpdate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const flyoutRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getStatusUpdates({ creator_id: creatorId, limit: 10 })
      .then((res) => {
        if (cancelled) return;
        if (res.ok) {
          setUpdates(res.updates);
        } else {
          setError("Failed to load updates");
        }
        setLoading(false);
      })
      .catch(() => {
        if (cancelled) return;
        setError("Failed to load updates");
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [creatorId]);

  // Click outside to dismiss
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (
        flyoutRef.current &&
        !flyoutRef.current.contains(e.target as Node)
      ) {
        onClose();
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    // Delay adding the listener so the opening click doesn't immediately close it
    const timer = setTimeout(() => {
      document.addEventListener("mousedown", handleClick);
      document.addEventListener("keydown", handleKey);
    }, 50);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [onClose]);

  // Calculate position
  let top = 100;
  let left = 100;
  if (anchorRect) {
    top = anchorRect.bottom + 8;
    left = anchorRect.left - 280;
    // Keep within viewport
    if (left < 12) left = 12;
    if (left + 340 > window.innerWidth) left = window.innerWidth - 352;
    if (top + 420 > window.innerHeight) {
      top = anchorRect.top - 428;
      if (top < 12) top = 12;
    }
  }

  const flyout = (
    <div
      ref={flyoutRef}
      className="creator-updates-flyout"
      style={{ top, left }}
    >
      <div className="creator-updates-flyout-header">
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{ fontSize: "1.1rem" }}>📋</span>
          <span
            style={{
              fontWeight: 700,
              fontSize: "0.9rem",
              color: "#e2e8f0",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              maxWidth: "220px",
            }}
          >
            {creatorName}
          </span>
        </div>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#94a3b8",
            cursor: "pointer",
            fontSize: "1.2rem",
            padding: "2px 6px",
            lineHeight: 1,
          }}
          title="Close"
        >
          &times;
        </button>
      </div>

      <div className="creator-updates-flyout-body">
        {loading && (
          <div
            style={{
              textAlign: "center",
              padding: "2rem 1rem",
              color: "#94a3b8",
              fontSize: "0.85rem",
            }}
          >
            <div
              style={{
                display: "inline-block",
                width: "20px",
                height: "20px",
                border: "2px solid rgba(99,102,241,0.3)",
                borderTopColor: "#6366f1",
                borderRadius: "50%",
                animation: "creatorFlyoutSpin 0.6s linear infinite",
                marginBottom: "8px",
              }}
            />
            <div>Loading updates...</div>
          </div>
        )}

        {error && !loading && (
          <div
            style={{
              textAlign: "center",
              padding: "1.5rem 1rem",
              color: "#f87171",
              fontSize: "0.85rem",
            }}
          >
            {error}
          </div>
        )}

        {!loading && !error && updates.length === 0 && (
          <div
            style={{
              textAlign: "center",
              padding: "1.5rem 1rem",
              color: "#64748b",
              fontSize: "0.85rem",
            }}
          >
            No updates tracked yet for this creator.
            <br />
            <span style={{ fontSize: "0.75rem", marginTop: "4px", display: "inline-block" }}>
              Check their live status to start tracking.
            </span>
          </div>
        )}

        {!loading &&
          !error &&
          updates.map((u) => (
            <a
              key={u.id}
              href={u.content_url || u.account_url || "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="creator-update-item"
              style={{ display: "block", textDecoration: "none", color: "inherit" }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  marginBottom: "4px",
                }}
              >
                <span style={{ fontSize: "0.85rem" }}>
                  {platformEmoji[u.platform] || "\u{1F310}"}
                </span>
                <span
                  style={{
                    fontSize: "0.75rem",
                    color: "#a5b4fc",
                    fontWeight: 600,
                  }}
                >
                  {getPlatformDisplayName(u.platform)}
                </span>
                <span
                  style={{
                    fontSize: "0.65rem",
                    padding: "1px 6px",
                    borderRadius: "4px",
                    background: u.is_live
                      ? "rgba(239, 68, 68, 0.2)"
                      : "rgba(255, 255, 255, 0.06)",
                    color: u.is_live ? "#f87171" : "#94a3b8",
                    fontWeight: 500,
                  }}
                >
                  {u.is_live ? "LIVE" : getUpdateTypeLabel(u.update_type)}
                </span>
                <span
                  style={{
                    fontSize: "0.65rem",
                    color: "#64748b",
                    marginLeft: "auto",
                  }}
                >
                  {formatContentAge(u.content_published_at || u.last_updated)}
                </span>
              </div>

              {u.content_title && (
                <div
                  style={{
                    fontSize: "0.8rem",
                    color: "#cbd5e1",
                    lineHeight: 1.3,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                  }}
                >
                  {u.content_title}
                </div>
              )}

              {u.content_thumbnail && (
                <img
                  src={u.content_thumbnail}
                  alt=""
                  style={{
                    width: "100%",
                    height: "auto",
                    maxHeight: "120px",
                    objectFit: "cover",
                    borderRadius: "6px",
                    marginTop: "6px",
                    opacity: 0.9,
                  }}
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = "none";
                  }}
                />
              )}

              {u.viewer_count > 0 && (
                <div
                  style={{
                    fontSize: "0.7rem",
                    color: "#64748b",
                    marginTop: "4px",
                  }}
                >
                  {u.viewer_count.toLocaleString()} viewers
                </div>
              )}
            </a>
          ))}
      </div>

      {!loading && updates.length > 0 && (
        <div
          style={{
            padding: "8px 12px",
            borderTop: "1px solid rgba(255,255,255,0.06)",
            textAlign: "center",
            flexShrink: 0,
          }}
        >
          <a
            href="/fc/#/updates"
            style={{
              fontSize: "0.75rem",
              color: "#818cf8",
              textDecoration: "none",
              fontWeight: 500,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.textDecoration = "underline";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.textDecoration = "none";
            }}
          >
            View all updates &rarr;
          </a>
        </div>
      )}
    </div>
  );

  return createPortal(flyout, document.body);
};

export default CreatorUpdatesFlyout;
