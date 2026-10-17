const assert = require("assert");
const fs = require("fs");

const bundle = fs.readFileSync(
  require.resolve("../docs/assets/main-DF_ZQ_dn.js"),
  "utf8"
);

// Guard 1: previous fix — full TikTok URL fallback before the colon parser.
assert.ok(
  bundle.includes(
    String.raw`urlMatch=/^https?:\/\/(?:www\.)?tiktok\.com\/@([^/?#]+)/i.exec(Qt.trim())`
  ),
  "missing full-URL TikTok fallback parser"
);
assert.ok(
  bundle.includes(String.raw`q=urlMatch?["tiktok"]:w.slice(1)`),
  "missing urlMatch platform wiring"
);

// Guard 2: new fix — scheme-less / typo-domain TikTok pre-parse in quick add.
assert.ok(
  bundle.includes(
    String.raw`ttm=/^(?:https?:\/\/)?(?:www\.)?tiktok\.com+\/?@([^/?#]+)/i.exec(qaIn)`
  ),
  "missing scheme-less/typo-domain TikTok pre-parse"
);
assert.ok(
  bundle.includes(
    String.raw`y=sb(Qt)||(ttm?{platform:"tiktok",username:ttm[1].toLowerCase()`
  ),
  "missing ttm fallback wiring in quick add"
);

// Guard 3: post-Quick-Add toast tells the user to enable the bell icon for
// live notifications — both success paths (URL branch and name/legacy branch).
assert.ok(
  bundle.includes(
    'Added ${jn} with 1 platform: ${Mn}. Tap the \ud83d\udd14 bell on their card to track live notifications.'
  ),
  "URL-branch success toast missing bell-icon hint"
);
assert.ok(
  bundle.includes(
    'Added ${xe.name} with platforms: ${ct}. Tap the \ud83d\udd14 bell on their card to track live notifications.'
  ),
  "legacy-branch success toast missing bell-icon hint"
);

// Guard 4: guest sign-in warning — when the user is NOT signed in (`!r`),
// both Quick Add success paths emit type "warning" with a persist reminder,
// and the toast renderer knows the amber "warning" styling.
assert.ok(
  bundle.includes(
    'F({type:r?"success":"warning",message:r?`Added ${jn} with 1 platform:'
  ),
  "URL-branch guest warning missing"
);
assert.ok(
  bundle.includes(
    'F({type:r?"success":"warning",message:r?`Added ${xe.name} with platforms:'
  ),
  "legacy-branch guest warning missing"
);
assert.strictEqual(
  bundle.split("sign in to persist your followed users!").length - 1,
  2,
  "both branches must carry the sign-in persist reminder text"
);
assert.ok(
  bundle.includes(
    'R.type==="warning"?"rgba(251, 191, 36, 0.15)"'
  ) &&
    bundle.includes('R.type==="warning"?"#fcd34d"'),
  "toast renderer missing warning (amber) styling"
);

// Guard 5 (2026-10-17 kaneljoseph bug): three fixes for guest follows.
// 5a. platform-first colon input (`kick:kaneljoseph`) swaps to [name, platform].
assert.ok(
  bundle.includes(
    '["kick","twitch","youtube","tiktok","instagram"].includes(t[0].toLowerCase())'
  ) &&
    bundle.includes("?[t[1],t[0]]:t"),
  "platform-first colon swap missing"
);
// 5b. quick-added streamer platforms are live-checked even when the default
//     live-platform list is tiktok-only (isLiveStreamer/checkLive union).
assert.strictEqual(
  bundle.split('["kick","twitch","youtube"]').length - 1,
  3,
  "expected 3 kick/twitch/youtube live-capable unions (Ke, checkLive, isLiveStreamer)"
);
assert.ok(
  bundle.includes(
    'Ke=Zt.defaultLivePlatforms.includes(y.platform)||["kick","twitch","youtube"].includes(y.platform)'
  ),
  "URL-branch live-capable union missing"
);
// 5c. guest load MERGES server list with local follows instead of replacing
//     (previously the get_my_creators user_id=0 response wiped guest adds).
assert.ok(
  bundle.includes(
    'Je(prev=>{const gCt=new Set(He.map(ct=>ct.id)),gCx=prev.filter(ct=>!gCt.has(ct.id));return td(gCx.length?He.concat(gCx):He)})'
  ),
  "guest load merge missing"
);

