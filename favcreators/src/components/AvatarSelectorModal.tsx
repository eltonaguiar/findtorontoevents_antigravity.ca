import { useState, useEffect } from "react";
import type { Creator } from "../types";
import type { AvatarOption } from "../utils/multiAvatarFetcher";
import { fetchAllAvatars } from "../utils/multiAvatarFetcher";

interface AvatarSelectorModalProps {
    creator: Creator;
    currentAvatarUrl: string;
    onSelect: (avatarUrl: string, source: string) => void;
    onClose: () => void;
}

export default function AvatarSelectorModal({
    creator,
    currentAvatarUrl,
    onSelect,
    onClose,
}: AvatarSelectorModalProps) {
    const [avatarOptions, setAvatarOptions] = useState<AvatarOption[]>([]);
    const [loading, setLoading] = useState(false);
    const [customUrl, setCustomUrl] = useState("");
    const [selectedUrl, setSelectedUrl] = useState(currentAvatarUrl);

    // Fetch avatars on mount
    useEffect(() => {
        loadAvatars();
    }, []);

    const loadAvatars = async () => {
        setLoading(true);
        try {
            const options = await fetchAllAvatars(
                creator.accounts,
                creator.name,
                currentAvatarUrl,
            );
            setAvatarOptions(options);
        } catch (error) {
            console.error("Failed to fetch avatar options:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleSelect = (url: string, source: string) => {
        setSelectedUrl(url);
        onSelect(url, source);
        onClose();
    };

    const handleCustomUrlSubmit = () => {
        if (customUrl.trim() && customUrl.startsWith("http")) {
            handleSelect(customUrl.trim(), "custom_url");
        }
    };

    return (
        <div
            className="modal-overlay"
            onClick={onClose}
            style={{
                position: "fixed",
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: "rgba(0, 0, 0, 0.7)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 1000,
            }}
        >
            <div
                className="modal-content"
                onClick={(e) => e.stopPropagation()}
                style={{
                    backgroundColor: "#1a1a1a",
                    borderRadius: "12px",
                    padding: "24px",
                    maxWidth: "600px",
                    width: "90%",
                    maxHeight: "80vh",
                    overflow: "auto",
                    border: "1px solid #333",
                }}
            >
                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: "20px",
                    }}
                >
                    <h2 style={{ margin: 0, fontSize: "20px", color: "#fff" }}>
                        Select Avatar for {creator.name}
                    </h2>
                    <button
                        onClick={onClose}
                        style={{
                            background: "none",
                            border: "none",
                            color: "#999",
                            fontSize: "24px",
                            cursor: "pointer",
                            padding: "0 8px",
                        }}
                    >
                        ×
                    </button>
                </div>

                {loading ? (
                    <div style={{ textAlign: "center", padding: "40px", color: "#999" }}>
                        <div className="spinner" style={{ marginBottom: "12px" }}>
                            Loading avatars...
                        </div>
                        <div style={{ fontSize: "12px", color: "#666", marginTop: "8px" }}>
                            This may take up to 1 minute
                        </div>
                    </div>
                ) : (
                    <>
                        {avatarOptions.length === 0 ? (
                            <div
                                style={{ textAlign: "center", padding: "40px", color: "#999" }}
                            >
                                No avatar options found. Try adding social media accounts or use
                                a custom URL below.
                            </div>
                        ) : (
                            <div
                                style={{
                                    display: "grid",
                                    gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))",
                                    gap: "16px",
                                    marginBottom: "24px",
                                }}
                            >
                                {avatarOptions.map((option, index) => (
                                    <div
                                        key={index}
                                        onClick={() => handleSelect(option.url, option.source)}
                                        style={{
                                            cursor: "pointer",
                                            border:
                                                selectedUrl === option.url
                                                    ? "3px solid #4CAF50"
                                                    : "2px solid #333",
                                            borderRadius: "8px",
                                            padding: "8px",
                                            backgroundColor: "#222",
                                            transition: "all 0.2s",
                                            position: "relative",
                                        }}
                                        onMouseEnter={(e) => {
                                            if (selectedUrl !== option.url) {
                                                e.currentTarget.style.borderColor = "#555";
                                            }
                                        }}
                                        onMouseLeave={(e) => {
                                            if (selectedUrl !== option.url) {
                                                e.currentTarget.style.borderColor = "#333";
                                            }
                                        }}
                                    >
                                        <img
                                            src={option.url}
                                            alt={`${option.platform} avatar`}
                                            style={{
                                                width: "100%",
                                                height: "100px",
                                                objectFit: "cover",
                                                borderRadius: "4px",
                                                marginBottom: "8px",
                                            }}
                                            onError={(e) => {
                                                e.currentTarget.src =
                                                    "https://ui-avatars.com/api/?name=" +
                                                    encodeURIComponent(creator.name);
                                            }}
                                        />
                                        <div
                                            style={{
                                                fontSize: "11px",
                                                color: "#999",
                                                textAlign: "center",
                                                textTransform: "capitalize",
                                            }}
                                        >
                                            {option.platform}
                                        </div>
                                        {option.isPrimary && (
                                            <div
                                                style={{
                                                    position: "absolute",
                                                    top: "4px",
                                                    right: "4px",
                                                    backgroundColor: "#4CAF50",
                                                    color: "#fff",
                                                    fontSize: "10px",
                                                    padding: "2px 6px",
                                                    borderRadius: "4px",
                                                    fontWeight: "bold",
                                                }}
                                            >
                                                CURRENT
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}

                        <div style={{ marginTop: "24px" }}>
                            <label
                                style={{
                                    display: "block",
                                    marginBottom: "8px",
                                    color: "#ccc",
                                    fontSize: "14px",
                                }}
                            >
                                Or enter a custom URL:
                            </label>
                            <div style={{ display: "flex", gap: "8px" }}>
                                <input
                                    type="text"
                                    value={customUrl}
                                    onChange={(e) => setCustomUrl(e.target.value)}
                                    placeholder="https://example.com/avatar.jpg"
                                    style={{
                                        flex: 1,
                                        padding: "10px",
                                        backgroundColor: "#222",
                                        border: "1px solid #333",
                                        borderRadius: "6px",
                                        color: "#fff",
                                        fontSize: "14px",
                                    }}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter") {
                                            handleCustomUrlSubmit();
                                        }
                                    }}
                                />
                                <button
                                    onClick={handleCustomUrlSubmit}
                                    disabled={!customUrl.trim() || !customUrl.startsWith("http")}
                                    style={{
                                        padding: "10px 20px",
                                        backgroundColor: "#4CAF50",
                                        color: "#fff",
                                        border: "none",
                                        borderRadius: "6px",
                                        cursor: "pointer",
                                        fontSize: "14px",
                                        fontWeight: "500",
                                        opacity:
                                            !customUrl.trim() || !customUrl.startsWith("http")
                                                ? 0.5
                                                : 1,
                                    }}
                                >
                                    Use URL
                                </button>
                            </div>
                        </div>

                        <div style={{ marginTop: "16px", textAlign: "right" }}>
                            <button
                                onClick={loadAvatars}
                                style={{
                                    padding: "8px 16px",
                                    backgroundColor: "#333",
                                    color: "#fff",
                                    border: "none",
                                    borderRadius: "6px",
                                    cursor: "pointer",
                                    fontSize: "13px",
                                    marginRight: "8px",
                                }}
                            >
                                🔄 Refresh
                            </button>
                            <button
                                onClick={onClose}
                                style={{
                                    padding: "8px 16px",
                                    backgroundColor: "#555",
                                    color: "#fff",
                                    border: "none",
                                    borderRadius: "6px",
                                    cursor: "pointer",
                                    fontSize: "13px",
                                }}
                            >
                                Cancel
                            </button>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
