import json, urllib.request, urllib.parse, ssl, os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

API_KEY = os.getenv("NEWSAPI_KEY", "")
BASE = 'https://newsapi.org/v2'

def fetch_news(query, page_size=20):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    params = urllib.parse.urlencode({'q': query, 'language': 'en', 'sortBy': 'publishedAt', 'pageSize': page_size, 'apiKey': API_KEY})
    url = f'{BASE}/everything?{params}'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        return json.loads(resp.read())
    except Exception as e:
        print(f'  API error for "{query}": {e}')
        return None

# Fetch news for key crypto and market topics
queries = {
    'bitcoin': 'bitcoin OR BTC',
    'ethereum': 'ethereum OR ETH',
    'altcoins': 'solana OR cardano OR avalanche OR polkadot',
    'defi': 'defi OR decentralized finance',
    'fed_rates': 'federal reserve OR interest rate OR monetary policy',
    'inflation': 'inflation OR CPI OR consumer prices',
    'crypto_regulation': 'crypto regulation OR SEC cryptocurrency',
    'ai_tech': 'artificial intelligence OR AI stocks OR nvidia',
    'forex': 'forex OR dollar index OR EURUSD',
    'market_fear': 'market crash OR recession OR bear market',
}

all_articles = {}
for topic, query in queries.items():
    print(f'Fetching news: {topic}...')
    data = fetch_news(query)
    if data and data.get('status') == 'ok':
        articles = data.get('articles', [])
        all_articles[topic] = articles
        print(f'  Got {len(articles)} articles')
    else:
        print(f'  Failed or rate limited')
        all_articles[topic] = []

# Simple sentiment scoring
def score_sentiment(title, desc):
    text = (title + ' ' + (desc or '')).lower()
    pos = sum(1 for w in ['surge','rally','bullish','gain','soar','rise','boom','breakout','record','high'] if w in text)
    neg = sum(1 for w in ['crash','plunge','bearish','fear','drop','fall','collapse','recession','sell','risk','warning'] if w in text)
    return pos - neg

# Score each topic
topic_sentiments = {}
for topic, articles in all_articles.items():
    scores = [score_sentiment(a.get('title',''), a.get('description','')) for a in articles]
    avg = sum(scores)/len(scores) if scores else 0
    pos = sum(1 for s in scores if s > 0)
    neg = sum(1 for s in scores if s < 0)
    neutral = sum(1 for s in scores if s == 0)
    topic_sentiments[topic] = {'avg': avg, 'pos': pos, 'neg': neg, 'neutral': neutral, 'total': len(articles)}
    print(f'{topic}: sentiment={avg:+.2f} (pos={pos}, neg={neg}, neutral={neutral})')

# Print top headlines per topic
print('\n' + '='*80)
print('TOP HEADLINES BY TOPIC')
print('='*80)
for topic, articles in all_articles.items():
    print(f'\n--- {topic.upper()} ---')
    for a in articles[:5]:
        src = a.get('source', {}).get('name', 'Unknown')
        title = a.get('title', 'No title')
        score = score_sentiment(a.get('title',''), a.get('description',''))
        sentiment_label = 'POSITIVE' if score > 0 else ('NEGATIVE' if score < 0 else 'NEUTRAL')
        print(f'  [{sentiment_label:>8}] ({src}) {title}')

# === 10 PORTFOLIO THEORIES ===
print('\n' + '='*80)
print('10 NEWS-BASED PORTFOLIO THEORIES')
print('='*80)

theories = [
    {
        'name': '1. FEAR CONTRARIAN',
        'thesis': 'When market_fear sentiment is extremely negative, go LONG on quality assets',
        'trigger': 'market_fear avg sentiment < -0.5',
        'assets': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'],
        'direction': 'LONG',
        'sizing': 'Equal weight, 20% each',
    },
    {
        'name': '2. MOMENTUM FOLLOW',
        'thesis': 'When bitcoin news is bullish, ride the momentum across top alts',
        'trigger': 'bitcoin sentiment > +0.3 AND ethereum sentiment > 0',
        'assets': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'AVAXUSDT', 'LINKUSDT'],
        'direction': 'LONG',
        'sizing': 'BTC 40%, ETH 30%, rest 10% each',
    },
    {
        'name': '3. REGULATION HEDGE',
        'thesis': 'Negative crypto regulation news = SHORT altcoins, LONG BTC (flight to safety)',
        'trigger': 'crypto_regulation sentiment < -0.3',
        'assets': ['BTCUSDT LONG', 'SOLUSDT SHORT', 'AVAXUSDT SHORT', 'DOTUSDT SHORT'],
        'direction': 'Mixed',
        'sizing': 'BTC 50% LONG, each alt 16.7% SHORT',
    },
    {
        'name': '4. AI NARRATIVE PLAY',
        'thesis': 'Positive AI news benefits AI-adjacent crypto tokens',
        'trigger': 'ai_tech sentiment > +0.3',
        'assets': ['FETUSDT', 'RENDERUSDT', 'NEARUSDT', 'TAOUSDT'],
        'direction': 'LONG',
        'sizing': 'Equal weight 25% each',
    },
    {
        'name': '5. FED RATE SENSITIVITY',
        'thesis': 'Hawkish Fed news = SHORT crypto, Dovish = LONG crypto',
        'trigger': 'fed_rates sentiment < -0.3 = SHORT, > +0.3 = LONG',
        'assets': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
        'direction': 'Conditional on sentiment',
        'sizing': 'Equal weight',
    },
    {
        'name': '6. DEFI MOMENTUM',
        'thesis': 'Positive DeFi news = LONG DeFi blue chips',
        'trigger': 'defi sentiment > +0.2',
        'assets': ['AAVEUSDT', 'UNIUSDT', 'LINKUSDT', 'MKRUSDT', 'COMPUSDT'],
        'direction': 'LONG',
        'sizing': 'AAVE/UNI 30% each, rest 13% each',
    },
    {
        'name': '7. INFLATION HEDGE',
        'thesis': 'High inflation news = LONG BTC + GOLD equivalent crypto',
        'trigger': 'inflation sentiment < -0.3 (negative = inflation is high)',
        'assets': ['BTCUSDT', 'PAXGUSDT', 'ETHUSDT'],
        'direction': 'LONG',
        'sizing': 'BTC 50%, PAXG 30%, ETH 20%',
    },
    {
        'name': '8. ALTCOIN ROTATION',
        'thesis': 'When altcoin news is bullish but BTC neutral, alts outperform',
        'trigger': 'altcoins sentiment > +0.3 AND bitcoin sentiment < +0.2',
        'assets': ['SOLUSDT', 'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'NEARUSDT'],
        'direction': 'LONG',
        'sizing': 'Equal weight 20% each',
    },
    {
        'name': '9. FEAR+FOREX CARRY',
        'thesis': 'Dollar weakness (negative forex USD news) = LONG crypto',
        'trigger': 'forex sentiment < -0.2 (negative = dollar weakness)',
        'assets': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT'],
        'direction': 'LONG',
        'sizing': 'BTC 40%, rest 20% each',
    },
    {
        'name': '10. NEWS REVERSAL (Contrarian)',
        'thesis': 'Extreme negative ALL topics = maximum contrarian LONG',
        'trigger': 'Average across ALL topics < -0.5',
        'assets': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'FETUSDT', 'RENDERUSDT'],
        'direction': 'LONG',
        'sizing': 'BTC/ETH 30% each, SOL 20%, FET/RENDER 10% each',
    },
]

