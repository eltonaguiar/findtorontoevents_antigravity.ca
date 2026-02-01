import { useState } from "react";
import type { Creator } from "./types";
import { ensureAvatarForCreators } from "./utils/avatar";

// Dummy: Replace with real fetch logic for last post and live status
async function fetchLastPostAndLiveStatus(creator: Creator) {
  // Simulate fetching last post and live status
  return {
    lastPost: {
      platform: creator.accounts[0]?.platform || "unknown",
      url: creator.accounts[0]?.url || "",
      content: "This is a simulated last post for demo purposes.",
      timestamp: new Date().toLocaleString(),
    },
    isLive: Math.random() > 0.5 ? true : false,
  };
}

export default function LastDetectedContentPage() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const creators = ensureAvatarForCreators([]); // Replace with real creators list if needed

  async function handleCheck() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      // Find creator by name (case-insensitive)
      const creator = creators.find(c => c.name.toLowerCase() === input.toLowerCase());
      if (!creator) throw new Error("Creator not found");
      const data = await fetchLastPostAndLiveStatus(creator);
      setResult(data);
    } catch (e: any) {
      setError(e.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 32, maxWidth: 600, margin: "0 auto" }}>
      <h2>Last Detected Content & Live Status</h2>
      <p>Enter a creator's name to check their last post and live status.</p>
      <input
        value={input}
        onChange={e => setInput(e.target.value)}
        placeholder="Enter creator name (e.g. WTFPreston)"
        style={{ padding: 8, width: "100%", marginBottom: 12 }}
      />
      <button onClick={handleCheck} disabled={loading || !input} style={{ padding: 8 }}>
        {loading ? "Checking..." : "Check"}
      </button>
      {error && <div style={{ color: "red", marginTop: 12 }}>{error}</div>}
      {result && (
        <div style={{ marginTop: 24, background: "#222", padding: 16, borderRadius: 8 }}>
          <h3>Last Post</h3>
          <div>Platform: {result.lastPost.platform}</div>
          <div>URL: <a href={result.lastPost.url} target="_blank" rel="noopener noreferrer">{result.lastPost.url}</a></div>
          <div>Content: {result.lastPost.content}</div>
          <div>Timestamp: {result.lastPost.timestamp}</div>
          <h3 style={{ marginTop: 16 }}>Live Status</h3>
          <div style={{ color: result.isLive ? "#0f0" : "#f44" }}>
            {result.isLive ? "LIVE NOW" : "Offline"}
          </div>
        </div>
      )}
    </div>
  );
}
