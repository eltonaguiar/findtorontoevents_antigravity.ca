export const extractYoutubeUsername = (url: string): string | null => {
  try {
    const parsed = new URL(url);
    if (!parsed.hostname.includes("youtube.com")) return null;
    const trimmedPath = parsed.pathname.replace(/^\/+/, "");
    if (!trimmedPath) {
      const directId = parsed.searchParams.get("v");
      return directId ? directId : null;
    }
    const candidate = trimmedPath.split("/")[0];
    if (candidate.startsWith("@")) return candidate.slice(1);
    if (candidate.startsWith("channel/")) return candidate.replace("channel/", "");
    if (candidate.startsWith("c/")) return candidate.replace("c/", "");
    return candidate;
  } catch {
    return null;
  }
};