// Guard 6 (guest boot wipe): the creators-state initializer must NOT skip
// localStorage on #/guest anymore — `if(qn)return ii` discarded the guest's
// saved list on every reload, then the first save effect overwrote storage
// with the default pack (root cause of follows vanishing on refresh).
assert.strictEqual(
  bundle.split("if(qn)return ii").length - 1,
  0,
  "initializer must not discard localStorage on the guest route"
);
assert.ok(
  bundle.includes(
    '[Re,Je]=g.useState(()=>{try{if(localStorage.getItem("fav_creators_version")!==nd)'
  ),
  "localStorage hydration for creators state missing"
);

// Guard 7 (cross-platform Quick Add, 2026-10-17 audit follow-through):
// both URL parsers gain Reddit / Spotify / Twitter-X / YouTube /user/,
// and the legacy name:platform path rejects unparsable input outright.
assert.strictEqual(
  bundle.split('if(c==="reddit.com"||c==="old.reddit.com")').length - 1,
  2,
  "reddit parser must exist in both URL parsers"
);
assert.strictEqual(
  bundle.split('if(c==="open.spotify.com"&&d.startsWith("/user/"))').length - 1,
  2,
  "spotify parser must exist in both URL parsers"
);
assert.strictEqual(
  bundle.split('if(c==="twitter.com"||c==="x.com")').length - 1,
  2,
  "twitter/x parser must exist in both URL parsers"
);
assert.strictEqual(
  bundle.split('d.startsWith("/user/")?h=d.slice(6).split("/")[0]||""').length -
    1,
  4,
  "youtube /user/ clause must exist in both parsers (reddit uses the same shape)"
);
assert.ok(
  bundle.includes('if(K.length===0||_.includes("/")){F({type:"error"'),
  "legacy parser must reject unparsable input (empty accounts or slash in name)"
);

// Guard 8: homepage thumbnail proxy list covers the hotlink-403 hosts.
const fsPath = require("path");
const homepage = fs.readFileSync(
  fsPath.join(__dirname, "..", "..", "TORONTOEVENTS_ANTIGRAVITY", "index.html"),
  "utf8"
);
assert.ok(
  homepage.includes(
    "'nowtoronto.com', 'www.nowtoronto.com', 'torontobotanicalgarden.ca', 'www.torontobotanicalgarden.ca', 'secure.meetupstatic.com'"
  ),
  "homepage dominated list must include the hotlink-403 hosts"
);

// Extract the deployed regex itself and test its behavior directly, so the
// assertions run against the pattern that actually ships.
const start = bundle.indexOf("ttm=") + 4;
assert.ok(start >= 4, "ttm= assignment not found in bundle");
const end = bundle.indexOf(".exec(qaIn)", start);
assert.ok(end > start, "ttm regex literal not found in bundle");
const reSrc = bundle.slice(start, end);
assert.ok(reSrc.startsWith("/") && reSrc.endsWith("/i"), `unexpected regex literal: ${reSrc}`);
const ttm = eval(reSrc);

const parseHandle = (input) => {
  const m = ttm.exec(String(input).trim());
  return m ? m[1].toLowerCase() : null;
};

// The reported bug input: typo'd domain, no scheme.
assert.strictEqual(parseHandle("tiktok.comm/@nikkibby11"), "nikkibby11");
// Original report: plain scheme-less domain.
assert.strictEqual(parseHandle("tiktok.com/@gurleen_dosanjh"), "gurleen_dosanjh");
// Variants that must keep working.
assert.strictEqual(parseHandle("https://www.tiktok.com/@ellamarisue"), "ellamarisue");
assert.strictEqual(parseHandle("http://tiktok.com/@SomeUser"), "someuser");
assert.strictEqual(parseHandle("  tiktok.comm/@nikkibby11  "), "nikkibby11");

// Negative: other platforms and junk must NOT be captured by the TikTok regex.
assert.strictEqual(parseHandle("https://twitch.tv/somebody"), null);
assert.strictEqual(parseHandle("kick.com/somebody"), null);
assert.strictEqual(parseHandle("hello world"), null);

// Negative: handle must stop before path/query fragments.
assert.strictEqual(parseHandle("tiktok.com/@user/videos?x=1"), "user");

console.log("quick_add_url_test: all assertions passed");