for t in theories:
    print(f'\n--- {t["name"]} ---')
    print(f'  Thesis: {t["thesis"]}')
    print(f'  Trigger: {t["trigger"]}')
    print(f'  Assets: {t["assets"]}')
    print(f'  Direction: {t["direction"]}')
    print(f'  Sizing: {t["sizing"]}')

    # Check if trigger would fire based on current sentiment
    fired = False
    if '1' in t['name'] and topic_sentiments.get('market_fear',{}).get('avg',0) < -0.5:
        fired = True
    elif '2' in t['name'] and topic_sentiments.get('bitcoin',{}).get('avg',0) > 0.3:
        fired = True
    elif '3' in t['name'] and topic_sentiments.get('crypto_regulation',{}).get('avg',0) < -0.3:
        fired = True
    elif '4' in t['name'] and topic_sentiments.get('ai_tech',{}).get('avg',0) > 0.3:
        fired = True
    elif '5' in t['name']:
        fed_avg = topic_sentiments.get('fed_rates',{}).get('avg',0)
        if fed_avg < -0.3 or fed_avg > 0.3:
            fired = True
    elif '6' in t['name'] and topic_sentiments.get('defi',{}).get('avg',0) > 0.2:
        fired = True
    elif '7' in t['name'] and topic_sentiments.get('inflation',{}).get('avg',0) < -0.3:
        fired = True
    elif '8' in t['name']:
        alt_avg = topic_sentiments.get('altcoins',{}).get('avg',0)
        btc_avg = topic_sentiments.get('bitcoin',{}).get('avg',0)
        if alt_avg > 0.3 and btc_avg < 0.2:
            fired = True
    elif '9' in t['name'] and topic_sentiments.get('forex',{}).get('avg',0) < -0.2:
        fired = True
    elif '10' in t['name']:
        avg_all = sum(s.get('avg',0) for s in topic_sentiments.values()) / max(1, len(topic_sentiments))
        fired = avg_all < -0.5

    status = 'TRIGGERED' if fired else 'MONITORING'
    print(f'  Current status: {status}')

# Summary of triggered strategies
print('\n' + '='*80)
print('STRATEGY TRIGGER SUMMARY')
print('='*80)
avg_all = sum(s.get('avg',0) for s in topic_sentiments.values()) / max(1, len(topic_sentiments))
print(f'Overall average sentiment: {avg_all:+.3f}')
print(f'Most bullish topic: {max(topic_sentiments, key=lambda k: topic_sentiments[k]["avg"])} ({topic_sentiments[max(topic_sentiments, key=lambda k: topic_sentiments[k]["avg"])]["avg"]:+.2f})')
print(f'Most bearish topic: {min(topic_sentiments, key=lambda k: topic_sentiments[k]["avg"])} ({topic_sentiments[min(topic_sentiments, key=lambda k: topic_sentiments[k]["avg"])]["avg"]:+.2f})')

# Save results
output = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'topic_sentiments': topic_sentiments,
    'theories': theories,
    'articles_by_topic': {k: [{'title': a.get('title',''), 'source': a.get('source',{}).get('name',''), 'sentiment': score_sentiment(a.get('title',''), a.get('description',''))} for a in v[:5]] for k, v in all_articles.items()},
}
os.makedirs('alpha_engine/data', exist_ok=True)
with open('alpha_engine/data/news_portfolio_theories.json', 'w') as f:
    json.dump(output, f, indent=2, default=str)
print('\nSaved to alpha_engine/data/news_portfolio_theories.json')
