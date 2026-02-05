import { useState } from "react";
import type { Creator, SocialAccount } from "../types";
import type { Platform } from "../types";
import { parseSocialUrl } from "../utils/parseSocialUrl";
import AvatarSelectorModal from "./AvatarSelectorModal";

const PLATFORMS: Platform[] = ["youtube", "tiktok", "instagram", "kick", "twitch", "spotify", "other"];

type Row = { id: string; platform: Platform; username: string; url: string; checkLive: boolean };

interface EditCreatorModalProps {
  creator: Creator;
  categories: string[];
  onSave: (updates: { category?: string; accounts: SocialAccount[]; note?: string; isLiveStreamer?: boolean; avatarUrl?: string; selectedAvatarSource?: string }) => void;
  onClose: () => void;
}

const defaultCheckLive = (platform: Platform, isLiveStreamer: boolean): boolean =>
  isLiveStreamer && (platform === "kick" || platform === "twitch");

export default function EditCreatorModal({ creator, categories, onSave, onClose }: EditCreatorModalProps) {
  const hasKickOrTwitch = creator.accounts.some((a) => a.platform === "kick" || a.platform === "twitch");
  const [isLiveStreamer, setIsLiveStreamer] = useState(
    creator.isLiveStreamer ?? hasKickOrTwitch
  );
  const [category, setCategory] = useState(creator.category ?? "");
  const [note, setNote] = useState(creator.note ?? creator.reason ?? "");
  const [rows, setRows] = useState<Row[]>(
    creator.accounts.map((a) => ({
      id: a.id,
      platform: a.platform,
      username: a.username,
      url: a.url,
      checkLive: a.checkLive ?? defaultCheckLive(a.platform, creator.isLiveStreamer ?? hasKickOrTwitch),
    }))
  );
  const [pasteUrls, setPasteUrls] = useState("");
  const [showAvatarSelector, setShowAvatarSelector] = useState(false);
  const [selectedAvatarUrl, setSelectedAvatarUrl] = useState(creator.avatarUrl || "");
  const [selectedAvatarSource, setSelectedAvatarSource] = useState(creator.selectedAvatarSource || "");

  const updateRow = (index: number, field: "platform" | "username" | "url", value: string) => {
    setRows((prev) =>
      prev.map((r, i) => (i === index ? { ...r, [field]: value } : r))
    );
  };

  const setRowCheckLive = (index: number, checkLive: boolean) => {
    setRows((prev) => prev.map((r, i) => (i === index ? { ...r, checkLive } : r)));
  };

  const addRow = () => {
    setRows((prev) => [
      ...prev,
      { id: crypto.randomUUID(), platform: "other", username: "", url: "", checkLive: false },
    ]);
  };

  const removeRow = (index: number) => {
    setRows((prev) => prev.filter((_, i) => i !== index));
  };

  const addFromPastedUrls = () => {
    const lines = pasteUrls.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    const newRows: Row[] = [];
    for (const line of lines) {
      const parsed = parseSocialUrl(line);
      if (parsed) {
        newRows.push({
          id: crypto.randomUUID(),
          platform: parsed.platform,
          username: parsed.username,
          url: parsed.url,
          checkLive: defaultCheckLive(parsed.platform, isLiveStreamer),
        });
      }
    }
    if (newRows.length > 0) {
      setRows((prev) => [...prev, ...newRows]);
      setPasteUrls("");
    }
  };

  const handleAvatarSelect = (avatarUrl: string, source: string) => {
    setSelectedAvatarUrl(avatarUrl);
    setSelectedAvatarSource(source);
  };

  const handleSave = () => {
    const accounts: SocialAccount[] = rows
      .filter((r) => r.url.trim() !== "")
      .map((r) => {
        let username = r.username.trim();
        if (!username && r.url.trim()) {
          try {
            const path = new URL(r.url).pathname.replace(/\/$/, "");
            username = path.split("/").filter(Boolean).pop() || "user";
          } catch {
            username = "user";
          }
        }
        return {
          id: r.id,
          platform: r.platform,
          username: username || "user",
          url: r.url.trim(),
          checkLive: r.checkLive,
        };
      });
    onSave({
      category: category.trim() || undefined,
      accounts,
      note: note.trim() || undefined,
      isLiveStreamer,
      avatarUrl: selectedAvatarUrl !== creator.avatarUrl ? selectedAvatarUrl : undefined,
      selectedAvatarSource: selectedAvatarSource !== creator.selectedAvatarSource ? selectedAvatarSource : undefined,
    });
    onClose();
  };

  return (
    <div
      className="edit-creator-modal-overlay"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
      }}
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className="edit-creator-modal"
        style={{
          background: "var(--card-bg)",
          borderRadius: "12px",
          border: "1px solid var(--glass-border)",
          maxWidth: "560px",
          width: "95%",
          maxHeight: "90vh",
          overflow: "auto",
          padding: "1.25rem",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", marginBottom: "1rem" }}>
          <img
            src={selectedAvatarUrl || creator.avatarUrl}
            alt={creator.name}
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "50%",
              objectFit: "cover",
              border: "2px solid rgba(255,255,255,0.2)",
            }}
            onError={(e) => {
              e.currentTarget.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(creator.name)}`;
            }}
          />
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, fontSize: "1.25rem" }}>Edit {creator.name}</h2>
            {selectedAvatarSource && (
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "2px" }}>
                Avatar from: {selectedAvatarSource}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={() => setShowAvatarSelector(true)}
            style={{
              padding: "6px 12px",
              backgroundColor: "rgba(76, 175, 80, 0.2)",
              border: "1px solid rgba(76, 175, 80, 0.4)",
              borderRadius: "6px",
              color: "#4CAF50",
              cursor: "pointer",
              fontSize: "0.85rem",
              fontWeight: "500",
            }}
          >
            Change Avatar
          </button>
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "4px", fontSize: "0.9rem" }}>Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            style={{
              width: "100%",
              padding: "8px",
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: "6px",
              color: "var(--text)",
            }}
          >
            <option value="" style={{ background: "var(--card-bg)", color: "var(--text)" }}>— Select —</option>
            {categories.map((c) => (
              <option key={c} value={c} style={{ background: "var(--card-bg)", color: "var(--text)" }}>{c}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontSize: "0.9rem" }}>
            <input
              type="checkbox"
              checked={isLiveStreamer}
              onChange={(e) => setIsLiveStreamer(e.target.checked)}
              style={{ width: "18px", height: "18px" }}
            />
            <span>Live streamer</span>
          </label>
          <p style={{ margin: "4px 0 0 26px", fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Mark which platforms to check for live status below. Your choice is saved per creator and does not affect other users.
          </p>
        </div>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "4px", fontSize: "0.9rem" }}>Personal note</label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Your note about this creator..."
            rows={2}
            style={{
              width: "100%",
              padding: "8px",
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: "6px",
              color: "inherit",
              fontSize: "0.9rem",
              resize: "vertical",
            }}
          />
        </div>

        <div style={{ marginBottom: "0.5rem", fontWeight: 600, fontSize: "0.95rem" }}>Social links</div>
        <p style={{ margin: "0 0 8px", fontSize: "0.85rem", color: "var(--text-muted)" }}>
          One link per row.{" "}
          {isLiveStreamer ? (
            <>Tick &quot;Check for live&quot; for platforms you want live status checked (e.g. Starfireara: TikTok; wtfpreston: Kick/Twitch).</>
          ) : (
            <span style={{ color: "rgba(250, 204, 21, 0.8)" }}>
              Enable &quot;Live streamer&quot; above to select which platforms to check for live status.
            </span>
          )}{" "}
          You can also paste URLs below (one per line).
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "1rem" }}>
          {rows.map((row, index) => (
            <div
              key={row.id}
              style={{
                display: "grid",
                gridTemplateColumns: "32px 90px 1fr 2fr auto",
                gap: "8px",
                alignItems: "center",
              }}
            >
              <label
                style={{
                  display: "flex",
                  alignItems: "center",
                  cursor: isLiveStreamer ? "pointer" : "not-allowed",
                  flexShrink: 0,
                  opacity: isLiveStreamer ? 1 : 0.4,
                }}
                title={isLiveStreamer ? "Check this account for live status" : "Enable 'Live streamer' above to check platforms for live status"}
              >
                <input
                  type="checkbox"
                  checked={isLiveStreamer && row.checkLive}
                  onChange={(e) => setRowCheckLive(index, e.target.checked)}
                  disabled={!isLiveStreamer}
                  style={{ width: "16px", height: "16px", cursor: isLiveStreamer ? "pointer" : "not-allowed" }}
                />
              </label>
              <select
                value={row.platform}
                onChange={(e) => updateRow(index, "platform", e.target.value as Platform)}
                style={{
                  padding: "6px 8px",
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "6px",
                  color: "var(--text)",
                  fontSize: "0.85rem",
                }}
              >
                {PLATFORMS.map((p) => (
                  <option key={p} value={p} style={{ background: "var(--card-bg)", color: "var(--text)" }}>{p}</option>
                ))}
              </select>
              <input
                type="text"
                value={row.username}
                onChange={(e) => updateRow(index, "username", e.target.value)}
                placeholder="Username"
                style={{
                  padding: "6px 8px",
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "6px",
                  color: "inherit",
                  fontSize: "0.85rem",
                }}
              />
              <input
                type="url"
                value={row.url}
                onChange={(e) => updateRow(index, "url", e.target.value)}
                placeholder="https://..."
                style={{
                  padding: "6px 8px",
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.2)",
                  borderRadius: "6px",
                  color: "inherit",
                  fontSize: "0.85rem",
                }}
              />
              <button
                type="button"
                onClick={() => removeRow(index)}
                title="Remove link"
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: "4px",
                  fontSize: "1rem",
                  opacity: 0.7,
                }}
              >
                ✕
              </button>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={addRow}
          className="btn-secondary"
          style={{ marginBottom: "1rem" }}
        >
          + Add link
        </button>

        <div style={{ marginBottom: "1rem" }}>
          <label style={{ display: "block", marginBottom: "4px", fontSize: "0.85rem" }}>
            Paste URLs (one per line) to add quickly
          </label>
          <textarea
            value={pasteUrls}
            onChange={(e) => setPasteUrls(e.target.value)}
            placeholder={"https://tiktok.com/@user\nhttps://youtube.com/@channel"}
            rows={3}
            style={{
              width: "100%",
              padding: "8px",
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.2)",
              borderRadius: "6px",
              color: "inherit",
              fontSize: "0.85rem",
              resize: "vertical",
            }}
          />
          <button type="button" onClick={addFromPastedUrls} className="btn-secondary" style={{ marginTop: "6px" }}>
            Add from pasted URLs
          </button>
        </div>

        <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
          <button type="button" onClick={onClose} className="btn-secondary">
            Cancel
          </button>
          <button type="button" onClick={handleSave} className="btn-add" style={{ padding: "8px 16px" }}>
            Apply changes
          </button>
        </div>
      </div>

      {showAvatarSelector && (
        <AvatarSelectorModal
          creator={creator}
          currentAvatarUrl={selectedAvatarUrl || creator.avatarUrl}
          onSelect={handleAvatarSelect}
          onClose={() => setShowAvatarSelector(false)}
        />
      )}
    </div>
  );
}
