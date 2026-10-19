import re
import sys

path = '/home/eaguiar2015/findtorontoevents_antigravity.ca/.worktrees/cis-vr-coding-guide/findtorontoevents.ca/CIS-VR/index.html'

with open(path, 'r') as f:
    content = f.read()

# 1. Insert background CSS into <style> block
# Find the </style> tag
style_end = content.find('</style>')
if style_end == -1:
    print('No </style> tag found')
    sys.exit(1)

# The CSS to insert (background animations)
bg_css = '''
  /* ============================================================
     DYNAMIC BACKGROUND
     CSS-only aurora: drifting radial blooms over a dark ink base,
     plus a film-grain overlay for texture. No canvas, no JS.
     ============================================================ */
  .bg-scene,
  .bg-aurora,
  .bg-orbit,
  .bg-grain {
    position: fixed;
    inset: 0;
    pointer-events: none;
  }

  .bg-scene {
    z-index: 0;
    inset: -8%;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 1000'%3E%3Cdefs%3E%3ClinearGradient id='line' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop offset='0%25' stop-color='%2362f5c7' stop-opacity='.22'/%3E%3Cstop offset='100%25' stop-color='%237aa2ff' stop-opacity='.18'/%3E%3C/linearGradient%3E%3CradialGradient id='node' cx='50%25' cy='50%25' r='50%25'%3E%3Cstop offset='0%25' stop-color='%23ffffff' stop-opacity='.92'/%3E%3Cstop offset='45%25' stop-color='%2362f5c7' stop-opacity='.55'/%3E%3Cstop offset='100%25' stop-color='%2362f5c7' stop-opacity='0'/%3E%3C/radialGradient%3E%3C/defs%3E%3Cg fill='none' stroke='url(%23line)' stroke-width='2'%3E%3Cpath d='M120 770 L360 590 L620 630 L820 420 L1090 470 L1380 260'/%3E%3Cpath d='M220 260 L470 330 L700 180 L980 250 L1210 120 L1480 200'/%3E%3Cpath d='M180 520 L390 440 L590 500 L790 360 L1030 380 L1260 560 L1470 520'/%3E%3Cpath d='M320 850 L560 720 L760 760 L1010 650 L1280 720'/%3E%3C/g%3E%3Cg fill='url(%23node)'%3E%3Ccircle cx='120' cy='770' r='40'/%3E%3Ccircle cx='360' cy='590' r='30'/%3E%3Ccircle cx='620' cy='630' r='26'/%3E%3Ccircle cx='820' cy='420' r='38'/%3E%3Ccircle cx='1090' cy='470' r='26'/%3E%3Ccircle cx='1380' cy='260' r='44'/%3E%3Ccircle cx='220' cy='260' r='34'/%3E%3Ccircle cx='470' cy='330' r='22'/%3E%3Ccircle cx='700' cy='180' r='42'/%3E%3Ccircle cx='980' cy='250' r='28'/%3E%3Ccircle cx='1210' cy='120' r='20'/%3E%3Ccircle cx='1480' cy='200' r='34'/%3E%3Ccircle cx='180' cy='520' r='28'/%3E%3Ccircle cx='390' cy='440' r='18'/%3E%3Ccircle cx='590' cy='500' r='22'/%3E%3Ccircle cx='790' cy='360' r='24'/%3E%3Ccircle cx='1030' cy='380' r='20'/%3E%3Ccircle cx='1260' cy='560' r='38'/%3E%3Ccircle cx='1470' cy='520' r='24'/%3E%3Ccircle cx='320' cy='850' r='44'/%3E%3Ccircle cx='560' cy='720' r='26'/%3E%3Ccircle cx='760' cy='760' r='18'/%3E%3Ccircle cx='1010' cy='650' r='28'/%3E%3Ccircle cx='1280' cy='720' r='34'/%3E%3C/g%3E%3Cg stroke='%23a9b6c9' stroke-opacity='.08'%3E%3Cpath d='M0 120 H1600'/%3E%3Cpath d='M0 320 H1600'/%3E%3Cpath d='M0 520 H1600'/%3E%3Cpath d='M0 720 H1600'/%3E%3Cpath d='M260 0 V1000'/%3E%3Cpath d='M620 0 V1000'/%3E%3Cpath d='M980 0 V1000'/%3E%3Cpath d='M1340 0 V1000'/%3E%3C/g%3E%3C/svg%3E");
    background-position: center;
    background-repeat: no-repeat;
    background-size: cover;
    mix-blend-mode: screen;
    opacity: .28;
    filter: saturate(1.05);
    animation: scene-drift 46s ease-in-out infinite alternate;
    will-change: transform;
  }

  .bg-aurora {
    z-index: 0;
    inset: -25%;
    /* Continuous dynamic background in the JS page's accent hues: teal-green
       bloom lower-left, slate-blue bloom upper-right, over the shared navy base. */
    background:
      radial-gradient(42% 46% at 18% 22%, rgba(98,245,199,.16) 0%, transparent 66%),
      radial-gradient(40% 44% at 82% 18%, rgba(122,162,255,.15) 0%, transparent 64%),
      radial-gradient(46% 50% at 62% 78%, rgba(98,245,199,.07) 0%, transparent 68%),
      radial-gradient(40% 44% at 24% 84%, rgba(18,27,46,.9) 0%, transparent 70%);
    filter: blur(82px) saturate(1.05) brightness(.8);
    animation: aurora-drift 32s ease-in-out infinite alternate;
    will-change: transform;
    opacity: .8;
  }

  .bg-orbit {
    z-index: 0;
    inset: -12%;
    background:
      radial-gradient(28% 28% at 22% 30%, rgba(98,245,199,.10) 0%, transparent 72%),
      radial-gradient(24% 24% at 76% 22%, rgba(122,162,255,.12) 0%, transparent 70%),
      radial-gradient(34% 34% at 62% 74%, rgba(98,245,199,.08) 0%, transparent 74%),
      repeating-linear-gradient(
        125deg,
        rgba(255,255,255,.00) 0 18px,
        rgba(122,162,255,.025) 18px 19px,
        rgba(255,255,255,.00) 19px 44px
      );
    mix-blend-mode: screen;
    filter: blur(1px) saturate(1.02);
    opacity: .34;
    animation: orbit-drift 44s linear infinite;
    transform-origin: 50% 50%;
    will-change: transform;
  }

  /* Calming veil over the ambient layers so the blooms never fight body text.
     Sits above the aurora/grain (z-index 1) but below all content (z-index 2). */
  .bg-veil {
    position: fixed;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background: linear-gradient(180deg, rgba(8,12,20,.34) 0%, rgba(8,12,20,.52) 55%, rgba(8,12,20,.7) 100%);
  }

  /* Content sits above the ambient layers */
  body > header.hero,
  body > main,
  body > footer {
    position: relative;
    z-index: 2;
  }

  /* Reading-progress bar, native scroll-driven CSS (no JS) */
  .scroll-progress {
    position: fixed;
    top: 0; left: 0;
    width: 100%;
    height: 3px;
    z-index: 60;
    background: linear-gradient(90deg, var(--brand-green), var(--sage), var(--critical));
    transform-origin: 0 50%;
    transform: scaleX(0);
    animation: progress-grow linear both;
    animation-timeline: scroll(root);
  }
  @keyframes progress-grow {
    from { transform: scaleX(0); }
    to   { transform: scaleX(1); }
  }

  /* Accessibility: honour reduced-motion on every ambient animation */
  @media (prefers-reduced-motion: reduce) {
    .bg-scene, .bg-aurora, .bg-orbit { animation: none; }
    .scroll-progress { animation: none; transform: scaleX(1); opacity: .35; }
    html { scroll-behavior: auto; }
    *, *::before, *::after {
      animation-duration: .01ms !important;
      animation-iteration-count: 1 !important;
      transition-duration: .01ms !important;
    }
  }

  /* Define variables used in animations if not present */
  :root {
    --brand-green:#62f5c7;
    --brand-green-bright:#7fead0;
    --blue-whale:#0a1420;
    --dark-green:#121b2e;
    --sage:#8fa3bd;
    --t-1:#e6edf6;
    --t-2:#a9b6c9;
    --t-3:#8b98ac;
    --ok:#4ade80;
    --warn:#fbbf24;
    --bad:#f87171;
    --critical:#7aa2ff;
    --r-sm:6px; --r-md:10px; --r-lg:14px; --r-xl:20px;
    --ease:cubic-bezier(.4,0,.2,1);
  }
'''

# Insert before </style>
new_content = content[:style_end] + bg_css + '\n' + content[style_end:]

# 2. Insert the background divs after <body> tag
body_open = new_content.find('<body>')
if body_open == -1:
    print('No <body> tag found')
    sys.exit(1)
# Insert right after the opening tag
insert_point = body_open + len('<body>')
divs = '\n  <div class="bg-scene"></div>\n  <div class="bg-aurora"></div>\n  <div class="bg-orbit"></div>\n  <div class="bg-grain"></div>\n  <div class="bg-veil"></div>'
new_content = new_content[:insert_point] + divs + '\n' + new_content[insert_point:]

# Write back
with open(path, 'w') as f:
    f.write(new_content)

print('Updated CIS-VR index.html with animated aurora background')