import type { Platform } from "../types";

/** Parse a pasted social URL (e.g. https://www.tiktok.com/@user) into platform + username + url. */
export function parseSocialUrl(input: string): { platform: Platform; username: string; url: string } | null {
  const trimmed = input.trim();
  if (!trimmed) return null;
  let url: URL;
  try {
    url = new URL(trimmed.startsWith("http") ? trimmed : "https://" + trimmed);
  } catch {
    return null;
  }
  const host = url.hostname.toLowerCase().replace(/^www\./, "");
  const path = url.pathname.replace(/\/$/, "").split("?")[0];

  if (host === "tiktok.com" && path.startsWith("/@")) {
    const username = path.slice(2).split("/")[0] || "";
    if (!username) return null;
    return { platform: "tiktok", username, url: `https://www.tiktok.com/@${username}` };
  }
  if (host === "youtube.com" || host === "youtu.be") {
    let username = "";
    if (path.startsWith("/@")) username = path.slice(2).split("/")[0] || "";
    else if (path.startsWith("/channel/")) username = path.split("/")[2] || "";
    else if (path.startsWith("/c/")) username = path.slice(3).split("/")[0] || "";
    if (!username) return null;
    const canonical = host === "youtu.be" ? `https://youtube.com/@${username}` : url.toString();
    return { platform: "youtube", username, url: canonical };
  }
  if (host === "instagram.com" && path.length > 1) {
    const username = path.slice(1).split("/")[0] || "";
    if (!username) return null;
    return { platform: "instagram", username, url: `https://instagram.com/${username}` };
  }
  if (host === "kick.com" && path.length > 1) {
    const username = path.slice(1).split("/")[0] || "";
    if (!username) return null;
    return { platform: "kick", username, url: `https://kick.com/${username}` };
  }
  if (host === "twitch.tv" && path.length > 1) {
    const username = path.slice(1).split("/")[0] || "";
    if (!username) return null;
    return { platform: "twitch", username, url: `https://twitch.tv/${username}` };
  }
  return null;
}
