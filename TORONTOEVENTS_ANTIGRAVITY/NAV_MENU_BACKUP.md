# Navigation Menu Backup — 2026-02-11

## Quick Nav Menu (Hamburger Sidebar) — index.html

### Current Structure (BEFORE changes):

#### PLATFORM Section
| Icon | Label | Action/Link |
|------|-------|-------------|
| 🌐 | Global Feed | Sets viewMode='feed', scrolls to events |
| 📧 | Contact Support | Pulsing button, scrolls to footer |

#### NETWORK Section (collapsible `<details>`)
| Icon | Label | Link |
|------|-------|------|
| 🛠️ | Windows Boot Fixer | /WINDOWSFIXER/ |
| 🌟 | Mental Health Resources | /MENTALHEALTHRESOURCES/ |
| 📈 | Find Stocks | /findstocks |
| 🎬 | Movies & TV | /MOVIESHOWS/ |
| ⭐ | Favorite Creators | /fc/#/guest |
| 💎 | FAVCREATORS | /fc/#/guest |
| 🔴 | are your favorite creators live? | /fc/#/guest |

#### Standalone items (outside NETWORK)
| Icon | Label | Link/Action |
|------|-------|-------------|
| 🎮 | 2XKO Frame Data | /2xko |
| ⚙️ | Event System Settings | Opens settings modal |
| 📧 | Contact Support | Dashed border, scrolls to footer |

#### DATA MANAGEMENT Section
| Icon | Label | Action |
|------|-------|--------|
| 📦 | JSON | Export saved events as JSON |
| 📊 | CSV | Export as CSV |
| 📅 | Calendar (ICS) | Export as .ics file |
| 📥 | Import Collection | File upload for .json import |

#### PERSONAL Section
| Icon | Label | Action |
|------|-------|--------|
| ♥ | My Collection | Sets viewMode='saved', shows count badge |

#### SUPPORT Section
- Manual Uplink: support@findtorontoevents.ca
- Response: 24-48h

#### Footer
- Antigravity Systems v0.5.2

---

## Quick Nav Menu — React Chunk (a2ac3a6616d60872.js, module 40625)

### Current Structure (BEFORE changes):

#### PLATFORM Section
| Icon | Label | Action |
|------|-------|--------|
| 🌐 | Global Feed | viewMode='feed' |
| ♥ | My Collection | viewMode='saved' + count badge |

#### NETWORK Section
| Icon | Label | Link |
|------|-------|------|
| 🎉 | Toronto Events | / |
| 🛠️ | Windows Fixer | /WINDOWSFIXER/ |
| 📈 | Find Stock Ideas | /findstocks |
| 🎬 | Movies & TV & Trailers | (expandable details) |
|  ├ 🎬 | V1 — Now Showing | /MOVIESHOWS/ |
|  ├ 🎞️ | V2 — The Film Vault | /movieshows2/ |
|  └ 🎥 | V3 — Binge Mode | /MOVIESHOWS3/ |
| ⭐ | FAVCREATORS | /fc/#/guest |
| 🌟 | Mental Health Resources | /MENTALHEALTHRESOURCES/ |
| 🌐 | VR Experience | /vr/ |
| 📱 | VR Mobile | /vr/mobile-index.html |
| 📊 | Accountability Dashboard | /fc/#/accountability |
| 🔗 | Recommended Gear & Links | /affiliates/ |
| ⚙️ | Event System Settings | Opens settings modal |

#### DATA MANAGEMENT Section
| Icon | Label | Action |
|------|-------|--------|
| 📦 | JSON | Export as JSON |
| 📊 | CSV | Export as CSV |
| 📅 | Calendar (ICS) | Export as .ics |
| 📥 | Import Collection | File upload .json |

#### Contact Support + SUPPORT Section
| Item | Details |
|------|---------|
| Contact Support button | Scrolls to footer |
| Manual Uplink | support@findtorontoevents.ca |
| Response | 24-48h |

---

## "Other Stuff" Menu — blog-events-engine.js

### Current Structure:

#### Featured (highlighted)
| Icon | Label | Description | Link | Color |
|------|-------|-------------|------|-------|
| ☁️ | Toronto Weather | Real-time conditions & what to wear | /weather/ | #00d4ff |
| 🔗 | Recommended Gear & Links | Products we trust & stand behind | /affiliates/ | #fbbf24 |
| 🆕 | Latest Updates | New features & improvements | /updates/ | #34d399 |
| 📰 | News Aggregator | Toronto & world news from 20+ sources | /news/ | #f87171 |
| 🎁 | Deals & Freebies | 78 birthday freebies & Canadian deals | /deals/ | #fbbf24 |

#### Apps & Tools
| Label | Description | Link | Color |
|-------|-------------|------|-------|
| Investment Hub | Portfolios, analytics & tools | /investments/ | #22c55e |
| Stock Ideas | AI picks, updated daily | /findstocks/ | #f59e0b |
| Portfolio Dashboard | Track your positions & equity curve | /findstocks/portfolio2/dashboard.html | #6366f1 |
| Dividends & Earnings | Dividend calendar & earnings tracker | /findstocks/portfolio2/dividends.html | #22c55e |
| Crypto Scanner | Crypto pairs analysis | /findcryptopairs/ | #f59e0b |
| Forex Scanner | Currency pairs analysis | /findforex2/ | #06b6d4 |
| Goldmine Dashboard | Multi-dimensional scoring | /live-monitor/goldmine-dashboard.html | #6366f1 |
| Sports Bet Finder | NHL, NBA, NFL odds & picks | /live-monitor/sports-betting.html | #4ade80 |

#### Entertainment
| Label | Description | Link | Color |
|-------|-------------|------|-------|
| Now Showing | Cineplex showtimes & ratings | /MOVIESHOWS/ | #f59e0b |
| The Film Vault | 4,000+ titles & playlists | /movieshows2/ | #fbbf24 |
| Binge Mode | TikTok-style auto-scroll trailers | /MOVIESHOWS3/ | #fb923c |
| Fav Creators | Track streamers across platforms | /fc/#/guest | #ec4899 |

#### More
| Label | Description | Link | Color |
|-------|-------------|------|-------|
| Mental Health | Wellness tools & crisis support | /MENTALHEALTHRESOURCES/ | #10b981 |
| Windows Boot Fixer | Fix BSOD & boot issues | /WINDOWSFIXER/ | #667eea |
| VR Experience | VR worlds for desktop & Quest | /vr/ | #a855f7 |
| Game Arena | Browser-based game prototypes | /vr/game-arena/ | #a855f7 |
| GotJob | Your job finding hub | /gotjob/ | #06b6d4 |
| Blog | Toronto event articles & guides | /blog/ | #818cf8 |

#### Footer
- "← Back to Events" → /

---

## Files Changed
- `TORONTOEVENTS_ANTIGRAVITY/index.html` — Main page Quick Nav
- `TORONTOEVENTS_ANTIGRAVITY/_next/static/chunks/a2ac3a6616d60872.js` — React nav component

## Copies of chunk file (all need updating if chunk is changed):
- `TORONTOEVENTS_ANTIGRAVITY/_next/static/chunks/a2ac3a6616d60872.js`
- `TORONTOEVENTS_ANTIGRAVITY/next/_next/static/chunks/a2ac3a6616d60872.js`
- `TORONTOEVENTS_ANTIGRAVITY/next/static/chunks/a2ac3a6616d60872.js`
- `TORONTOEVENTS_ANTIGRAVITY/TORONTOEVENTS_ANTIGRAVITY/_next/static/chunks/a2ac3a6616d60872.js`
