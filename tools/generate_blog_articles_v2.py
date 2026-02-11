#!/usr/bin/env python3
"""
Generate neighbourhood, event, and things-to-do articles for Toronto Events blog.
Adds 23 new articles with 3 new filter categories.

Run from project root:
  python tools/generate_blog_articles_v2.py
"""
import os
import random
from pathlib import Path
from datetime import datetime, timedelta

BLOG_DIR = Path(__file__).resolve().parent.parent / 'TORONTOEVENTS_ANTIGRAVITY' / 'build' / 'blog'
SITE_URL = 'https://findtorontoevents.ca'


def article_template(title, slug, description, keywords, date_str, category, tag_label, image, content_html, related_html):
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Toronto Events Blog</title>
    <meta name="description" content="{description}">
    <meta name="keywords" content="{keywords}">
    <link rel="canonical" href="{SITE_URL}/blog/{slug}">
    <link rel="icon" href="/favicon.ico" sizes="256x256" type="image/x-icon">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:type" content="article">
    <meta property="og:url" content="{SITE_URL}/blog/{slug}">
    <meta property="og:image" content="{SITE_URL}/blog/images/{image}">
    <meta property="og:site_name" content="Toronto Events">
    <meta property="og:locale" content="en_CA">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
    <meta name="twitter:image" content="{SITE_URL}/blog/images/{image}">
    <meta name="geo.region" content="CA-ON">
    <meta name="geo.placename" content="Toronto">
    <meta name="geo.position" content="43.6532;-79.3832">
    <meta name="ICBM" content="43.6532, -79.3832">
    <meta name="robots" content="index, follow">
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "{title}",
        "description": "{description}",
        "url": "{SITE_URL}/blog/{slug}",
        "datePublished": "{date_str}",
        "dateModified": "{date_str}",
        "image": "{SITE_URL}/blog/images/{image}",
        "author": {{ "@type": "Organization", "name": "Toronto Events", "url": "{SITE_URL}" }},
        "publisher": {{
            "@type": "Organization",
            "name": "Toronto Events",
            "url": "{SITE_URL}",
            "logo": {{ "@type": "ImageObject", "url": "{SITE_URL}/favicon.ico" }}
        }},
        "mainEntityOfPage": {{ "@type": "WebPage", "@id": "{SITE_URL}/blog/{slug}" }}
    }}
    </script>
    <style>
        :root {{
            --pk-300:#c084fc;--pk-400:#a855f7;--pk-500:#9333ea;--pk-600:#7e22ce;--pk-900:#3b0764;
            --surface-0:#0a0a0f;--surface-1:#12121a;--surface-2:#1a1a25;
            --text-1:#f0f0f5;--text-2:#a0a0b5;--text-3:#606075;
        }}
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--surface-0);color:var(--text-1);line-height:1.8;min-height:100vh}}
        body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 20% 0%,rgba(147,51,234,.15) 0%,transparent 50%),radial-gradient(ellipse at 80% 100%,rgba(59,7,100,.2) 0%,transparent 50%);pointer-events:none;z-index:-1}}
        a{{color:var(--pk-400);text-decoration:none;transition:color .2s}}a:hover{{color:var(--pk-300)}}
        .top-nav{{position:sticky;top:0;z-index:100;background:rgba(10,10,15,.85);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,.05);padding:.75rem 1.5rem;display:flex;align-items:center;justify-content:space-between}}
        .nav-brand{{font-weight:900;font-size:1.1rem;letter-spacing:-.02em;color:#fff}}.nav-brand span{{color:var(--pk-400)}}
        .nav-links{{display:flex;gap:1.5rem;align-items:center}}.nav-links a{{font-size:.8rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--text-2)}}.nav-links a:hover{{color:#fff}}.nav-links a.active{{color:var(--pk-400)}}
        .breadcrumb{{max-width:800px;margin:0 auto;padding:1.5rem 1.5rem 0;font-size:.8rem;color:var(--text-3)}}.breadcrumb a{{color:var(--text-3)}}.breadcrumb a:hover{{color:var(--pk-300)}}
        .hero-img{{width:100%;max-height:420px;object-fit:cover;border-bottom:1px solid rgba(255,255,255,.05)}}
        article{{max-width:800px;margin:0 auto;padding:0 1.5rem 3rem}}
        .article-header{{padding:2rem 0 1.5rem;border-bottom:1px solid rgba(255,255,255,.05);margin-bottom:2rem}}
        .tag{{display:inline-block;font-size:.65rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;padding:.25rem .75rem;border-radius:999px;background:rgba(147,51,234,.15);color:var(--pk-300);margin-bottom:.75rem}}
        .tag.breaking{{background:rgba(239,68,68,.15);color:#f87171}}
        .tag.sports{{background:rgba(34,197,94,.15);color:#4ade80}}
        .tag.food{{background:rgba(251,191,36,.15);color:#fbbf24}}
        .tag.arts{{background:rgba(96,165,250,.15);color:#60a5fa}}
        .tag.community{{background:rgba(244,114,182,.15);color:#f472b6}}
        .tag.seasonal{{background:rgba(45,212,191,.15);color:#2dd4bf}}
        .tag.event{{background:rgba(251,146,60,.15);color:#fb923c}}
        .tag.thingstodo{{background:rgba(52,211,153,.15);color:#34d399}}
        .tag.neighbourhood{{background:rgba(129,140,248,.15);color:#818cf8}}
        h1{{font-size:clamp(1.8rem,4vw,2.5rem);font-weight:900;line-height:1.2;letter-spacing:-.02em;margin-bottom:1rem}}
        .meta{{font-size:.8rem;color:var(--text-3);display:flex;gap:1.5rem;flex-wrap:wrap}}
        h2{{font-size:1.4rem;font-weight:800;margin:2.5rem 0 1rem;color:var(--text-1)}}
        h3{{font-size:1.1rem;font-weight:700;margin:2rem 0 .75rem;color:var(--text-1)}}
        p{{margin-bottom:1.25rem;color:var(--text-2);font-size:1rem}}
        ul,ol{{margin:0 0 1.25rem 1.5rem;color:var(--text-2)}}li{{margin-bottom:.5rem}}
        .callout{{background:var(--surface-1);border:1px solid rgba(255,255,255,.06);border-left:3px solid var(--pk-500);border-radius:.75rem;padding:1.25rem 1.5rem;margin:1.5rem 0}}
        .callout h3{{margin:0 0 .5rem;font-size:1rem;color:#fff}}
        .callout p{{margin-bottom:.5rem;font-size:.9rem}}
        .callout .detail{{font-size:.8rem;color:var(--text-3);display:flex;gap:1rem;flex-wrap:wrap}}
        .source-tag{{display:inline-block;font-size:.65rem;padding:.15rem .5rem;border-radius:4px;background:rgba(255,255,255,.05);color:var(--text-3);margin-left:.5rem}}
        .cta{{text-align:center;padding:3rem 0;margin-top:2rem;border-top:1px solid rgba(255,255,255,.05)}}
        .cta h2{{font-size:1.5rem;margin-bottom:.75rem;color:#fff}}
        .cta p{{color:var(--text-2);margin-bottom:1.5rem}}
        .cta-btn{{display:inline-block;padding:.8rem 2rem;background:var(--pk-500);color:#fff;font-weight:800;font-size:.85rem;border-radius:999px;text-transform:uppercase;letter-spacing:.05em;transition:background .2s,transform .2s}}.cta-btn:hover{{background:var(--pk-600);transform:scale(1.05);color:#fff}}
        .related{{max-width:800px;margin:0 auto;padding:0 1.5rem 3rem}}
        .related h2{{font-size:1.3rem;font-weight:800;margin-bottom:1.5rem}}
        .related-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem}}
        .related-card{{background:var(--surface-1);border:1px solid rgba(255,255,255,.06);border-radius:.75rem;padding:1.25rem;transition:border-color .2s}}.related-card:hover{{border-color:rgba(147,51,234,.3)}}
        .related-card h3{{font-size:.9rem;font-weight:700;line-height:1.3;margin-bottom:.5rem}}.related-card h3 a{{color:#fff}}.related-card h3 a:hover{{color:var(--pk-300)}}
        .related-card .meta{{font-size:.7rem}}
        .venue-card{{background:var(--surface-1);border:1px solid rgba(255,255,255,.06);border-radius:.75rem;padding:1.25rem 1.5rem;margin:1rem 0}}
        .venue-card h3{{margin:0 0 .5rem;font-size:1rem;color:#fff}}.venue-card p{{margin-bottom:.25rem;font-size:.9rem}}
        .venue-card .addr{{font-size:.8rem;color:var(--text-3)}}
        footer{{text-align:center;padding:3rem 1.5rem;border-top:1px solid rgba(255,255,255,.05);color:var(--text-3);font-size:.75rem}}footer a{{color:var(--text-2)}}
        @media(max-width:768px){{.nav-links{{gap:.75rem}}.nav-links a{{font-size:.7rem}}.related-grid{{grid-template-columns:1fr}}}}
    </style>
</head>
<body>
    <nav class="top-nav"><a href="/" class="nav-brand"><span>Toronto</span> Events</a><div class="nav-links"><a href="/">Home</a><a href="/blog/" class="active">Blog</a><a href="/MOVIESHOWS/">Movies</a><a href="/findstocks">Stocks</a></div></nav>
    <div class="breadcrumb"><a href="/">Home</a> &rsaquo; <a href="/blog/">Blog</a> &rsaquo; {title}</div>
    <article>
        <div class="article-header">
            <span class="tag {category}">{tag_label}</span>
            <h1>{title}</h1>
            <div class="meta"><span>{date_str}</span><span>Toronto Events Blog</span></div>
        </div>
        {content_html}
        <div class="cta">
            <h2>Discover More Toronto Events</h2>
            <p>Find breaking news, neighbourhood guides, and things to do across the city.</p>
            <a href="/" class="cta-btn">Browse All Toronto Events</a>
        </div>
    </article>
    <section class="related">
        <h2>More Toronto Stories</h2>
        <div class="related-grid">{related_html}</div>
    </section>
    <footer><p>Built with love for Toronto &middot; <a href="/">Toronto Events</a> &middot; <a href="https://tdotevent.ca">TdotEvent.ca</a></p></footer>
</body>
</html>'''


# ── Articles Data ─────────────────────────────────────────────────
# Each: (slug, title, description, keywords, category_css, tag_label, image, date, content_html)

ARTICLES = [
    # ══════════════════════════════════════════════════════════════
    # EVENT CATEGORY
    # ══════════════════════════════════════════════════════════════

    ("illuminite-light-festival-toronto-2026",
     "ILLUMINITE 2026: Toronto's Free Light Festival at 5 Downtown Locations",
     "ILLUMINITE transforms five Downtown Yonge locations with immersive light installations exploring the theme of Play. Free from February 13 to March 8, 2026.",
     "ILLUMINITE Toronto, Toronto light festival, free events Toronto 2026, Downtown Yonge, light installations Toronto, things to do Toronto February",
     "event", "Event",
     "events-in-toronto.jpg",
     "February 11, 2026",
     """<p>The third annual ILLUMINITE festival returns to Downtown Yonge from <strong>February 13 to March 8, 2026</strong>, transforming five locations into immersive, light-based experiences. This year's theme is <strong>"PLAY"</strong>, and every installation is designed to spark joy, movement, and connection during the darkest months of winter.</p>
<p>Best of all, it is completely free.</p>

<h2>The Five Locations</h2>
<p>ILLUMINITE spreads across five distinct Downtown Yonge sites, each hosting different installations:</p>

<div class="venue-card">
<h3>777 Bay Plaza</h3>
<p>Home to the glowing <strong>LED Oval Swings</strong>, where visitors can sit, swing, and watch the lights respond to their movement. A crowd favourite from early previews.</p>
<p class="addr">777 Bay Street</p>
</div>

<div class="venue-card">
<h3>College Park</h3>
<p>Features <strong>Hearts at Play</strong>, interactive heart-shaped sculptures that light up and pulse with colour when touched. Perfect for Valentine's weekend.</p>
<p class="addr">444 Yonge Street</p>
</div>

<div class="venue-card">
<h3>Granby Parkette</h3>
<p>The <strong>Domino Effect</strong> installation turns musical dominoes into a collaborative game of light and sound. Tip one, and watch the chain reaction cascade in colour.</p>
<p class="addr">Granby Street at Yonge</p>
</div>

<div class="venue-card">
<h3>Sankofa Square</h3>
<p>Toronto's central public square hosts a rotating program of light performances and digital art projections throughout the festival.</p>
<p class="addr">1 Dundas Street East</p>
</div>

<div class="venue-card">
<h3>Trinity Square Park</h3>
<p>Adjacent to the Eaton Centre, this park features ambient light paths and contemplative installations that reward evening strolls.</p>
<p class="addr">Behind 10 Trinity Square</p>
</div>

<h2>When to Visit</h2>
<p>Installations are active nightly from <strong>4 PM to 11 PM</strong>, February 13 through March 8. Weeknight visits tend to be less crowded. The opening weekend coincides with Valentine's Day and the start of the Canadian International AutoShow, making it easy to combine activities.</p>

<h2>Getting There</h2>
<p>All five locations are within a 10-minute walk of each other along Yonge Street between College and Queen. The closest TTC stations are Dundas and College on Line 1. Street parking is limited; the TTC or PATH system is recommended.</p>

<div class="callout">
<h3>Key Details</h3>
<p>Free admission, nightly 4-11 PM, February 13 - March 8, 2026</p>
<div class="detail"><span>Downtown Yonge, 5 locations</span><span>All ages</span></div>
</div>

<p>ILLUMINITE is presented by the Downtown Yonge BIA. For the full map and installation details, visit the Downtown Yonge BIA website.</p>"""),

    ("lumiere-art-of-light-ontario-place-2026",
     "Lumiere at Ontario Place: Free Outdoor Light Art Exhibition Opens February 16",
     "Lumiere: The Art of Light brings 14 stunning light installations by Ontario artists to Trillium Park at Ontario Place. Free outdoor exhibition from February 16 to March 27.",
     "Lumiere Ontario Place, Toronto light art, Trillium Park Toronto, free events Toronto, outdoor art Toronto winter, Ontario Place events 2026",
     "event", "Event",
     "toronto-events.jpg",
     "February 11, 2026",
     """<p>A brand new outdoor light exhibition is coming to Ontario Place. <strong>Lumiere: The Art of Light</strong> opens on Family Day (February 16) and runs through March 27, 2026, featuring 14 large-scale light-based installations by Ontario artists.</p>

<h2>What to Expect</h2>
<p>Set in the beautiful Trillium Park on the western tip of Ontario Place, the exhibition explores the theme <strong>"Rhythms of Light: Motion, Sound, and Time."</strong> Each of the 14 installations uses light as a medium for art, creating immersive experiences that interact with the natural landscape of the park.</p>
<p>The exhibition also includes bonfires along the lakeside trail, creating a warm, social atmosphere for evening visits. It is completely free.</p>

<h2>Trillium Park: An Underrated Toronto Gem</h2>
<p>Trillium Park itself is worth the visit. Opened in 2017, this 7.5-acre waterfront park features walking trails, rocky beaches, native plantings, and some of the best skyline views in the city. Adding 14 light installations to this setting creates something genuinely special for winter evenings.</p>

<h2>Visiting Details</h2>
<p>The exhibition runs nightly from dusk (approximately 5:30 PM) and is open until late. The closest transit is the 29 Dufferin bus to Exhibition Place, or a short walk from Exhibition GO station. Free parking is available on-site in the Ontario Place lot.</p>

<div class="callout">
<h3>Lumiere: The Art of Light</h3>
<p>February 16 - March 27, 2026 | Trillium Park, Ontario Place</p>
<div class="detail"><span>Free admission</span><span>Nightly from dusk</span><span>14 installations</span></div>
</div>

<p>This is one of the most compelling free events on Toronto's winter calendar. Combined with ILLUMINITE downtown, the city is offering an unprecedented amount of free public art this February.</p>"""),

    ("toronto-spring-festival-lunar-new-year-2026",
     "Toronto Spring Festival 2026: Lunar New Year Fireworks at City Hall",
     "Toronto Spring Festival celebrates the Year of the Horse with fireworks, lion dances, and cultural performances at Nathan Phillips Square on February 14-15, 2026.",
     "Toronto Spring Festival, Lunar New Year Toronto 2026, Year of the Horse, Nathan Phillips Square, Chinese New Year Toronto, fireworks Toronto",
     "event", "Event",
     "upcoming-toronto-events.jpg",
     "February 11, 2026",
     """<p>The <strong>Toronto Spring Festival</strong> takes over Nathan Phillips Square on <strong>February 14-15, 2026</strong> with a spectacular celebration of the Lunar New Year. This year marks the <strong>Year of the Fire Horse</strong>, which comes around only once every 60 years.</p>

<h2>What to Expect</h2>
<p>Running from noon to 11 PM both days, the free festival features:</p>
<ul>
<li><strong>Fireworks display</strong> over Nathan Phillips Square</li>
<li><strong>Lion and dragon dances</strong> by traditional performance troupes</li>
<li><strong>Live cultural performances</strong> including music, dance, and martial arts</li>
<li><strong>Immersive experiences</strong> and interactive workshops</li>
<li><strong>Food vendors</strong> with traditional Lunar New Year treats</li>
</ul>

<h2>The Fire Horse Significance</h2>
<p>2026 is the Year of the Fire Horse in the Chinese zodiac, a combination that occurs only once every 60 years. The Fire Horse is associated with energy, passion, and dramatic change. Expect extra-vibrant celebrations and larger-than-usual crowds.</p>

<h2>Chinatown Street Festival</h2>
<p>The following weekend (February 21-22), the celebration continues with the <strong>Downtown Chinatown Lunar New Year Street Festival</strong> on Spadina Avenue between College and Sullivan Street. This free two-day festival features lion and dragon dances, cooking demonstrations, fortune-telling, and cultural booths organized by the Downtown Chinatown BIA.</p>

<div class="callout">
<h3>Toronto Spring Festival</h3>
<p>February 14-15, 2026 | Noon - 11 PM | Nathan Phillips Square</p>
<div class="detail"><span>Free admission</span><span>All ages</span><span>Fireworks</span></div>
</div>

<p>Between the Toronto Spring Festival, Chinatown celebrations, and ILLUMINITE, mid-to-late February is shaping up to be one of the most event-packed stretches of the winter.</p>"""),

    ("winter-stations-woodbine-beach-2026",
     "Winter Stations 2026: Outdoor Art Installations Open at Woodbine Beach",
     "Winter Stations returns to Woodbine Beach on Family Day 2026 with large-scale art installations along the boardwalk. Free outdoor exhibition runs through late March.",
     "Winter Stations Toronto, Woodbine Beach art, outdoor art Toronto, free events Toronto, Family Day Toronto, Beaches boardwalk Toronto",
     "event", "Event",
     "things-to-do-toronto.jpg",
     "February 10, 2026",
     """<p><strong>Winter Stations</strong> returns to the Woodbine Beach boardwalk on Family Day (February 16, 2026), transforming lifeguard stations into large-scale public art installations. Now in its eleventh year, this free outdoor exhibition has become one of Toronto's most photographed winter events.</p>

<h2>How It Works</h2>
<p>Each year, artists and designers from around the world are invited to reimagine the iconic wooden lifeguard stations that dot the Beaches boardwalk. The stations become canvases for creative installations ranging from sculptural to interactive to conceptual. Visitors can walk the boardwalk and experience each piece at their own pace.</p>

<h2>Why It Works</h2>
<p>The genius of Winter Stations is its setting. The Beaches boardwalk in winter has a stark, beautiful quality that most Torontonians never see. The frozen lake, empty sand, and grey sky create a natural gallery that elevates the artwork. Add a thermos of coffee and warm layers, and you have one of the city's most memorable free outings.</p>

<h2>Visiting Tips</h2>
<ul>
<li>The installations are accessible 24/7, but daylight hours offer the best viewing</li>
<li>Start at the eastern end near the RC Harris Water Treatment Plant for the most dramatic approach</li>
<li>Combine with a walk through the Kew Gardens neighbourhood and lunch on Queen East</li>
<li>The 501 Queen streetcar stops at Woodbine Avenue, a short walk south to the boardwalk</li>
</ul>

<div class="callout">
<h3>Winter Stations 2026</h3>
<p>Opens February 16, 2026 | Woodbine Beach Boardwalk</p>
<div class="detail"><span>Free</span><span>24/7 access</span><span>Through late March</span></div>
</div>

<p>Winter Stations is the kind of quiet, contemplative event that makes Toronto special. No tickets, no lineups, just art on the beach.</p>"""),

    ("rom-after-dark-valentines-2026",
     "ROM After Dark Valentine's 2026: Late-Night Museum Party on February 14",
     "ROM After Dark celebrates Valentine's Day with a late-night party featuring live performances, DJ sets, and access to exhibitions including Sharks. February 14, 7:30-11 PM.",
     "ROM After Dark, Valentine's Day Toronto, Royal Ontario Museum party, museum events Toronto, things to do Valentine's Day Toronto 2026",
     "event", "Event",
     "toronto-events.jpg",
     "February 10, 2026",
     """<p>Forget the prix fixe dinner. The Royal Ontario Museum is hosting <strong>ROM After Dark: Valentines</strong> on <strong>Friday, February 14, 2026</strong>, transforming one of the world's great museums into a late-night party celebrating love, friendship, and community.</p>

<h2>What's Included</h2>
<p>From 7:30 PM to 11:00 PM, the museum opens its galleries for an adults-only evening featuring:</p>
<ul>
<li><strong>Live performances</strong> and curated DJ sets throughout the building</li>
<li>Full access to current exhibitions including <strong>Sharks</strong> (through March 22)</li>
<li><strong>Saints, Sinners, Lovers, and Fools: 300 Years of Flemish Masterworks</strong></li>
<li><strong>Wildlife Photographer of the Year</strong> exhibition</li>
<li>Cash bars and food stations throughout the museum</li>
<li>The stunning Michael Lee-Chin Crystal architecture lit up for the occasion</li>
</ul>

<h2>Why ROM After Dark Works</h2>
<p>There is something uniquely electric about wandering museum galleries at night with a drink in hand. The dinosaur galleries take on a completely different character after dark, and the Sharks exhibition hits different when the crowds thin out and the lighting shifts. It is one of Toronto's best date nights, but it works equally well as a Galentine's or group outing.</p>

<h2>Tickets and Details</h2>
<p>Tickets start at $40 and tend to sell out. The museum is at 100 Queen's Park, directly above Museum station on Line 1. The event is 19+.</p>

<div class="callout">
<h3>ROM After Dark: Valentines</h3>
<p>February 14, 2026 | 7:30 PM - 11:00 PM | Royal Ontario Museum</p>
<div class="detail"><span>From $40</span><span>19+</span><span>100 Queen's Park</span></div>
</div>"""),

    ("paul-mccartney-photographs-ago-2026",
     "Paul McCartney Photography Exhibition Opens at the AGO This February",
     "Paul McCartney Photographs 1963-1964: Eyes of the Storm opens at the Art Gallery of Ontario, featuring intimate photos from the early days of Beatlemania.",
     "Paul McCartney AGO, Eyes of the Storm Toronto, Art Gallery of Ontario 2026, Toronto exhibitions, Beatles photography Toronto",
     "event", "Event",
     "toronto-event-calendar.jpg",
     "February 10, 2026",
     """<p>The Art Gallery of Ontario opens one of its most anticipated exhibitions of 2026 this month: <strong>Paul McCartney Photographs 1963-1964: Eyes of the Storm.</strong></p>

<h2>About the Exhibition</h2>
<p>The exhibition features intimate photographs taken by Paul McCartney himself during the explosive early days of Beatlemania. Using a 35mm camera, McCartney captured candid moments of the band, their fans, and the surreal world they inhabited as they became the biggest act in music history.</p>
<p>These are not professional press photos. They are personal snapshots from inside the phenomenon, shot by one of the four people at its centre. The perspective is unique in music history.</p>

<h2>What the AGO Has Planned for 2026</h2>
<p>The McCartney exhibition is part of an ambitious 2026 lineup at the AGO that also includes:</p>
<ul>
<li><strong>Edna Tacon</strong> (February 28 - August 31) &mdash; Rarely seen paintings by the late Toronto-based artist</li>
<li><strong>Monet</strong> (coming later in 2026) &mdash; A major Impressionist exhibition</li>
<li><strong>Melissa Auf der Maur</strong> (later in 2026) &mdash; The musician-turned-photographer's work</li>
</ul>

<h2>AGO Visiting Tips</h2>
<p>The AGO is at 317 Dundas Street West, steps from St. Patrick station on Line 1. Wednesday evenings after 6 PM offer free general admission (special exhibitions like McCartney require a separate ticket). The AGO gift shop and FRANK restaurant are destinations in their own right.</p>

<div class="callout">
<h3>Paul McCartney Photographs 1963-1964: Eyes of the Storm</h3>
<p>Opens February 2026 - June 7, 2026 | Art Gallery of Ontario</p>
<div class="detail"><span>317 Dundas St. W.</span><span>Ticketed exhibition</span></div>
</div>"""),

    ("toronto-comicon-2026",
     "Toronto Comicon 2026: Everything You Need to Know for March 20-22",
     "Toronto Comicon returns to Metro Toronto Convention Centre March 20-22 with exhibitors, panels, cosplay, celebrity guests, and gaming. Complete guide.",
     "Toronto Comicon 2026, comic con Toronto, Metro Convention Centre events, cosplay Toronto, Toronto geek events, March Break Toronto",
     "event", "Event",
     "upcoming-toronto-events.jpg",
     "February 9, 2026",
     """<p><strong>Toronto Comicon 2026</strong> takes over the Metro Toronto Convention Centre on <strong>March 20-22</strong>, bringing together fans of comics, sci-fi, fantasy, horror, anime, gaming, and cosplay for one of the city's biggest pop culture weekends.</p>

<h2>What to Expect</h2>
<p>Comicon is a three-day celebration of fandom culture featuring:</p>
<ul>
<li><strong>Exhibitor hall</strong> with hundreds of vendors selling comics, collectibles, artwork, and memorabilia</li>
<li><strong>Celebrity meet-and-greets</strong> and photo opportunities (guests announced closer to the event)</li>
<li><strong>Panel discussions</strong> covering comics, film, TV, and gaming</li>
<li><strong>Cosplay competition</strong> with prizes for best costumes</li>
<li><strong>Gaming zone</strong> with retro and modern games</li>
<li><strong>Artist Alley</strong> where independent creators sell original work and do live sketches</li>
</ul>

<h2>Timing Is Everything</h2>
<p>Comicon 2026 lands on the final weekend of March Break, making it an ideal family outing. Saturday is typically the busiest day, with cosplay peaking in the afternoon. Friday evening and Sunday morning tend to be the least crowded for those who want more browsing time.</p>

<h2>Getting There</h2>
<p>The Metro Toronto Convention Centre is at 255 Front Street West, accessible via Union Station (Line 1) and a short walk through the PATH. Weekend parking rates in the area are steep; TTC is recommended.</p>

<div class="callout">
<h3>Toronto Comicon 2026</h3>
<p>March 20-22, 2026 | Metro Toronto Convention Centre</p>
<div class="detail"><span>255 Front St. W.</span><span>Tickets required</span><span>All ages</span></div>
</div>"""),

    ("march-break-toronto-2026-family-guide",
     "March Break 2026 in Toronto: 15 Best Activities for Families",
     "Complete guide to March Break 2026 in Toronto (March 14-22). ROM, AGO, LEGOLAND, Toronto Zoo, Young People's Theatre, and more family activities.",
     "March Break Toronto 2026, family activities Toronto, kids events Toronto, ROM March Break, AGO March Break, LEGOLAND Toronto, Toronto Zoo",
     "event", "Event",
     "things-to-do-toronto.jpg",
     "February 9, 2026",
     """<p>March Break 2026 runs <strong>March 14-22</strong> in Ontario, and Toronto has no shortage of activities for families. Here are 15 of the best things to do with kids during the break.</p>

<h2>Museums and Science</h2>

<div class="venue-card">
<h3>1. Royal Ontario Museum &mdash; Sharks Exhibition</h3>
<p>The ROM's blockbuster Sharks exhibition runs through March 22, making March Break the last chance to see it. Interactive activities explore shark anatomy, behavior, and marine ecosystems.</p>
<p class="addr">100 Queen's Park | From $20.75 (kids)</p>
</div>

<div class="venue-card">
<h3>2. Art Gallery of Ontario</h3>
<p>Special hands-on art activities, interactive installations, and creative play sessions designed for kids. Plus the new Paul McCartney photography exhibition for the adults.</p>
<p class="addr">317 Dundas St. W. | Free for kids under 25</p>
</div>

<div class="venue-card">
<h3>3. Ontario Science Centre (at Flip Out)</h3>
<p>While the original building undergoes reconstruction, Science Centre programming continues at interim locations with hands-on science experiments and demonstrations.</p>
</div>

<h2>Entertainment</h2>

<div class="venue-card">
<h3>4. LEGOLAND Discovery Centre</h3>
<p>Themed rides, play areas, a 4D cinema, and MINILAND featuring Toronto landmarks built from millions of LEGO bricks.</p>
<p class="addr">Vaughan Mills | Advance tickets recommended</p>
</div>

<div class="venue-card">
<h3>5. Young People's Theatre &mdash; "Love You Forever ... and More Munsch"</h3>
<p>A whimsical adaptation of Robert Munsch's beloved stories, perfect for ages 4-10.</p>
<p class="addr">165 Front St. E.</p>
</div>

<div class="venue-card">
<h3>6. Pinocchio &mdash; National Ballet of Canada</h3>
<p>A family-friendly ballet adaptation with Canadian twists, magical effects, and a full orchestra. Playing March 13-22 at the Four Seasons Centre.</p>
<p class="addr">145 Queen St. W.</p>
</div>

<div class="venue-card">
<h3>7. Toronto Comicon (March 20-22)</h3>
<p>Comics, cosplay, gaming, and celebrity guests at the Metro Toronto Convention Centre. Falls on the final March Break weekend.</p>
</div>

<h2>Animals and Nature</h2>

<div class="venue-card">
<h3>8. Toronto Zoo</h3>
<p>March Break programming with special animal encounters, keeper talks, and educational activities. Dress warm for outdoor exhibits.</p>
<p class="addr">2000 Meadowvale Rd. | Open 9:30 AM - 4:30 PM</p>
</div>

<div class="venue-card">
<h3>9. Ripley's Aquarium of Canada</h3>
<p>Walk through the underwater tunnel, touch stingrays, and watch diver feeding shows. Open extended hours during March Break.</p>
<p class="addr">288 Bremner Blvd.</p>
</div>

<h2>Active Fun</h2>

<div class="venue-card">
<h3>10. Hotel X Retro Arcade</h3>
<p>A pop-up retro arcade at Hotel X Toronto running February 13 through March 22. Classic games, modern comforts.</p>
</div>

<div class="venue-card">
<h3>11. The Rec Room</h3>
<p>VR games, ping pong, shuffleboard, arcade games, and bowling. A family-friendly entertainment centre at Roundhouse Park.</p>
<p class="addr">255 Bremner Blvd.</p>
</div>

<h2>Free and Outdoor</h2>

<div class="venue-card">
<h3>12. Winter Stations at Woodbine Beach</h3>
<p>Free outdoor art installations along the boardwalk. Combine with a walk through the Beaches neighbourhood.</p>
</div>

<div class="venue-card">
<h3>13. Lumiere at Ontario Place</h3>
<p>Free outdoor light art exhibition at Trillium Park. Running through March 27.</p>
</div>

<div class="venue-card">
<h3>14. Toronto History Museums</h3>
<p>All 10 City of Toronto history museums offer free general admission year-round, including Fort York, Spadina Museum, and Todmorden Mills.</p>
</div>

<div class="venue-card">
<h3>15. High Park</h3>
<p>Toronto's largest public park has trails, playgrounds, a small zoo (free), and Grenadier Pond. Check if the High Park Zoo animals are in their spring rotation.</p>
</div>

<div class="callout">
<h3>March Break 2026</h3>
<p>March 14-22, 2026 | Plan ahead: popular venues sell out</p>
<div class="detail"><span>Book ROM and LEGOLAND in advance</span></div>
</div>"""),

    ("wavelength-music-festival-toronto-2026",
     "Wavelength Music Festival 2026: Toronto's Best Indie Music Event Returns March 19-21",
     "Wavelength Music Festival brings 30+ live acts to venues across Toronto's west end March 19-21. Workshops, panels, and indie music discovery.",
     "Wavelength Music Festival Toronto, indie music Toronto, live music Toronto March 2026, Toronto music festivals, west end Toronto events",
     "event", "Event",
     "toronto-events.jpg",
     "February 8, 2026",
     """<p>The <strong>Wavelength Music Festival + Conference</strong> returns to Toronto on <strong>March 19-21, 2026</strong>, taking over multiple venues in the city's west end for three days of indie music, panels, and creative community.</p>

<h2>What Makes Wavelength Special</h2>
<p>Unlike Toronto's larger festivals, Wavelength is artist-centric. It prioritizes discovery over star power, showcasing 30+ live acts across intimate venues where you can stand three feet from the stage. The festival has a track record of spotlighting artists before they break out.</p>

<h2>2026 Venues</h2>
<p>This year's festival spans several west-end venues:</p>
<ul>
<li><strong>St. Anne's</strong> &mdash; The stunning Byzantine-style church hosts the festival's showcase events</li>
<li><strong>Art Gallery of Ontario (AGO)</strong> &mdash; Special programming inside the gallery</li>
<li><strong>The Baby G</strong> &mdash; Intimate Dundas West venue for late-night sets</li>
<li><strong>The Garrison</strong> &mdash; Dundas West's beloved indie music bar</li>
<li><strong>InterAccess</strong> &mdash; Electronic art and media installations</li>
<li><strong>Lula Lounge</strong> &mdash; World music and dance performances</li>
</ul>

<h2>Beyond the Music</h2>
<p>Wavelength also runs a conference track with workshops, panels, and guided tours that celebrate the creative community of Toronto's west end. It is as much about connecting people as it is about the performances.</p>

<div class="callout">
<h3>Wavelength Music Festival 2026</h3>
<p>March 19-21, 2026 | Multiple west-end venues</p>
<div class="detail"><span>30+ live acts</span><span>Workshops and panels</span><span>Tickets required</span></div>
</div>"""),

    # ══════════════════════════════════════════════════════════════
    # THINGS TO DO CATEGORY
    # ══════════════════════════════════════════════════════════════

    ("best-free-skating-rinks-toronto-2026",
     "Best Free Outdoor Skating Rinks in Toronto: 2026 Winter Guide",
     "Guide to the best free outdoor skating rinks in Toronto including Nathan Phillips Square, The Bentway, and Harbourfront Centre. Hours, skate rentals, and tips.",
     "free skating Toronto, outdoor skating rinks Toronto, Nathan Phillips Square skating, The Bentway skating, Harbourfront Centre skating, winter activities Toronto",
     "thingstodo", "Things to Do",
     "things-to-do-toronto.jpg",
     "February 11, 2026",
     """<p>Toronto has some of the best free outdoor skating in the world. Here is your guide to the city's top rinks, what to expect, and how to make the most of each one.</p>

<h2>The Big Three</h2>

<div class="venue-card">
<h3>Nathan Phillips Square</h3>
<p>Toronto's most iconic skating rink, set in front of the famous <strong>TORONTO</strong> sign and City Hall. Skate under the stars with the downtown skyline as your backdrop. Free admission; skate rentals available on-site.</p>
<p class="addr">100 Queen St. W. | Line 1: Osgoode or Queen station</p>
</div>

<div class="venue-card">
<h3>The Bentway</h3>
<p>One of the most creative urban reclamation projects in the country. The Bentway's figure-eight skating trail runs under the Gardiner Expressway, with DJ nights, art installations, and a cozy warming area. Free admission and skate lending library. <strong>Final day: February 16 (Family Day).</strong></p>
<p class="addr">250 Fort York Blvd. | Line 1: Bathurst station</p>
</div>

<div class="venue-card">
<h3>Harbourfront Centre</h3>
<p>Skate by the lake with views of the Toronto Islands and the harbour. The rink hosts DJ Skate Nights (through February 14) with live DJ sets while you skate. Free admission; skate rentals available.</p>
<p class="addr">235 Queens Quay W. | 509/510 streetcar</p>
</div>

<h2>Hidden Gem Rinks</h2>

<div class="venue-card">
<h3>Colonel Samuel Smith Park</h3>
<p>A large, natural outdoor rink in Etobicoke that feels like skating in the countryside. Less crowded than downtown rinks with a beautiful park setting.</p>
<p class="addr">3145 Lake Shore Blvd. W.</p>
</div>

<div class="venue-card">
<h3>Dufferin Grove Park</h3>
<p>A community-run rink with a famous wood-fired bake oven nearby. Hot chocolate and fresh bread after skating make this a neighbourhood favourite.</p>
<p class="addr">875 Dufferin St.</p>
</div>

<div class="venue-card">
<h3>Evergreen Brick Works</h3>
<p>A smaller rink set in the beautiful Don Valley. Combine with a visit to the Saturday Farmers' Market and a hike on the valley trails.</p>
<p class="addr">550 Bayview Ave.</p>
</div>

<h2>Pro Tips</h2>
<ul>
<li>Weekday afternoons are the least crowded at all rinks</li>
<li>Bring your own skates to skip rental lines</li>
<li>Nathan Phillips Square rink is open late (usually until 10 PM) for romantic evening skates</li>
<li>Check ice conditions online before heading out after warm spells</li>
<li>Most rinks close by mid-March; do not wait too long</li>
</ul>"""),

    ("toronto-best-new-restaurants-winter-2026",
     "Toronto's 10 Most Exciting New Restaurants to Try Right Now",
     "The hottest new restaurant openings in Toronto for winter 2026. From Michelin-calibre omakase to Lebanese fast-casual, these 10 spots are generating serious buzz.",
     "new restaurants Toronto 2026, best restaurants Toronto, Toronto food, Toronto dining, restaurant openings Toronto, where to eat Toronto",
     "thingstodo", "Things to Do",
     "toronto-events.jpg",
     "February 11, 2026",
     """<p>Toronto's restaurant scene never slows down. Here are the 10 most exciting new openings generating buzz across the city right now.</p>

<div class="venue-card">
<h3>1. MSSM &mdash; Yorkville</h3>
<p>A 14-course edomae-style omakase experience overseen by chef Masaki Saito (two-Michelin-star pedigree). This is one of the most exclusive dining experiences in Canada, with just a handful of seats per service.</p>
<p class="addr">154 Cumberland St., 2nd Floor</p>
</div>

<div class="venue-card">
<h3>2. Chez Nad by Nadege &mdash; Queen West</h3>
<p>Modern French bistronomie from Nadege Nourian, the founder of Nadege Patisserie. Chef Laura Maxwell leads the kitchen with 20+ years in French fine dining. Opened for dinner service February 6, 2026.</p>
<p class="addr">780 Queen St. W.</p>
</div>

<div class="venue-card">
<h3>3. Osteria Alba &mdash; Little Italy</h3>
<p>Executive chef Adam Pereira serves Italian classics with subtle French and Mediterranean nods. Part of Little Italy's genuine restaurant revival on College Street. Opened February 2, 2026.</p>
<p class="addr">665 College St.</p>
</div>

<div class="venue-card">
<h3>4. Riley's Fish &amp; Steak &mdash; Financial District</h3>
<p>A Michelin-recommended Vancouver import taking over the massive 8,000 sq ft former Shore Club space beneath RBC Tower. One of the most anticipated openings of 2026, serving lunch, dinner, and weekend brunch.</p>
<p class="addr">144 Wellington St. W.</p>
</div>

<div class="venue-card">
<h3>5. Sadelle's &mdash; Yorkville</h3>
<p>The first Canadian location of this famous New York brunch institution, located inside the Kith flagship store. The Salmon Tower alone is worth the trip. Toronto-exclusive sandwiches and Kith cereal treats.</p>
<p class="addr">78 Yorkville Ave., 2nd Floor</p>
</div>

<div class="venue-card">
<h3>6. Little Baba by Amal &mdash; King West</h3>
<p>Fast-casual Lebanese from the team behind Michelin-recommended Amal. Opened January 2026 with approachable prices and the same quality ingredients that earned the original restaurant its accolades.</p>
<p class="addr">75 Portland St.</p>
</div>

<div class="venue-card">
<h3>7. Liliana &mdash; West Queen West</h3>
<p>Chef Marvin Palomo's 30-seat, low-lit restaurant blending Italian with Asian creative touches (Korean, Japanese, Filipino). The beef carpaccio with furikake is a standout. Halal-friendly.</p>
<p class="addr">1198 Queen St. W.</p>
</div>

<div class="venue-card">
<h3>8. Sal's Pasta and Chops &mdash; Little Italy</h3>
<p>Italian-Canadian classics with tableside tagliatelle and wine on tap. From the team formerly behind Lucia in the Junction Triangle. Family-gathering energy.</p>
<p class="addr">614 College St.</p>
</div>

<div class="venue-card">
<h3>9. Tono by Akira Back &mdash; Yorkville</h3>
<p>World-renowned chef Akira Back's Nikkei (Japanese-Peruvian) cuisine atop the W Toronto Hotel. Inventive sushi, sleek rooftop views, and the 9th-floor Skylight bar downstairs.</p>
<p class="addr">W Toronto Hotel, Bloor St. W.</p>
</div>

<div class="venue-card">
<h3>10. Marugame Udon &mdash; Yonge &amp; Dundas</h3>
<p>A world-famous Japanese udon chain with 1,000+ locations globally, opening its first Toronto location. Freshly made udon noodles prepared teppan-style in front of customers.</p>
<p class="addr">494 Yonge St.</p>
</div>

<h2>The Trend</h2>
<p>The common thread across 2026's hottest openings: chef-driven concepts from respected names, whether it is Michelin pedigree (MSSM, Riley's), beloved local brands spinning off (Little Baba, Chez Nad), or international imports making their Canadian debut (Sadelle's, Marugame). Toronto's dining scene is competing at a global level.</p>"""),

    ("roundhouse-winter-craft-beer-fest-2026",
     "Roundhouse Winter Craft Beer Fest 2026: Ontario's Best Breweries on February 21",
     "Roundhouse Winter Craft Beer Fest returns February 21 with Ontario-only craft beers, marshmallow roasting, and winter activities at Roundhouse Park near the CN Tower.",
     "Roundhouse craft beer fest, craft beer Toronto, Ontario craft beer, beer festival Toronto 2026, Roundhouse Park events, winter beer fest Toronto",
     "thingstodo", "Things to Do",
     "toronto-events.jpg",
     "February 10, 2026",
     """<p>The <strong>Roundhouse Winter Craft Beer Fest</strong> takes over Roundhouse Park on <strong>Saturday, February 21, 2026</strong>, bringing together some of Ontario's best craft breweries for an afternoon of winter drinking and socializing.</p>

<h2>What Sets This Apart</h2>
<p>Unlike larger beer festivals that include macro breweries and international brands, the Roundhouse fest is <strong>Ontario craft beer only</strong>. This means every pour comes from an independent Ontario brewery, many of which you cannot find at the LCBO. It is a genuine discovery event for craft beer fans.</p>

<h2>Beyond the Beer</h2>
<p>The festival leans into its winter setting with:</p>
<ul>
<li><strong>Marshmallow roasting</strong> over fire pits</li>
<li><strong>Winter activities</strong> in Roundhouse Park</li>
<li><strong>Food vendors</strong> with pairings designed for cold-weather drinking</li>
<li>The backdrop of the CN Tower and Steam Whistle Brewery</li>
</ul>

<h2>Location</h2>
<p>Roundhouse Park is steps from Union Station, the CN Tower, and the Rogers Centre. It is one of Toronto's most accessible event locations. The park itself is built around the historic John Street Roundhouse, a beautifully restored 1897 railway building.</p>

<div class="callout">
<h3>Roundhouse Winter Craft Beer Fest</h3>
<p>Saturday, February 21, 2026 | Roundhouse Park</p>
<div class="detail"><span>Ontario craft beer only</span><span>Tickets required</span><span>19+</span></div>
</div>"""),

    ("toronto-theatre-winter-spring-2026",
     "Toronto Theatre Guide: 8 Must-See Shows Playing Winter-Spring 2026",
     "Guide to the best theatre in Toronto for winter and spring 2026. From Broadway hits to Canadian premieres, here are the shows worth booking.",
     "Toronto theatre, Toronto shows, Broadway Toronto, Mirvish shows 2026, Some Like It Hot Toronto, theatre guide Toronto",
     "thingstodo", "Things to Do",
     "toronto-event-calendar.jpg",
     "February 10, 2026",
     """<p>Toronto's theatre scene is stacked this winter and spring. From Tony Award-winning Broadway transfers to Canadian world premieres, here are 8 shows worth your time and money.</p>

<div class="venue-card">
<h3>1. Some Like It Hot (Feb 10 - Mar 15)</h3>
<p>Winner of more awards than any show its season, including Best Musical from the Drama Desk, Drama League, and Outer Critics Circle. High-energy jazz-age romp based on the classic Billy Wilder film. A crowd-pleaser in every sense.</p>
<p class="addr">CAA Ed Mirvish Theatre | From $49</p>
</div>

<div class="venue-card">
<h3>2. Shucked (Feb 25 - Apr 5)</h3>
<p>Hit Broadway musical comedy that defies easy description. Corn puns, country music, and genuine heart. Opening at the Royal Alexandra Theatre before moving to Princess of Wales.</p>
<p class="addr">Royal Alexandra / Princess of Wales Theatre</p>
</div>

<div class="venue-card">
<h3>3. Cyrano (Mar 14 - Apr 5)</h3>
<p>A fresh theatrical adaptation of the classic romantic tale. Playing at the intimate CAA Theatre in the Mirvish district.</p>
<p class="addr">CAA Theatre, 300 King St. W.</p>
</div>

<div class="venue-card">
<h3>4. Pinocchio &mdash; National Ballet of Canada (Mar 13-22)</h3>
<p>Family-friendly ballet with Canadian twists and magical stage effects. The full National Ballet orchestra elevates this beyond a typical children's show. March Break timing makes this ideal for families.</p>
<p class="addr">Four Seasons Centre, 145 Queen St. W.</p>
</div>

<div class="venue-card">
<h3>5. Through the Eyes of God (Feb 1-21)</h3>
<p>World premiere by Anusree Roy, a sequel to her award-winning 2007 solo hit "Pyaasa." Canadian theatre at its most personal and powerful.</p>
</div>

<div class="venue-card">
<h3>6. Summer and Smoke (Feb 3 - Mar 5)</h3>
<p>Tennessee Williams classic co-produced by Crowpepper and Birdland Theatre. Headlined by bahia watson and Dan Mousseau. Intimate and emotionally devastating.</p>
</div>

<div class="venue-card">
<h3>7. The Surrogate (Feb 24 - Mar 22)</h3>
<p>New production at Crow's Theatre, one of Toronto's most exciting independent theatre companies. The Crow's Theatre space in Leslieville is worth visiting for the architecture alone.</p>
</div>

<div class="venue-card">
<h3>8. Little Willy &mdash; Ronnie Burkett (Feb 27 - Apr 5)</h3>
<p>Ronnie Burkett's Theatre of Marionettes. Burkett is a living legend of Canadian puppetry, and his shows are unlike anything else in Toronto theatre. For adults.</p>
</div>

<h2>Booking Tips</h2>
<ul>
<li>Mirvish shows (Some Like It Hot, Shucked, Cyrano) offer student and rush tickets</li>
<li>Tuesday and Wednesday evening performances are typically the least crowded</li>
<li>The King Street Theatre District is walkable from St. Andrew station (Line 1)</li>
<li>National Ballet matinees sell out during March Break; book early</li>
</ul>"""),

    # ══════════════════════════════════════════════════════════════
    # NEIGHBOURHOOD CATEGORY
    # ══════════════════════════════════════════════════════════════

    ("whats-new-yonge-dundas-sankofa-square-2026",
     "What's New Near Sankofa Square: Downtown Toronto's Hottest New Spots",
     "Guide to new restaurants, shops, and changes near Yonge and Dundas (Sankofa Square). Marugame Udon, Ema-Datsi Bhutanese, KaleMart24, Ontario Line, and more.",
     "Sankofa Square Toronto, Yonge Dundas Toronto, new restaurants downtown Toronto, Marugame Udon Toronto, things to do downtown Toronto, Ontario Line construction",
     "neighbourhood", "Neighbourhood",
     "toronto-events.jpg",
     "February 11, 2026",
     """<p>The intersection of Yonge and Dundas, now officially <strong>Sankofa Square</strong>, is one of the most dynamic corners in Toronto. Here is what is new and changing in the neighbourhood.</p>

<h2>New Restaurants and Food</h2>

<div class="venue-card">
<h3>Marugame Udon &mdash; 494 Yonge Street</h3>
<p>A world-famous Japanese udon chain with over 1,000 locations globally is opening its <strong>first Toronto location</strong>. Freshly made udon noodles prepared teppan-style in front of customers. A major addition to the Yonge Street food corridor.</p>
</div>

<div class="venue-card">
<h3>Ema-Datsi Bhutanese Cuisine &mdash; 335 Yonge Street</h3>
<p>Toronto's <strong>first Bhutanese food kiosk</strong> at the World Food Market, just steps north of Sankofa Square. Family-owned and operated, serving fiery chilli-cheese dishes, home-made curries, and slow-simmered meats. A genuinely unique culinary addition.</p>
</div>

<div class="venue-card">
<h3>KaleMart24 &mdash; 601-603 Yonge Street (Opening June 2026)</h3>
<p>Montreal's health-focused 24/7 convenience store is opening its <strong>first Toronto location</strong> in a beautiful four-storey red-brick heritage building. Fresh grab-and-go meals, healthy snacks, and technology-enabled checkout.</p>
</div>

<div class="venue-card">
<h3>More Nearby Eats</h3>
<p><strong>Muji Coffee</strong> (20 Dundas St. W.) serves robot-prepared coffee. <strong>Afro's Pizza</strong> (107 Mutual St.) went viral after a Keith Lee review. <strong>Hailed Coffee</strong> (44 Gerrard St. W.) brings Middle Eastern artisanal coffee. <strong>Coti Coffee</strong> (374 Yonge St.) starts at $0.99.</p>
</div>

<h2>What's Happening at the Square</h2>
<p>Sankofa Square has <strong>172 event days confirmed for 2026</strong>, exceeding all of 2025 by 25%. The renamed square (Sankofa is an Akan word meaning "to go back and get it") is bouncing back after a difficult 2025 that saw revenue drop $700,000 amid protests and reduced U.S. brand activations.</p>
<p>Current and upcoming events include:</p>
<ul>
<li><strong>OCAD University Black History Month Exhibition</strong> (all February) &mdash; Digital artworks on five screens</li>
<li><strong>ILLUMINITE</strong> (Feb 13 - Mar 8) &mdash; Light installations as part of the larger Downtown Yonge festival</li>
<li>Lunchtime programming, markets, movie nights, and soccer activations throughout 2026</li>
</ul>

<h2>Ontario Line Construction</h2>
<p>The biggest change coming to the area is the <strong>Ontario Line subway</strong>, a 15.6-kilometre line that will run from Exhibition Place through downtown to Don Mills Road with 15 new stations. Construction is actively underway with support-of-excavation and piling work. Estimated completion: 2031. The new Queen Station interchange will be steps from Sankofa Square.</p>

<h2>Development Watch</h2>
<ul>
<li><strong>Concord Sky</strong> (391 Yonge St.) &mdash; 1,100-unit residential tower completing in 2026</li>
<li><strong>Pinnacle One Yonge SkyTower</strong> &mdash; 220-room hotel and 950+ residences opening fall 2026</li>
<li><strong>Elektra Condos</strong> (218 Dundas St. E.) &mdash; Cancelled due to insufficient buyers, reflecting condo market challenges</li>
</ul>"""),

    ("yorkville-bloor-restaurants-luxury-guide-2026",
     "Yorkville and Bloor: Toronto's Luxury Dining and Shopping Boom in 2026",
     "New Michelin-calibre restaurants, luxury retail flagships, and museum exhibitions make Yorkville the most dynamic neighbourhood in Toronto right now.",
     "Yorkville restaurants Toronto, Bloor Street luxury, new restaurants Yorkville 2026, MSSM Toronto, Sadelle's Toronto, ROM exhibitions, Gardiner Museum",
     "neighbourhood", "Neighbourhood",
     "toronto-event-calendar.jpg",
     "February 11, 2026",
     """<p>Yorkville is in the middle of a remarkable transformation. New Michelin-calibre restaurants, international luxury brands, and museum renovations are making this small neighbourhood arguably the most exciting square kilometre in Canada right now.</p>

<h2>The Restaurant Boom</h2>

<div class="venue-card">
<h3>MSSM &mdash; 154 Cumberland Street</h3>
<p>A 14-course edomae-style omakase overseen by chef Masaki Saito, who runs the two-Michelin-star Sushi Masaki Saito. Lunch and dinner. One of the most exclusive dining experiences in Canada.</p>
</div>

<div class="venue-card">
<h3>St. Thomas Restaurant and Wine Bar &mdash; 23 St. Thomas Street</h3>
<p>Spanish-inspired small plates from chef-owner Quinton Bennett, who also runs one-Michelin-starred Enigma. Seasonal, locally sourced, with a serious wine program.</p>
</div>

<div class="venue-card">
<h3>Sadelle's &mdash; 78 Yorkville Avenue</h3>
<p>First Canadian location of the famous New York brunch spot, inside the Kith flagship. The Salmon Tower, Toronto-exclusive sandwiches, and Kith Treats cereal bar.</p>
</div>

<div class="venue-card">
<h3>Tono by Akira Back &mdash; W Toronto Hotel</h3>
<p>World-renowned chef Akira Back brings Nikkei (Japanese-Peruvian) cuisine to a rooftop setting with skyline views. Skylight bar on the 9th floor serves cocktails.</p>
</div>

<div class="venue-card">
<h3>Paros &mdash; 119 Yorkville Avenue</h3>
<p>Modern Greek from executive chef Jack Connacher. Contemporary takes on classic dishes with quality ingredients and a cocktail menu.</p>
</div>

<h2>Luxury Retail Expansion</h2>
<p>Bloor Street is cementing its position as Canada's pre-eminent luxury shopping corridor:</p>
<ul>
<li><strong>Van Cleef &amp; Arpels</strong> &mdash; Opening at 100 Bloor St. W.</li>
<li><strong>Harry Rosen</strong> &mdash; 38,000 sq ft flagship on Cumberland (spring 2026), part of a $50M national investment</li>
<li><strong>Saint Laurent</strong> &mdash; 10,400 sq ft flagship at 110 Bloor St. W.</li>
<li><strong>Alexander Wang</strong> &mdash; First Toronto boutique at 110 Bloor St. W.</li>
<li><strong>Salvatore Ferragamo</strong> &mdash; New flagship at 131 Bloor St. W., between Dior and Prada</li>
<li><strong>Bang &amp; Olufsen</strong> &mdash; Returning to 135 Yorkville Ave. with a new flagship</li>
<li><strong>Rolex</strong> &mdash; One of North America's largest boutiques at 101 Bloor St. W.</li>
</ul>

<h2>Museums Worth Visiting Right Now</h2>

<div class="venue-card">
<h3>Royal Ontario Museum</h3>
<p><strong>Sharks</strong> (through March 22) | <strong>Wildlife Photographer of the Year</strong> | <strong>Crawford Lake: Layers in Time</strong> (through September 2026) | Upcoming: <strong>Shokkan: Japanese Art Through Touch</strong> (April 4)</p>
<p class="addr">100 Queen's Park</p>
</div>

<div class="venue-card">
<h3>Gardiner Museum (Newly Reopened)</h3>
<p>Reopened after a <strong>$15.5 million renovation</strong>. Features <strong>Linda Rotua Sormin: Uncertain Ground</strong> (through April 12) and a new permanent <strong>Indigenous Immemorial</strong> gallery dedicated to ceramics from the Great Lakes region.</p>
<p class="addr">111 Queen's Park</p>
</div>

<h2>What Makes Yorkville Special Right Now</h2>
<p>Within walking distance, you have two-Michelin-star-pedigree omakase, a $15.5M museum renovation, North America's largest Rolex boutique, and wellness concepts like Othership bathhouse (sauna, ice baths, breathwork). Plus the $1.5 billion Bloor-Yonge station expansion underway. The density of world-class experiences in this small area is unmatched in Canada.</p>"""),

    ("king-west-portland-square-restaurant-guide-2026",
     "King West's Restaurant Revolution: Portland Square and the New Wave",
     "King West's dining scene explodes with Portland Square mega food hall, Little Baba by Amal, Cafe Renee, and Riley's Fish and Steak. Restaurant guide for 2026.",
     "King West restaurants Toronto, Portland Square Toronto, new restaurants King West 2026, Little Baba Amal, Cafe Renee Toronto, Riley's Fish Steak",
     "neighbourhood", "Neighbourhood",
     "things-to-do-toronto.jpg",
     "February 10, 2026",
     """<p>King West has always been Toronto's party neighbourhood. In 2026, it is becoming a serious dining destination. A wave of new restaurants, from mega food halls to Michelin-recommended spinoffs, is reshaping the strip.</p>

<h2>Portland Square: Four Restaurants in One</h2>
<p>The biggest opening is <strong>Portland Square</strong> at King and Portland, a massive multi-level dining and entertainment complex with four distinct concepts under one roof:</p>
<ul>
<li><strong>Honey Chinese</strong> (3rd floor) &mdash; King West's only Chinese restaurant. Finally.</li>
<li><strong>Rodeo Dive</strong> (main level) &mdash; Country music-themed sports bar with oversized screens and draft beer towers</li>
<li>Two additional concepts rounding out a building designed for spending the entire evening in one address</li>
</ul>

<h2>The New Must-Try Spots</h2>

<div class="venue-card">
<h3>Little Baba by Amal &mdash; 75 Portland Street</h3>
<p>Fast-casual Lebanese from the team behind Michelin-recommended Amal. Opened January 2026 with the same quality at approachable prices. This is the trend: fine dining brands launching accessible spinoffs.</p>
</div>

<div class="venue-card">
<h3>Cafe Renee &mdash; Portland Street</h3>
<p>French pasta-focused restaurant with greenhouse-like glass walls and skylights. The viral ravioles de Dauphine are worth the hype. Premium option: spaghetti with uni cream or gnocchi with caviar. Feels like dining inside a Parisian greenhouse.</p>
</div>

<div class="venue-card">
<h3>Riley's Fish &amp; Steak &mdash; 144 Wellington Street West</h3>
<p>Michelin-recommended Vancouver import taking over the massive former Shore Club space (8,000 sq ft beneath RBC Tower). Opening mid-to-late February 2026. Lunch, dinner, and weekend brunch seven days a week.</p>
</div>

<div class="venue-card">
<h3>Chamberlains Pony Bar &mdash; King &amp; Portland</h3>
<p>Tex-Mex with oversized draft beers and an extensive margarita selection (spicy, mango, melon, black currant, passion fruit). Chorizo tacos and late-night energy.</p>
</div>

<div class="venue-card">
<h3>Vinny &mdash; King West</h3>
<p>A listening bar where spinning LPs provide the soundtrack. Inspired by the soulful spirit of the 1970s. Part of the growing listening bar trend across Toronto.</p>
</div>

<h2>Waterworks Food Hall Updates</h2>
<p>The Waterworks Food Hall at 50 Brant Street is adding three new vendors in 2026:</p>
<ul>
<li><strong>Bello Pizza</strong> &mdash; Slow-fermented dough with inventive Italian comfort food</li>
<li><strong>Darna Middle Eastern Cuisine</strong> &mdash; Charcoal-grilled meats and vibrant mezze</li>
<li><strong>Union Chicken</strong> &mdash; Buttermilk fried chicken sandwiches and waffles</li>
</ul>

<h2>The King West Trend</h2>
<p>The neighbourhood is doubling down on multi-concept complexes (Portland Square), fast-casual from fine dining (Little Baba), and experiential dining (Cafe Renee's greenhouse, Vinny's vinyl). The era of King West as just a nightclub strip is evolving into something more interesting.</p>"""),

    ("queen-west-ossington-bars-restaurants-2026",
     "Queen West and Ossington: Toronto's Coolest New Bars and Restaurants",
     "Guide to the hottest new openings on Queen West and Ossington in 2026. Chez Nad, Liliana, No Vacancy, Small Talk, secret bars, and the Michelin-recognized strip.",
     "Queen West restaurants Toronto, Ossington bars Toronto, new bars Toronto 2026, No Vacancy Toronto, Chez Nad Toronto, cocktail bars Toronto",
     "neighbourhood", "Neighbourhood",
     "toronto-events.jpg",
     "February 10, 2026",
     """<p>Queen West and Ossington remain the epicentre of Toronto's creative dining and nightlife scene. The Michelin Guide has designated West Queen West as a destination neighbourhood, and the latest wave of openings proves why.</p>

<h2>Queen West: New Restaurants</h2>

<div class="venue-card">
<h3>Chez Nad by Nadege &mdash; 780 Queen St. W.</h3>
<p>Modern French bistronomie from Nadege Patisserie founder Nadege Nourian. Chef Laura Maxwell brings 20+ years in French kitchens. <strong>Opened February 6, 2026.</strong> This is the kind of restaurant that defines a neighbourhood.</p>
</div>

<div class="venue-card">
<h3>Liliana &mdash; 1198 Queen St. W.</h3>
<p>Chef Marvin Palomo's 30-seat, low-lit restaurant blending Italian with Asian creative touches (Korean, Japanese, Filipino). Halal-friendly. The beef carpaccio with furikake is the dish everyone is talking about.</p>
</div>

<div class="venue-card">
<h3>Cassette &mdash; 1214 Queen St. W.</h3>
<p>Part restaurant, part entertainment venue. Retro-themed with checkered floors, a vinyl room, drag shows, karaoke nights, and live performances. The hybrid dining-entertainment concept done right.</p>
</div>

<h2>Ossington: The Secret Bar Phenomenon</h2>

<div class="venue-card">
<h3>No Vacancy &mdash; Ossington Avenue</h3>
<p>A swanky cocktail bar steering its menu into Japanese waters: sake, Japanese whisky, shochu highballs, and creative cocktails using unusual ingredients. Converted from the former Ghost Chicken space.</p>
</div>

<div class="venue-card">
<h3>Small Talk &mdash; 110 Ossington Avenue</h3>
<p>A kitschy jazz bar with live performances, DJs, a <strong>champagne vending machine</strong>, and wagyu hot dogs. Replaced the beloved Baby Huey. The energy is immaculate.</p>
</div>

<div class="venue-card">
<h3>Bar Raton Laveur &mdash; 130 Foxley Place</h3>
<p>Ultra under-the-radar wine and beer bar with a <strong>private Instagram account</strong>. No reservations, no cocktails. You have to find it first. The secret bar phenomenon is alive and well on Ossington.</p>
</div>

<div class="venue-card">
<h3>Bar Koukla &mdash; 88 Ossington Avenue</h3>
<p>Intimate snack bar by the Mamakas team, inspired by Athenian snack bars. Mezes, seafood, cocktails, and Greek wines in a cozy setting.</p>
</div>

<h2>Notable Closures</h2>
<p><strong>Banu</strong> closed after 20 years on West Queen West. <strong>Cold Tea</strong>, the legendary speakeasy-style bar, also shuttered in fall 2025. <strong>Superpoint</strong> closed abruptly after 9 years on Ossington. The cycle of creative renewal continues.</p>

<h2>The Trend</h2>
<p>Ossington's direction is clear: intimate, concept-driven bars with Japanese influences, natural wine, and speakeasy vibes. Queen West continues to attract chef-driven restaurants that blur cuisines (Italian-Asian, French-bistronomie). Both strips reward exploration.</p>"""),

    ("little-italy-college-street-revival-2026",
     "Little Italy's Restaurant Revival: College Street Is Back",
     "A new wave of Italian restaurants is reviving Toronto's Little Italy on College Street. Osteria Alba, Sal's Pasta and Chops, Lonely Diner, and more.",
     "Little Italy Toronto, College Street restaurants, new restaurants Little Italy 2026, Osteria Alba Toronto, Italian restaurants Toronto, Sal's Pasta Chops",
     "neighbourhood", "Neighbourhood",
     "toronto-events.jpg",
     "February 10, 2026",
     """<p>After years of losing iconic spots (San Francesco Foods after 71 years, Vivoli after 20), Toronto's Little Italy is experiencing a genuine revival. A new generation of restaurants is arriving on College Street that nods to the neighbourhood's roots while adding modern energy.</p>

<h2>The New Wave</h2>

<div class="venue-card">
<h3>Osteria Alba &mdash; 665 College Street</h3>
<p>Executive chef Adam Pereira serves Italian classics with subtle French and Mediterranean influences. <strong>Opened February 2, 2026.</strong> The kind of refined-but-relaxed Italian that College Street has been missing.</p>
</div>

<div class="venue-card">
<h3>Sal's Pasta and Chops &mdash; 614 College Street</h3>
<p>Italian-Canadian classics from Michael Sangregorio and Fabio Bondi (formerly of Lucia in the Junction Triangle). <strong>Tableside tagliatelle</strong>, wine on tap, and a family-gathering atmosphere. This is not trying to be modern; it is trying to be your Italian grandmother's kitchen, and it works.</p>
</div>

<div class="venue-card">
<h3>Lonely Diner &mdash; 432 College Street</h3>
<p>A funky new cocktail bar with Asian-inspired small plates. A collaborative venture from the teams behind Midnight Market, BarChef, Overpressure Club, and After Seven. The kind of place that evolves over the evening from dinner spot to late-night scene.</p>
</div>

<div class="venue-card">
<h3>Contrada &mdash; College Street</h3>
<p>Modern Italian-Canadian celebrating the neighbourhood's heritage with fresh twists. Part of the trend of younger chefs reclaiming Italian cooking from the red-sauce stereotype.</p>
</div>

<div class="venue-card">
<h3>Danny's Pizza Tavern &mdash; College Street</h3>
<p>Thin-crust pies, killer cocktails, and late-night vibes. The kind of casual spot that anchors a neighbourhood.</p>
</div>

<h2>What Was Lost</h2>
<p>The revival is especially meaningful given the closures that preceded it:</p>
<ul>
<li><strong>San Francesco Foods</strong> &mdash; Legendary sandwich shop, closed after 71 years on Clinton Street</li>
<li><strong>Vivoli</strong> &mdash; Closed after 20 years in July 2025</li>
</ul>
<p>These losses represented decades of culinary history. The new wave is not replacing that history so much as building on it.</p>

<h2>The Bigger Picture</h2>
<p>Little Italy's new restaurants are less about red-sauce joints and more about refined pasta programs, natural wines, and chef-driven menus. But the neighbourhood's DNA remains: the Italian grocery stores on Clinton, the espresso bars, the nonnas walking to Mass. The new restaurants understand this context. They are adding to it, not replacing it.</p>"""),

    ("leslieville-east-end-toronto-guide-2026",
     "Leslieville and the East End: What's New and Coming in 2026",
     "Guide to changes in Leslieville, Riverside, and Riverdale. New restaurants, East Harbour transit hub, Ontario Line stations, and neighbourhood evolution.",
     "Leslieville Toronto, Riverdale Toronto, east end Toronto, East Harbour transit, Ontario Line Leslieville, new restaurants Leslieville 2026",
     "neighbourhood", "Neighbourhood",
     "upcoming-toronto-events.jpg",
     "February 9, 2026",
     """<p>Toronto's east end, spanning Leslieville, Riverside, and Riverdale, is in the middle of a transformation driven by massive transit investments and a quietly evolving food scene.</p>

<h2>New on the Dining Scene</h2>

<div class="venue-card">
<h3>Fangio Trattoria &mdash; 1111 Queen St. E.</h3>
<p>Classic Italian that took over the space left by beloved Ascari Enoteca (closed after 15 years due to rising costs). Fangio retains the iconic red Formula 1 racecar logo and serves honest pasta plates and an 11-oz bone-in veal chop. It is filling a genuine gap on Queen East.</p>
</div>

<h2>The Transit Revolution</h2>
<p>Two massive projects are reshaping the east end's future:</p>

<div class="venue-card">
<h3>East Harbour Transit Hub</h3>
<p>Major construction began summer 2025 on what will become a new multi-modal transit hub connecting Lakeshore East and Stouffville GO lines with the future Ontario Line subway. This single project will make the east end dramatically more accessible.</p>
</div>

<div class="venue-card">
<h3>Riverside-Leslieville Ontario Line Station</h3>
<p>A brand new subway station will directly serve Leslieville, Riverside, and Riverdale communities when the Ontario Line opens (estimated 2031). This is a game-changer for an area that has never had rapid transit.</p>
</div>

<h2>What Was Lost</h2>
<p>The east end has seen painful closures recently:</p>
<ul>
<li><strong>Ascari Enoteca</strong> &mdash; Closed after nearly 15 years. Bankruptcy notice cited rising food costs and wages.</li>
<li><strong>Greta Solomon's</strong> &mdash; Intimate 26-seat French bistro closed March 2025.</li>
<li><strong>Barrio</strong> &mdash; Leslieville fixture closed after 9 years.</li>
</ul>

<h2>Why the East End Matters</h2>
<p>Queen Street East through Leslieville and the Beaches remains one of Toronto's best walking streets. The mix of independent shops, brunch spots, vintage stores, and parks (Jimmie Simpson, Woodbine Beach) creates a neighbourhood character that feels more like a small town than a big city. Add the coming transit connections, and the east end's trajectory is clear: this is where Toronto is growing next.</p>

<h2>Worth the Trip</h2>
<ul>
<li><strong>Crow's Theatre</strong> (345 Carlaw Ave.) &mdash; One of Toronto's best independent theatres, in a stunning converted building</li>
<li><strong>Gerrard Street East</strong> &mdash; Toronto's original Chinatown East and Little India</li>
<li><strong>Broadview Hotel</strong> &mdash; Rooftop bar with east-side skyline views</li>
<li><strong>Evergreen Brick Works</strong> &mdash; Saturday farmers' market and valley trails</li>
</ul>"""),

    ("junction-parkdale-west-end-guide-2026",
     "The Junction, Parkdale, and Roncesvalles: Toronto's West End Food Guide",
     "Neighbourhood guide to Toronto's west end dining scene. Taste of the Junction, BB's Diner (Michelin Bib Gourmand), Proper, and multicultural flavours across Parkdale.",
     "Junction Toronto, Parkdale restaurants, Roncesvalles Toronto, west end Toronto food, Taste of the Junction 2026, BB's Diner Parkdale, multicultural food Toronto",
     "neighbourhood", "Neighbourhood",
     "culture-diversity-toronto.jpg",
     "February 9, 2026",
     """<p>Toronto's west end, from the Junction to Parkdale to Roncesvalles, is where the city's multicultural food scene reaches its peak. Here is your neighbourhood-by-neighbourhood guide.</p>

<h2>The Junction</h2>

<div class="callout">
<h3>Taste of the Junction 2026</h3>
<p>Saturday, June 27, 2026, at the Green P lot (385 Pacific Ave.). This year's FIFA-themed edition features <strong>35+ vendors</strong>, a new <strong>augmented reality mural</strong>, and five immersive cultural installations called "Passageways" inspired by the Junction's diverse communities.</p>
<div class="detail"><span>Free admission</span><span>All ages</span></div>
</div>

<p>The Junction maintains one of Toronto's strongest restaurant strips anchored by General Public, Terroni Sterling, and Hoyra. Notable closure: Piri Piri Grill after 25 years.</p>

<h2>Parkdale</h2>
<p>Parkdale's dining scene is defined by <strong>multicultural authenticity</strong>. The neighbourhood's diverse immigrant communities create a food landscape unlike anywhere else in the city:</p>

<div class="venue-card">
<h3>BB's Diner</h3>
<p><strong>Michelin Bib Gourmand</strong> restaurant serving Philippine-inspired cuisine. The Michelin recognition put Parkdale on the global culinary map.</p>
</div>

<div class="venue-card">
<h3>The Multicultural Strip</h3>
<p><strong>NUNA Kitchen &amp; Bar</strong> (Peruvian) | <strong>Afrobeat Kitchen</strong> (Nigerian) | <strong>The MoMo House</strong> (Tibetan/Nepalese) | <strong>Loga's Corner</strong> (Tamil) | <strong>Himalayan Kitchen</strong> (Nepalese) | <strong>Le Baratin</strong> (French). Where else can you eat Peruvian ceviche, Tibetan momos, and Nigerian jollof rice within three blocks?</p>
</div>

<h2>Roncesvalles</h2>

<div class="venue-card">
<h3>Proper &mdash; 392 Roncesvalles Avenue</h3>
<p>Italian-American red-sauce restaurant by chef Julien Cawagas. From-scratch pasta and chicken parmesan that does not apologize for being comfort food. Fills the gap left by La Cubana's closure.</p>
</div>

<p>Roncesvalles' identity is comfort food with Eastern European and Italian-American influences. The Polish-Ukrainian heritage remains strong (<strong>Cafe Polonez</strong>, the Heavenly Perogy team's Ukrainian restaurant), alongside the neighbourhood classics: <strong>Barque Smokehouse</strong>, <strong>The Ace</strong>, <strong>Arbequina</strong>.</p>

<h2>The West End Advantage</h2>
<p>What unites these three neighbourhoods is value. While Yorkville and King West trend upscale, the west end delivers world-class flavours at neighbourhood prices. A Michelin Bib Gourmand meal at BB's Diner, authentic momos at The MoMo House, or tableside pierogi at Cafe Polonez cost a fraction of their downtown equivalents.</p>"""),

    ("danforth-greektown-multicultural-guide-2026",
     "Danforth Greektown Goes Global: Toronto's Multicultural Food Evolution",
     "The Danforth is evolving beyond Greek restaurants. Malaysian, Ethiopian, Turkish, and Persian cuisines join the strip alongside Taste of the Danforth 2026.",
     "Danforth Toronto, Greektown Toronto, Taste of the Danforth 2026, multicultural restaurants Toronto, Danforth restaurants, Greek food Toronto",
     "neighbourhood", "Neighbourhood",
     "culture-diversity-toronto.jpg",
     "February 8, 2026",
     """<p>The Danforth has been Toronto's Greektown since the 1960s. But in 2026, the strip is becoming something more interesting: a genuinely multicultural food corridor where Malaysian, Ethiopian, Turkish, and Persian cuisines sit alongside the traditional tavernas.</p>

<h2>Beyond Greek</h2>

<div class="venue-card">
<h3>Sambal &mdash; The Danforth</h3>
<p>Malaysian and Indonesian flavours in the heart of Greektown. Rendang, nasi goreng, and bakmi ayam bringing Southeast Asian heat to a street previously dominated by souvlaki. A sign of the Danforth's evolution.</p>
</div>

<div class="venue-card">
<h3>Croquembouche &mdash; The Danforth</h3>
<p>A new patisserie-restaurant bringing French-inspired baking to the neighbourhood.</p>
</div>

<div class="venue-card">
<h3>The Multicultural Mix</h3>
<p>Beyond the Greek classics, the Danforth now features: <strong>Rendez-Vous</strong> (Ethiopian) | <strong>Mr. Pide</strong> (Turkish) | <strong>Herby Restaurant</strong> (Persian) | <strong>Beiteddine</strong> (Lebanese). The strip has quietly evolved into one of Toronto's most diverse food streets.</p>
</div>

<h2>Taste of the Danforth 2026</h2>

<div class="callout">
<h3>Taste of the Danforth</h3>
<p>August 11-13, 2026. Running since 1994, this festival has historically attracted <strong>over a million visitors</strong> for Greek food, plate-breaking, live music, dance lessons, carnival rides, and celebrity meet-and-greets. It is one of the largest street festivals in North America.</p>
<div class="detail"><span>Free admission</span><span>Danforth Avenue</span><span>1M+ visitors</span></div>
</div>

<h2>The Greek Core Endures</h2>
<p>The evolution does not mean the Greek identity is fading. The traditional tavernas, bakeries, and coffee shops remain the neighbourhood's backbone. What is happening is addition, not replacement. The Danforth is becoming richer because of its new diversity while keeping the souvlaki, spanakopita, and baklava that made it famous.</p>

<h2>Getting There</h2>
<p>The Danforth runs east from Broadview station along Line 2 (Bloor-Danforth). The best stretch for dining is between Broadview and Pape stations, about a 15-minute walk. The Broadview Hotel's rooftop bar on the western end is a perfect place to start or end an evening.</p>"""),

    ("kensington-market-chinatown-guide-2026",
     "Kensington Market and Chinatown: Toronto's Most Eclectic Food Neighbourhoods",
     "Guide to Kensington Market's Pedestrian Sundays and Chinatown's evolving food scene. R&D, Dai Lo, vintage shops, and the neighbourhoods that resist change.",
     "Kensington Market Toronto, Chinatown Toronto, Pedestrian Sundays 2026, Kensington Market restaurants, Chinatown restaurants, vintage shopping Toronto",
     "neighbourhood", "Neighbourhood",
     "hidden-gems-toronto.jpg",
     "February 8, 2026",
     """<p>Kensington Market and Chinatown sit side by side in Toronto's west downtown, forming one of the most eclectic food and culture zones in any North American city. Here is what makes them special in 2026.</p>

<h2>Kensington Market</h2>

<div class="callout">
<h3>Pedestrian Sundays 2026</h3>
<p>Returns on the <strong>last Sunday of every month from May through October</strong> (starting May 26). Streets close to traffic and fill with live music, food vendors, poetry, dance, community yard sales, and immersive art installations. These are some of the most genuinely joyful events in the city.</p>
<div class="detail"><span>Free</span><span>Last Sunday monthly, May-Oct</span></div>
</div>

<p>Kensington Market actively resists corporate encroachment. There are no chain restaurants, no big-box stores, and the neighbourhood's UNESCO-worthy cultural preservation ethos is maintained by residents and the BIA. What you get instead is vintage clothing stores, cheese shops, fishmongers, Latin American bakeries, independent cafes, and a community that fiercely protects its character.</p>

<h3>Notable Change</h3>
<p>Rasta Pasta closed after 10+ years. The Kensington staple was lost due to landlord repossession for non-payment of rent. Its absence leaves a visible gap on Augusta Avenue.</p>

<h2>Chinatown (Spadina &amp; Dundas)</h2>
<p>One of Toronto's oldest neighbourhoods (established 1878) and the largest Chinatown in North America is in a state of slow regeneration:</p>

<div class="venue-card">
<h3>R&amp;D &mdash; 241 Spadina Avenue</h3>
<p>Modern Canadian-Asian cuisine by Eric Chong and celebrity chef Alvin Leung. Dim sum, inventive mains, and creative cocktails. The bridge between Chinatown's traditional roots and its evolving identity.</p>
</div>

<div class="venue-card">
<h3>Dai Lo &mdash; near College &amp; Spadina</h3>
<p>Elevated Cantonese cuisine that remains one of the area's top restaurants. Chef Nick Liu's cooking is a masterclass in honouring tradition while pushing boundaries.</p>
</div>

<div class="venue-card">
<h3>Midnight Snack Bar</h3>
<p>Inventive teapot cocktails and Japanese-inspired "wafu pastas." Late-night vibes in the heart of Chinatown.</p>
</div>

<h2>Lunar New Year Street Festival</h2>
<p>The <strong>Downtown Chinatown Lunar New Year Street Festival</strong> (February 21-22) on Spadina Avenue features lion and dragon dances, cooking demonstrations, fortune-telling, and cultural booths. Free. Organized by the Downtown Chinatown BIA.</p>

<h2>Why These Neighbourhoods Matter</h2>
<p>In a city where condos are going up on every corner and chain restaurants are spreading, Kensington Market and Chinatown represent something increasingly rare: authentic, community-driven neighbourhoods that prioritize character over commerce. Visit them not just for the food, but for what they represent about Toronto's identity.</p>"""),
]


def build_related_html(current_slug, all_articles):
    others = [a for a in all_articles if a[0] != current_slug]
    picks = random.sample(others, min(4, len(others)))
    cards = []
    for slug, title, _, _, _, _, _, date, _ in picks:
        cards.append(f'''
            <div class="related-card">
                <h3><a href="{slug}.html">{title}</a></h3>
                <div class="meta"><span>{date}</span></div>
            </div>''')
    return '\n'.join(cards)


def main():
    BLOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f'Generating {len(ARTICLES)} new articles in {BLOG_DIR}')
    print()

    for slug, title, desc, keywords, category, tag_label, image, date_str, content_html in ARTICLES:
        related = build_related_html(slug, ARTICLES)
        html = article_template(title, slug, desc, keywords, date_str, category, tag_label, image, content_html, related)
        out_path = BLOG_DIR / f'{slug}.html'
        out_path.write_text(html, encoding='utf-8')
        print(f'  [{category:13s}] {slug}.html')

    print()
    print(f'Done! Generated {len(ARTICLES)} articles.')
    print('Now update the blog index to include these articles.')


if __name__ == '__main__':
    main()
