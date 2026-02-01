/**
 * Test script for Avatar Grabber V4
 * Run with: npx tsx test-v4-scraper.ts
 */

import { grabAvatarV4, type V4ScraperResult } from "./src/utils/avatarGrabberV4";
import type { SocialAccount } from "./src/types";

// All creators from INITIAL_DATA in App.tsx
const CREATORS: Array<{ name: string; accounts: SocialAccount[] }> = [
  {
    name: "WTFPreston",
    accounts: [
      { id: "wtfpreston-tiktok", platform: "tiktok", username: "wtfprestonlive", url: "https://www.tiktok.com/@wtfprestonlive", followers: "330K", lastChecked: 0 },
      { id: "wtfpreston-youtube", platform: "youtube", username: "wtfprestonlive", url: "https://www.youtube.com/@wtfprestonlive", lastChecked: 0 },
      { id: "wtfpreston-instagram", platform: "instagram", username: "wtfprestonlive", url: "https://www.instagram.com/wtfprestonlive", lastChecked: 0 },
      { id: "wtfpreston-spotify", platform: "spotify" as any, username: "wtfprestonlive", url: "https://open.spotify.com/artist/5Ho2sjbNmEkALWz8hbNBUH", lastChecked: 0 },
    ],
  },
  {
    name: "Clavicular",
    accounts: [
      { id: "clavicular-kick", platform: "kick", username: "clavicular", url: "https://kick.com/clavicular", lastChecked: 0 },
      { id: "clavicular-twitch", platform: "twitch", username: "clavicular", url: "https://www.twitch.tv/clavicular", lastChecked: 0 },
    ],
  },
  {
    name: "Zarthestar",
    accounts: [
      { id: "zarthestar-tiktok", platform: "tiktok", username: "zarthestarcomedy", url: "https://www.tiktok.com/@zarthestarcomedy", followers: "125K", lastChecked: 0 },
      { id: "zarthestar-instagram", platform: "instagram", username: "zar.the.star", url: "https://www.instagram.com/zar.the.star/?hl=en", followers: "45K", lastChecked: 0 },
      { id: "zarthestar-twitch", platform: "twitch", username: "zarthestar", url: "https://twitch.tv/zarthestar", followers: "2.3K", lastChecked: 0 },
      { id: "zarthestar-youtube", platform: "youtube", username: "zarthestarcomedy", url: "https://www.youtube.com/@zarthestarcomedy", followers: "800", lastChecked: 0 },
    ],
  },
  {
    name: "Adin Ross",
    accounts: [
      { id: "3a", platform: "kick", username: "adinross", url: "https://kick.com/adinross", followers: "1.9M", lastChecked: 0 },
      { id: "3b", platform: "youtube", username: "adinross", url: "https://youtube.com/@adinross", followers: "4.6M", lastChecked: 0 },
    ],
  },
  {
    name: "Starfireara",
    accounts: [
      { id: "6b", platform: "tiktok", username: "starfireara", url: "https://www.tiktok.com/@starfireara", followers: "247.3K", lastChecked: 0 },
    ],
  },
];

async function runTest() {
  console.log("=".repeat(80));
  console.log("AVATAR GRABBER V4 - FAILOVER SCRAPER TEST");
  console.log("=".repeat(80));
  console.log(`Testing ${CREATORS.length} creators...\n`);

  const results: V4ScraperResult[] = [];

  for (const creator of CREATORS) {
    console.log(`\n${"─".repeat(60)}`);
    console.log(`Scraping: ${creator.name}`);
    console.log(`Accounts: ${creator.accounts.map(a => `${a.platform}:${a.username}`).join(", ")}`);
    console.log(`${"─".repeat(60)}`);

    const startTime = Date.now();
    const result = await grabAvatarV4(creator.accounts, creator.name);
    const duration = Date.now() - startTime;

    results.push(result);

    console.log(`\nResult for ${creator.name}:`);
    console.log(`  Strategy: ${result.strategy}`);
    console.log(`  Platform: ${result.platform || "N/A"}`);
    console.log(`  Avatar URL: ${result.avatarUrl}`);
    console.log(`  Duration: ${duration}ms`);
    console.log(`  Attempts: ${result.attempts.length}`);
    if (result.error) {
      console.log(`  Warning: ${result.error}`);
    }

    // Small delay between creators
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  // Summary report
  console.log("\n" + "=".repeat(80));
  console.log("SUMMARY REPORT");
  console.log("=".repeat(80));

  const realAvatars = results.filter(r => !r.strategy.includes("UI-Avatars") && !r.strategy.includes("DiceBear"));
  const generatedAvatars = results.filter(r => r.strategy.includes("UI-Avatars") || r.strategy.includes("DiceBear"));

  console.log(`\nTotal Creators: ${results.length}`);
  console.log(`Real Avatars Found: ${realAvatars.length}`);
  console.log(`Generated Fallbacks: ${generatedAvatars.length}`);
  console.log(`Success Rate: ${((realAvatars.length / results.length) * 100).toFixed(1)}%`);

  console.log("\n" + "─".repeat(80));
  console.log("DETAILED RESULTS:");
  console.log("─".repeat(80));

  for (const result of results) {
    const status = result.error ? "FALLBACK" : "SUCCESS";
    console.log(`\n[${status}] ${result.creatorName}`);
    console.log(`  Strategy: ${result.strategy}`);
    console.log(`  URL: ${result.avatarUrl}`);
  }

  console.log("\n" + "=".repeat(80));
  console.log("TEST COMPLETE");
  console.log("=".repeat(80));

  return results;
}

// Run the test
runTest().catch(console.error);
