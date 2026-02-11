#!/usr/bin/env python3
"""
Generate the blog index page with all articles listed.
Run: python tools/generate_blog_index.py
"""
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent / 'TORONTOEVENTS_ANTIGRAVITY' / 'build' / 'blog'

# All articles: (slug, title, excerpt, date_display, category, tag_class, image)
# Ordered newest first
ARTICLES = [
    # Featured
    ("sankofa-square-illuminite-2026.html", "Sankofa Square ILLUMINITE 2026: Toronto's Winter Light Festival Guide",
     "From February 13 to March 8, five Downtown Yonge locations transform with immersive light installations, silent disco skating, and Lunar New Year celebrations.",
     "February 10, 2026", "Featured Event", "featured", "events-in-toronto.jpg"),

    # Breaking News
    ("toronto-2026-budget-events-culture.html", "Toronto's 2026 Budget: What Mayor Olivia Chow's Proposal Means for Events and Culture",
     "Mayor Olivia Chow's 2026 budget proposal goes to City Council. Here's what it means for Toronto's event scene and cultural funding.",
     "February 10, 2026", "Breaking", "breaking", "toronto-events.jpg"),

    ("things-to-do-toronto-this-weekend-february-2026.html", "15 Things to Do in Toronto This Weekend: February 2026 Edition",
     "From outdoor skating to ILLUMINITE light walks to Winterlicious dining, here are 15 can't-miss events happening across the city right now.",
     "February 10, 2026", "Breaking", "breaking", "things-to-do-toronto.jpg"),

    ("eglinton-crosstown-lrt-launch-toronto-events.html", "Eglinton Crosstown LRT Finally Launches: What It Means for Getting to Toronto Events",
     "The long-awaited Eglinton Crosstown LRT begins rush-hour service, opening new connections to event venues across midtown.",
     "February 9, 2026", "Breaking", "breaking", "toronto-events.jpg"),

    ("toronto-relaxes-liquor-laws-olympics-2026.html", "Toronto Relaxes Liquor Laws for Olympics: 6 AM Serving Now Allowed",
     "Bars and restaurants can now serve alcohol starting at 6 AM during the 2026 Milano Cortina Winter Olympics. Early-morning watch parties are on.",
     "February 9, 2026", "Breaking", "breaking", "upcoming-toronto-events.jpg"),

    ("cp24-toronto-breaking-news-events-update.html", "Toronto Breaking News Roundup: How City News Shapes Your Event Calendar",
     "From transit launches to budget debates, breaking news directly impacts things to do in Toronto. Stay informed with CP24, CTV, and Toronto Star coverage.",
     "February 8, 2026", "Breaking", "breaking", "toronto-events.jpg"),

    ("free-events-toronto-february-2026.html", "Toronto's Best Free Events This Month: February 2026",
     "Enjoy Toronto without spending a dime. Sweet City Fest, ILLUMINITE, KUUMBA, free gallery nights, and more free things to do this month.",
     "February 8, 2026", "Breaking", "breaking", "things-to-do-toronto.jpg"),

    ("toronto-home-prices-drop-below-million-2026.html", "Toronto Home Prices Drop Below $1M for First Time in Five Years",
     "Toronto-area average home prices have dropped below $1 million. What this means for the city's communities and creative scene.",
     "February 7, 2026", "Breaking", "breaking", "toronto-events.jpg"),

    ("cyclists-snow-blocked-bike-lanes-toronto-2026.html", "Toronto Cyclists Frustrated by Snow-Blocked Bike Lanes After Record Storm",
     "A record snowstorm has left Toronto bike lanes blocked, highlighting how weather impacts getting to events and activities.",
     "February 6, 2026", "Breaking", "breaking", "toronto-events.jpg"),

    # Sports
    ("winter-olympics-watch-parties-toronto-2026.html", "Where to Watch the 2026 Winter Olympics in Toronto: Best Bars and Venues",
     "Complete guide to Milano Cortina 2026 watch parties. Team Canada FanFest at Nathan Phillips Square, sports bars, and early-morning viewing events.",
     "February 9, 2026", "Sports", "sports", "upcoming-toronto-events.jpg"),

    ("auston-matthews-team-usa-captain-olympics-2026.html", "Auston Matthews Captains Team USA at 2026 Winter Olympics",
     "Maple Leafs star Auston Matthews leads Team USA at Milano Cortina. What Toronto fans need to know during the NHL Olympic break.",
     "February 8, 2026", "Sports", "sports", "upcoming-toronto-events.jpg"),

    ("toronto-wnba-expansion-team-2026.html", "Toronto Gets WNBA Expansion Team: Everything You Need to Know",
     "Toronto is officially getting a WNBA franchise, becoming the league's first international team. Larry Tanenbaum's Kilmer Sports secures the franchise.",
     "February 8, 2026", "Sports", "sports", "toronto-events.jpg"),

    ("scottie-barnes-nba-all-star-raptors-2026.html", "Scottie Barnes Named NBA All-Star: Toronto Raptors' Rising Star Shines",
     "Raptors forward Scottie Barnes selected as an NBA All-Star reserve, cementing his status as one of the league's brightest young stars.",
     "February 7, 2026", "Sports", "sports", "toronto-events.jpg"),

    ("maple-leafs-trade-deadline-2026.html", "Maple Leafs Trade Deadline 2026: Morgan Rielly's Future in Question",
     "The 2026 NHL trade deadline approaches with big questions. Morgan Rielly trade rumors, goalie injuries, and Hildeby's emergence.",
     "February 7, 2026", "Sports", "sports", "toronto-events.jpg"),

    ("super-bowl-party-toronto-rebel-2026.html", "Toronto's First Official NFL Super Bowl Party at Rebel Nightclub",
     "Toronto hosts its first-ever official NFL-sanctioned Super Bowl party. A historic moment for football fans in the city.",
     "February 6, 2026", "Sports", "sports", "upcoming-toronto-events.jpg"),

    # Food & Drink
    ("winterlicious-2026-toronto-best-restaurants.html", "Winterlicious 2026: 25 Best Restaurant Picks and What to Order",
     "Winterlicious 2026 runs January 30 to February 12 with prix fixe menus across Toronto. Our picks for the best restaurants and dishes.",
     "February 9, 2026", "Food", "food", "things-to-do-toronto.jpg"),

    ("sweet-city-fest-stackt-market-toronto-2026.html", "Sweet City Fest at STACKT Market: Toronto's Free Dessert Festival",
     "Sweet City Fest takes over STACKT Market February 13-16 with free desserts, fun stations, and treats for the whole family.",
     "February 8, 2026", "Food", "food", "things-to-do-toronto.jpg"),

    ("toronto-new-restaurants-winter-2026.html", "Toronto's Hottest New Restaurant Openings for Winter 2026",
     "From Hello Nori's Yorkville expansion to Brasserie Cote in the Annex, here are the must-visit new restaurants opening this winter.",
     "February 7, 2026", "Food", "food", "things-to-do-toronto.jpg"),

    ("new-bars-toronto-january-2026.html", "5 New Bars in Toronto Everyone's Talking About Right Now",
     "From Book Bar's wine-meets-bookstore concept to Yorkville's caviar-and-martini lounge, these new bars are generating serious buzz.",
     "February 7, 2026", "Food", "food", "things-to-do-toronto.jpg"),

    ("winter-chocolate-show-toronto-2026.html", "Winter Chocolate Show 2026 at Toronto Reference Library",
     "Artisanal chocolates, bean-to-bar makers, tasting sessions, and seminars at the beautiful Appel Salon on Yonge Street.",
     "February 6, 2026", "Food", "food", "things-to-do-toronto.jpg"),

    ("st-lawrence-market-toronto-guide-2026.html", "St. Lawrence Market Toronto: Weekend Guide and What's New in 2026",
     "Toronto's top food destination: Saturday Farmers' Market, 120+ vendors, Sunday antiques, and the best peameal bacon sandwiches.",
     "February 3, 2026", "Food", "food", "things-to-do-toronto.jpg"),

    ("toronto-rooftop-bars-patios-summer-2026.html", "Toronto's Best Rooftop Bars and Patios Opening for Summer 2026",
     "As winter fades, Toronto's rooftop bars and patios prepare to open. Preview the best outdoor drinking and dining spots.",
     "January 29, 2026", "Food", "food", "things-to-do-toronto.jpg"),

    # Arts & Entertainment
    ("toronto-2026-concert-lineup-shows-cant-miss.html", "Toronto's 2026 Concert Lineup Is Already Stacked: Shows You Can't Miss",
     "From arena tours to intimate club shows, the city's music scene is offering something for every taste. Eric Church, Brandi Carlile, and more.",
     "February 8, 2026", "Arts", "arts", "events-in-toronto.jpg"),

    ("toronto-black-film-festival-2026.html", "14th Toronto Black Film Festival 2026: Complete Guide to Screenings",
     "The 14th TBFF runs February 11-16 with screenings at Carlton Cinema, Isabel Bader Theatre, and online during Black History Month.",
     "February 8, 2026", "Arts", "arts", "culture-diversity-toronto.jpg"),

    ("some-like-it-hot-musical-toronto-2026.html", "Some Like It Hot Musical Debuts in Toronto: What to Expect",
     "The award-winning Broadway musical brings Tony Award-winning performances, high-energy dance numbers, and sharp humour to Canadian audiences.",
     "February 7, 2026", "Arts", "arts", "events-in-toronto.jpg"),

    ("winterfolk-blues-roots-festival-toronto-2026.html", "Winterfolk XXIV Blues and Roots Festival: 4 Days of Live Music at the Tranzac",
     "Over 100 artists across multiple stages. Shakura S'Aida, Suzie Vinnick, Sultans of String, and four days of roots music discovery.",
     "February 7, 2026", "Arts", "arts", "events-in-toronto.jpg"),

    ("zara-larsson-toronto-2026-midnight-sun-tour.html", "Zara Larsson Toronto 2026: Midnight Sun Tour Dates and Tickets",
     "Swedish pop sensation Zara Larsson brings her Midnight Sun tour to Toronto this spring. Dynamic setlist and commanding stage presence.",
     "February 4, 2026", "Arts", "arts", "events-in-toronto.jpg"),

    ("matt-berninger-get-sunk-tour-toronto-2026.html", "Matt Berninger Get Sunk Tour Comes to Toronto This Spring",
     "The National frontman brings his intimate solo tour to Toronto. A more personal performance from indie rock's most distinctive voice.",
     "February 3, 2026", "Arts", "arts", "events-in-toronto.jpg"),

    ("hot-docs-festival-toronto-2026.html", "Hot Docs 2026: North America's Largest Documentary Festival Returns to Toronto",
     "Hundreds of documentaries from around the world. Industry conferences, filmmaker talks, and public screenings at multiple venues.",
     "February 2, 2026", "Arts", "arts", "events-in-toronto.jpg"),

    ("toronto-comic-arts-festival-tcaf-2026.html", "Toronto Comic Arts Festival (TCAF) 2026: What to Expect",
     "TCAF returns to the Toronto Reference Library in May. Free exhibitions, panels, and workshops celebrating independent comics.",
     "January 31, 2026", "Arts", "arts", "events-in-toronto.jpg"),

    # Community & Culture
    ("black-history-month-toronto-2026-events-guide.html", "Black History Month Events in Toronto 2026: Complete Guide",
     "Film festivals, art exhibitions, music performances, and community workshops celebrating Black history and culture across the city.",
     "February 9, 2026", "Community", "community", "culture-diversity-toronto.jpg"),

    ("kuumba-harbourfront-centre-black-history-month-2026.html", "KUUMBA at Harbourfront Centre: Celebrating Black History Month in Toronto",
     "Month-long celebration of Black history, art, music, and storytelling. Live performances, exhibitions, and community workshops.",
     "February 8, 2026", "Community", "community", "culture-diversity-toronto.jpg"),

    ("lunar-new-year-toronto-2026-year-of-horse.html", "Lunar New Year 2026 in Toronto: Year of the Horse Celebrations Guide",
     "From Nathan Phillips Square to Chinatown to Little Canada, Toronto celebrates with lion dances, food festivals, and cultural performances.",
     "February 7, 2026", "Community", "community", "culture-diversity-toronto.jpg"),

    ("family-day-2026-toronto-open-closed.html", "Family Day 2026 in Toronto: What's Open and Closed on February 16",
     "Plan your Family Day with our guide to what's open, what's closed, and the best family-friendly events across the city.",
     "February 6, 2026", "Community", "community", "upcoming-toronto-events.jpg"),

    ("pride-toronto-2026-wont-stop.html", "Pride Toronto 2026: 'We Won't Stop' Theme and What to Expect This Summer",
     "One of the world's largest Pride celebrations announces its 2026 theme. Month-long festivities in Church-Wellesley Village and downtown.",
     "February 5, 2026", "Community", "community", "events-in-toronto.jpg"),

    ("kensington-market-pedestrian-sundays-2026.html", "Kensington Market Pedestrian Sundays 2026: Monthly Street Celebration Guide",
     "Car-free streets, live music, food vendors, and Toronto's best neighbourhood vibe. May through October on the last Sunday.",
     "February 2, 2026", "Community", "community", "hidden-gems-toronto.jpg"),

    ("doors-open-toronto-2026-free-buildings.html", "Doors Open Toronto 2026: Explore 150+ Buildings for Free",
     "Architecturally and historically significant buildings open their doors for free. Plan your self-guided walking tour of the city.",
     "February 1, 2026", "Community", "community", "hidden-gems-toronto.jpg"),

    ("toronto-distillery-district-events-2026.html", "Distillery District Events 2026: Markets, Art, and Cobblestone Culture",
     "From summer markets to winter festivals, the cobblestone streets host markets, art shows, and seasonal celebrations year-round.",
     "January 30, 2026", "Community", "community", "hidden-gems-toronto.jpg"),

    # Seasonal
    ("canadian-international-auto-show-2026.html", "Canadian International Auto Show 2026: What's New at the Metro Toronto Convention Centre",
     "EVs, concept cars, Camp Jeep off-road course, and retro vehicles from the 80s and 90s. February 13-22.",
     "February 8, 2026", "Seasonal", "seasonal", "upcoming-toronto-events.jpg"),

    ("valentines-day-toronto-2026-romantic-events.html", "Valentine's Day Events in Toronto 2026: Romantic Things to Do",
     "Romantic dinners, live shows, unique experiences, and outdoor adventures for couples on Saturday, February 14.",
     "February 7, 2026", "Seasonal", "seasonal", "things-to-do-toronto.jpg"),

    ("toronto-event-calendar-2026-must-book.html", "Toronto Events 2026 Calendar: 10 Major Events You Must Book Tickets for Now",
     "TIFF, Caribana, CNE, Pride, Nuit Blanche, and more. These 10 massive events will sell out. Book now before it's too late.",
     "February 4, 2026", "Seasonal", "seasonal", "upcoming-toronto-events.jpg"),

    ("cherry-blossom-high-park-toronto-2026.html", "Cherry Blossom Season in Toronto 2026: When to Visit High Park",
     "Plan your visit for late April and early May. Timing tips, best viewing spots, and how to avoid the weekend crowds.",
     "February 2, 2026", "Seasonal", "seasonal", "things-to-do-toronto.jpg"),

    ("toronto-summer-festivals-2026-calendar.html", "Toronto Summer Festivals 2026: Complete Calendar and Confirmed Dates",
     "Pride, Caribana, CNE, TIFF, and dozens more. Your complete guide to planning a summer full of festivals and outdoor events.",
     "January 31, 2026", "Seasonal", "seasonal", "upcoming-toronto-events.jpg"),

    ("toronto-waterfront-festival-tall-ships-2026.html", "Toronto Waterfront Festival 2026: Tall Ships Return to Sugar Beach",
     "Free admission. Tall ship tours, live entertainment, local food, and nautical family fun on June 28-29 at Sugar Beach.",
     "January 30, 2026", "Seasonal", "seasonal", "events-in-toronto.jpg"),

    ("toronto-escape-rooms-immersive-experiences-2026.html", "Toronto's Best Escape Rooms and Immersive Experiences for 2026",
     "Theatrical escape rooms, immersive art, and technology-enhanced experiences that put you at the centre of the action.",
     "January 28, 2026", "Seasonal", "seasonal", "things-to-do-toronto.jpg"),

    ("toronto-island-ferry-events-summer-2026.html", "Toronto Islands 2026: Ferry Guide, Events, and What's New This Summer",
     "Beaches, bike paths, Centreville, and stunning skyline views. Your updated guide to ferries, events, and island activities.",
     "January 27, 2026", "Seasonal", "seasonal", "things-to-do-toronto.jpg"),

    # Evergreen SEO articles
    ("hidden-gem-events-toronto.html", "Hidden Gem Events in Toronto You Probably Didn't Know About",
     "Beyond the headline festivals, Toronto's best moments are quieter, more local, and easier on your wallet. ROM After Dark, AGO nights, Doors Open, and more.",
     "February 5, 2026", "Hidden Gems", "", "hidden-gems-toronto.jpg"),

    ("toronto-events-culture-diversity.html", "Toronto Events That Showcase the City's Culture and Diversity",
     "Caribbean festivals, Indigenous gatherings, neighbourhood street celebrations, global music nights, and grassroots community events.",
     "February 6, 2026", "Culture", "", "culture-diversity-toronto.jpg"),

    ("toronto-events-sell-out-fast.html", "Toronto Events That Sell Out Fast and How to Catch Them",
     "Intimate concerts, food pop-ups, and one-night-only experiences vanish in hours. Strategies to secure your spot before tickets are gone.",
     "February 7, 2026", "Tips", "", "sell-out-fast-toronto.jpg"),

    ("holiday-toronto-event-calendar.html", "Holiday Toronto Event Calendar: Markets, Light Shows & Seasonal Events",
     "Winter markets, immersive light installations, cultural celebrations, and family-friendly activities for Toronto's holiday season.",
     "February 8, 2026", "Seasonal", "seasonal", "holiday-events-toronto.jpg"),

    ("toronto-event-calendar-vs-social-media.html", "Toronto Event Calendar vs Social Media: Which Finds Better Events?",
     "Algorithms decide what you see on social media. Discover why a dedicated event calendar beats scrolling for finding things to do.",
     "February 9, 2026", "Guide", "", "toronto-event-calendar.jpg"),
]

def generate_card_html(slug, title, excerpt, date, category, tag_class, image, is_featured=False):
    if is_featured:
        return f'''
            <article class="featured-card" data-category="{tag_class}">
                <img src="images/{image}" alt="{title}" width="600" height="400" loading="eager">
                <div class="article-card-body">
                    <span class="tag {tag_class}">{category}</span>
                    <h2><a href="{slug}">{title}</a></h2>
                    <p class="excerpt">{excerpt}</p>
                    <div class="meta"><span>{date}</span></div>
                    <a href="{slug}" class="read-more">Read Full Guide &rarr;</a>
                </div>
            </article>'''
    else:
        return f'''
            <article class="article-card" data-category="{tag_class}">
                <div class="article-card-body">
                    <span class="tag {tag_class}">{category}</span>
                    <h2><a href="{slug}">{title}</a></h2>
                    <p class="excerpt">{excerpt}</p>
                    <div class="meta"><span>{date}</span></div>
                    <a href="{slug}" class="read-more">Read More &rarr;</a>
                </div>
            </article>'''


def main():
    # Build article cards
    featured = ARTICLES[0]
    rest = ARTICLES[1:]

    featured_html = generate_card_html(*featured, is_featured=True)
    cards_html = '\n'.join(generate_card_html(*a) for a in rest)

    # Get unique categories for filter buttons
    categories = []
    seen = set()
    for a in ARTICLES:
        cat = a[4]
        tc = a[5]
        if tc and tc not in seen:
            categories.append((tc, cat))
            seen.add(tc)

    filter_buttons = '<button class="filter-btn active" data-filter="all">All</button>\n'
    for tc, cat in categories:
        filter_buttons += f'            <button class="filter-btn" data-filter="{tc}">{cat}</button>\n'

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Toronto Events Blog | Breaking News, Event Guides & Things to Do in Toronto</title>
    <meta name="description" content="Toronto's source for event news, breaking stories, and insider guides. 50+ articles covering sports, food, arts, culture, and things to do in Toronto. Updated daily.">
    <meta name="keywords" content="Toronto events, events in Toronto, things to do in Toronto, Toronto event calendar, upcoming Toronto events, Toronto news, Toronto blog, CP24, Toronto Star, CTV News Toronto, Toronto festivals, Toronto nightlife, Toronto sports">
    <link rel="canonical" href="https://findtorontoevents.ca/blog/">
    <link rel="icon" href="/favicon.ico" sizes="256x256" type="image/x-icon">
    <meta property="og:title" content="Toronto Events Blog — Breaking News, Guides & Hidden Gems">
    <meta property="og:description" content="50+ articles covering Toronto events, breaking news, sports, food, arts, and things to do. Your insider guide to the city.">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://findtorontoevents.ca/blog/">
    <meta property="og:image" content="https://findtorontoevents.ca/blog/images/blog-banner.jpg">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="Toronto Events">
    <meta property="og:locale" content="en_CA">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Toronto Events Blog — Breaking News & Guides">
    <meta name="twitter:description" content="50+ articles covering Toronto events, breaking news, sports, food, arts, and things to do.">
    <meta name="twitter:image" content="https://findtorontoevents.ca/blog/images/blog-banner.jpg">
    <meta name="geo.region" content="CA-ON">
    <meta name="geo.placename" content="Toronto">
    <meta name="geo.position" content="43.6532;-79.3832">
    <meta name="ICBM" content="43.6532, -79.3832">
    <meta name="robots" content="index, follow">
    <script type="application/ld+json">
    {{
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": "Toronto Events Blog",
        "description": "Toronto's source for event news, breaking stories, and insider guides covering sports, food, arts, culture, and things to do.",
        "url": "https://findtorontoevents.ca/blog/",
        "publisher": {{
            "@type": "Organization",
            "name": "Toronto Events",
            "url": "https://findtorontoevents.ca",
            "logo": {{ "@type": "ImageObject", "url": "https://findtorontoevents.ca/favicon.ico" }}
        }}
    }}
    </script>
    <style>
        :root {{
            --pk-300:#c084fc;--pk-400:#a855f7;--pk-500:#9333ea;--pk-600:#7e22ce;--pk-900:#3b0764;
            --surface-0:#0a0a0f;--surface-1:#12121a;--surface-2:#1a1a25;
            --text-1:#f0f0f5;--text-2:#a0a0b5;--text-3:#606075;
        }}
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:var(--surface-0);color:var(--text-1);line-height:1.7;min-height:100vh}}
        body::before{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 20% 0%,rgba(147,51,234,.15) 0%,transparent 50%),radial-gradient(ellipse at 80% 100%,rgba(59,7,100,.2) 0%,transparent 50%);pointer-events:none;z-index:-1}}
        a{{color:var(--pk-400);text-decoration:none;transition:color .2s}}a:hover{{color:var(--pk-300)}}
        .top-nav{{position:sticky;top:0;z-index:100;background:rgba(10,10,15,.85);backdrop-filter:blur(20px);border-bottom:1px solid rgba(255,255,255,.05);padding:.75rem 1.5rem;display:flex;align-items:center;justify-content:space-between}}
        .nav-brand{{font-weight:900;font-size:1.1rem;letter-spacing:-.02em;color:#fff}}.nav-brand span{{color:var(--pk-400)}}
        .nav-links{{display:flex;gap:1.5rem;align-items:center}}.nav-links a{{font-size:.8rem;font-weight:600;text-transform:uppercase;letter-spacing:.08em;color:var(--text-2)}}.nav-links a:hover{{color:#fff}}.nav-links a.active{{color:var(--pk-400)}}
        .hero{{text-align:center;padding:4rem 1.5rem 2rem;background:linear-gradient(180deg,var(--pk-900) 0%,transparent 100%)}}
        .hero h1{{font-size:clamp(2rem,5vw,3.5rem);font-weight:900;letter-spacing:-.03em;margin-bottom:.75rem}}.hero h1 span{{color:var(--pk-400)}}
        .hero p{{font-size:1.05rem;color:var(--text-2);max-width:650px;margin:0 auto}}
        .hero .stats{{margin-top:1rem;font-size:.8rem;color:var(--text-3)}}

        .filters{{max-width:1200px;margin:0 auto;padding:1.5rem 1.5rem 0;display:flex;flex-wrap:wrap;gap:.5rem;justify-content:center}}
        .filter-btn{{padding:.4rem 1rem;border:1px solid rgba(255,255,255,.1);border-radius:999px;background:transparent;color:var(--text-2);font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;cursor:pointer;transition:all .2s}}
        .filter-btn:hover{{border-color:var(--pk-400);color:var(--pk-300)}}
        .filter-btn.active{{background:var(--pk-500);border-color:var(--pk-500);color:#fff}}

        .articles-grid{{max-width:1200px;margin:0 auto;padding:2rem 1.5rem;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:1.5rem}}
        .article-card{{background:var(--surface-1);border:1px solid rgba(255,255,255,.06);border-radius:1rem;overflow:hidden;transition:transform .3s,border-color .3s,box-shadow .3s}}
        .article-card:hover{{transform:translateY(-3px);border-color:rgba(147,51,234,.3);box-shadow:0 15px 30px rgba(0,0,0,.4)}}
        .article-card-body{{padding:1.25rem}}
        .tag{{display:inline-block;font-size:.6rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;padding:.2rem .6rem;border-radius:999px;background:rgba(147,51,234,.15);color:var(--pk-300);margin-bottom:.5rem}}
        .tag.breaking{{background:rgba(239,68,68,.15);color:#f87171}}
        .tag.sports{{background:rgba(34,197,94,.15);color:#4ade80}}
        .tag.food{{background:rgba(251,191,36,.15);color:#fbbf24}}
        .tag.arts{{background:rgba(96,165,250,.15);color:#60a5fa}}
        .tag.community{{background:rgba(244,114,182,.15);color:#f472b6}}
        .tag.seasonal{{background:rgba(45,212,191,.15);color:#2dd4bf}}
        .tag.featured{{background:rgba(234,179,8,.15);color:#fbbf24}}
        .article-card h2{{font-size:1.1rem;font-weight:800;line-height:1.3;margin-bottom:.5rem}}
        .article-card h2 a{{color:#fff}}.article-card h2 a:hover{{color:var(--pk-300)}}
        .article-card .excerpt{{font-size:.85rem;color:var(--text-2);line-height:1.5;margin-bottom:.75rem;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
        .article-card .meta{{font-size:.7rem;color:var(--text-3);font-weight:600}}
        .read-more{{display:inline-flex;align-items:center;gap:.3rem;font-size:.75rem;font-weight:700;color:var(--pk-400);margin-top:.5rem}}.read-more:hover{{gap:.5rem}}
        .featured-card{{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr;background:var(--surface-1);border:1px solid rgba(255,255,255,.08);border-radius:1rem;overflow:hidden;transition:transform .3s,border-color .3s,box-shadow .3s}}
        .featured-card:hover{{transform:translateY(-3px);border-color:rgba(147,51,234,.3);box-shadow:0 20px 40px rgba(0,0,0,.4)}}
        .featured-card img{{width:100%;height:100%;min-height:280px;object-fit:cover}}
        .featured-card .article-card-body{{padding:2rem;display:flex;flex-direction:column;justify-content:center}}
        .featured-card h2{{font-size:1.5rem}}
        .cta-section{{max-width:800px;margin:0 auto;text-align:center;padding:3rem 1.5rem}}
        .cta-section h2{{font-size:1.6rem;font-weight:900;margin-bottom:.75rem}}.cta-section p{{color:var(--text-2);margin-bottom:1.5rem}}
        .cta-btn{{display:inline-block;padding:.8rem 2rem;background:var(--pk-500);color:#fff;font-weight:800;font-size:.85rem;border-radius:999px;text-transform:uppercase;letter-spacing:.05em;transition:background .2s,transform .2s}}.cta-btn:hover{{background:var(--pk-600);transform:scale(1.05);color:#fff}}
        .news-sources{{max-width:1200px;margin:0 auto;padding:0 1.5rem 2rem;text-align:center}}
        .news-sources p{{font-size:.75rem;color:var(--text-3)}}
        footer{{text-align:center;padding:2rem 1.5rem;border-top:1px solid rgba(255,255,255,.05);color:var(--text-3);font-size:.7rem}}footer a{{color:var(--text-2)}}
        .hidden{{display:none!important}}
        @media(max-width:768px){{.articles-grid{{grid-template-columns:1fr}}.featured-card{{grid-template-columns:1fr}}.featured-card img{{height:200px;min-height:auto}}.nav-links{{gap:.75rem}}.nav-links a{{font-size:.7rem}}.filters{{gap:.3rem}}.filter-btn{{font-size:.65rem;padding:.3rem .7rem}}}}
    </style>
</head>
<body>
    <nav class="top-nav"><a href="/" class="nav-brand"><span>Toronto</span> Events</a><div class="nav-links"><a href="/">Home</a><a href="/blog/" class="active">Blog</a><a href="/MOVIESHOWS/">Movies</a><a href="/findstocks">Stocks</a></div></nav>
    <header class="hero">
        <h1><span>Toronto Events</span> Blog</h1>
        <p>Breaking news, event guides, and insider tips covering everything happening in Toronto. Sourced from CP24, Toronto Star, CTV News, BlogTO, and more.</p>
        <p class="stats">{len(ARTICLES)} articles &middot; Updated daily &middot; Covering sports, food, arts, culture &amp; community</p>
    </header>
    <div class="filters">
        {filter_buttons}
    </div>
    <main>
        <div class="articles-grid">
            {featured_html}
            {cards_html}
        </div>
        <div class="news-sources">
            <p>News sourced from: CP24 &middot; CTV News Toronto &middot; Toronto Star &middot; Global News &middot; BlogTO &middot; NOW Toronto &middot; Toronto Life &middot; CBC Toronto &middot; UrbanToronto &middot; City of Toronto</p>
        </div>
        <section class="cta-section">
            <h2>Never Miss a Toronto Event</h2>
            <p>Browse upcoming events, hidden gems, and community celebrations across the city.</p>
            <a href="/" class="cta-btn">Explore Toronto Events</a>
        </section>
    </main>
    <footer>
        <p>Built with love for Toronto &middot; <a href="/">Toronto Events</a> &middot; <a href="https://tdotevent.ca">TdotEvent.ca</a> &middot; support@findtorontoevents.ca</p>
    </footer>
    <script>
        document.querySelectorAll('.filter-btn').forEach(function(btn) {{
            btn.addEventListener('click', function() {{
                document.querySelectorAll('.filter-btn').forEach(function(b) {{ b.classList.remove('active'); }});
                btn.classList.add('active');
                var filter = btn.getAttribute('data-filter');
                document.querySelectorAll('.article-card, .featured-card').forEach(function(card) {{
                    if (filter === 'all' || card.getAttribute('data-category') === filter) {{
                        card.classList.remove('hidden');
                    }} else {{
                        card.classList.add('hidden');
                    }}
                }});
            }});
        }});
    </script>
</body>
</html>'''

    index_path = BLOG_DIR / 'index.html'
    index_path.write_text(html, encoding='utf-8')
    print(f'Blog index generated with {len(ARTICLES)} articles at {index_path}')


if __name__ == '__main__':
    main()
