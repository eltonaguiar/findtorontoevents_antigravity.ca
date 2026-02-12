#!/usr/bin/env python3
"""
FinBERT Sentiment Analyzer — Finance-specific NLP for news sentiment.

Replaces generic keyword-based sentiment with ProsusAI/FinBERT:
  - 87% accuracy on financial text vs 72% for VADER
  - Understands "beat expectations but guided lower" = NEGATIVE
  - Understands "missed estimates but raised guidance" = POSITIVE

Pipeline:
  1. Fetch recent news headlines from Finnhub API
  2. Run each through FinBERT for (positive/negative/neutral, confidence)
  3. Aggregate per-ticker sentiment scores
  4. Post to world_class_intelligence.php for signal modulation

Requires: pip install transformers torch requests
Runs via: python run_all.py --finbert
"""
import sys
import os
import json
import logging
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import post_to_api, safe_request, API_HEADERS
from config import API_BASE, ADMIN_KEY, TRACKED_TICKERS, FINNHUB_API_KEY

logger = logging.getLogger('finbert_sentiment')

# Lazy-load model to avoid import cost when not running
_tokenizer = None
_model = None
MODEL_NAME = "ProsusAI/finbert"


def _load_model():
    """Lazy-load FinBERT model (downloads ~420MB on first run, cached after)."""
    global _tokenizer, _model
    if _tokenizer is not None:
        return

    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
        logger.info("Loading FinBERT model (%s)...", MODEL_NAME)
        _tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        _model.eval()
        logger.info("FinBERT loaded successfully")
    except ImportError:
        logger.error("Missing dependencies: pip install transformers torch")
        raise


def analyze_sentiment(text):
    """
    Analyze financial text sentiment using FinBERT.

    Returns: {
        'label': 'positive' | 'negative' | 'neutral',
        'score': float (0-1 confidence),
        'scores': {'positive': float, 'negative': float, 'neutral': float}
    }
    """
    import torch

    _load_model()

    inputs = _tokenizer(text, return_tensors="pt", truncation=True,
                        max_length=512, padding=True)

    with torch.no_grad():
        outputs = _model(**inputs)

    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    labels = ["positive", "negative", "neutral"]

    scores = {labels[i]: float(probs[0][i]) for i in range(3)}
    best_idx = torch.argmax(probs).item()

    return {
        'label': labels[best_idx],
        'score': float(probs[0][best_idx]),
        'scores': scores
    }


def analyze_batch(texts):
    """Analyze a batch of texts efficiently."""
    import torch

    _load_model()

    results = []
    # Process in batches of 16 for memory efficiency
    batch_size = 16
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        inputs = _tokenizer(batch, return_tensors="pt", truncation=True,
                            max_length=512, padding=True)

        with torch.no_grad():
            outputs = _model(**inputs)

        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        labels = ["positive", "negative", "neutral"]

        for j in range(len(batch)):
            scores = {labels[k]: float(probs[j][k]) for k in range(3)}
            best_idx = torch.argmax(probs[j]).item()
            results.append({
                'text': batch[j][:100],
                'label': labels[best_idx],
                'score': float(probs[j][best_idx]),
                'scores': scores
            })

    return results


def fetch_news_headlines(ticker, days_back=3):
    """Fetch recent news for a ticker from Finnhub."""
    if not FINNHUB_API_KEY:
        logger.warning("No Finnhub API key — set FINNHUB env variable")
        return []

    end = datetime.utcnow()
    start = end - timedelta(days=days_back)

    url = "https://finnhub.io/api/v1/company-news"
    params = {
        'symbol': ticker,
        'from': start.strftime('%Y-%m-%d'),
        'to': end.strftime('%Y-%m-%d'),
        'token': FINNHUB_API_KEY
    }

    resp = safe_request(url, params=params, timeout=15)
    if resp is None:
        return []

    try:
        articles = resp.json()
        # Extract headlines
        headlines = []
        for article in articles[:20]:  # Max 20 per ticker
            headline = article.get('headline', '')
            summary = article.get('summary', '')
            # Use headline + first sentence of summary for richer context
            text = headline
            if summary:
                first_sentence = summary.split('.')[0]
                if len(first_sentence) > 20:
                    text = f"{headline}. {first_sentence}"
            if text:
                headlines.append({
                    'text': text,
                    'datetime': article.get('datetime', 0),
                    'source': article.get('source', 'unknown')
                })
        return headlines
    except Exception as e:
        logger.warning("Failed to parse Finnhub response for %s: %s", ticker, e)
        return []


def compute_ticker_sentiment(ticker, headlines):
    """
    Compute aggregate sentiment for a ticker from its headlines.

    Returns: {
        'ticker': str,
        'sentiment_score': float (-1 to +1, negative=bearish, positive=bullish),
        'sentiment_label': str,
        'confidence': float (0-1),
        'num_articles': int,
        'positive_pct': float,
        'negative_pct': float,
        'neutral_pct': float,
        'strongest_signal': str (most extreme headline)
    }
    """
    if not headlines:
        return {
            'ticker': ticker,
            'sentiment_score': 0.0,
            'sentiment_label': 'neutral',
            'confidence': 0.0,
            'num_articles': 0,
            'positive_pct': 0.0,
            'negative_pct': 0.0,
            'neutral_pct': 0.0,
            'strongest_signal': ''
        }

    texts = [h['text'] for h in headlines]
    results = analyze_batch(texts)

    # Aggregate
    pos_count = sum(1 for r in results if r['label'] == 'positive')
    neg_count = sum(1 for r in results if r['label'] == 'negative')
    neu_count = sum(1 for r in results if r['label'] == 'neutral')
    total = len(results)

    # Weighted sentiment score: positive = +1, negative = -1, neutral = 0
    # Weighted by confidence
    weighted_sum = sum(
        r['scores']['positive'] - r['scores']['negative']
        for r in results
    )
    sentiment_score = weighted_sum / total  # Range: -1 to +1

    # Overall label
    if sentiment_score > 0.15:
        label = 'bullish'
    elif sentiment_score < -0.15:
        label = 'bearish'
    else:
        label = 'neutral'

    # Average confidence
    avg_confidence = sum(r['score'] for r in results) / total

    # Find strongest signal (most extreme sentiment)
    strongest = max(results, key=lambda r: abs(r['scores']['positive'] - r['scores']['negative']))

    return {
        'ticker': ticker,
        'sentiment_score': round(sentiment_score, 4),
        'sentiment_label': label,
        'confidence': round(avg_confidence, 4),
        'num_articles': total,
        'positive_pct': round(pos_count / total * 100, 1),
        'negative_pct': round(neg_count / total * 100, 1),
        'neutral_pct': round(neu_count / total * 100, 1),
        'strongest_signal': strongest['text'][:120]
    }


def main():
    """Run FinBERT sentiment analysis for all tracked tickers."""
    logger.info("=" * 60)
    logger.info("FINBERT SENTIMENT ANALYZER — Starting")
    logger.info("=" * 60)

    all_sentiments = []

    for ticker in TRACKED_TICKERS:
        logger.info("  Analyzing %s...", ticker)

        # Fetch news
        headlines = fetch_news_headlines(ticker, days_back=3)
        if not headlines:
            logger.info("    No news found for %s", ticker)
            continue

        logger.info("    Found %d headlines", len(headlines))

        # Compute sentiment
        sentiment = compute_ticker_sentiment(ticker, headlines)
        all_sentiments.append(sentiment)

        emoji = {'bullish': '+', 'bearish': '-', 'neutral': '='}
        logger.info("    [%s] %s: score=%.3f conf=%.2f (%d articles) | %d%% pos, %d%% neg",
                     emoji.get(sentiment['sentiment_label'], '?'),
                     ticker,
                     sentiment['sentiment_score'],
                     sentiment['confidence'],
                     sentiment['num_articles'],
                     sentiment['positive_pct'],
                     sentiment['negative_pct'])

    # Post to API
    if all_sentiments:
        result = post_to_api('ingest_regime', {
            'source': 'finbert_sentiment',
            'sentiments': all_sentiments,
            'computed_at': datetime.utcnow().isoformat(),
            'model': MODEL_NAME,
            'tickers_analyzed': len(all_sentiments)
        })

        if result.get('ok'):
            logger.info("Sentiment data posted to API")
        else:
            logger.warning("API post error: %s", result.get('error', 'unknown'))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("FINBERT SENTIMENT SUMMARY")
    logger.info("  Tickers analyzed: %d", len(all_sentiments))

    bullish = [s for s in all_sentiments if s['sentiment_label'] == 'bullish']
    bearish = [s for s in all_sentiments if s['sentiment_label'] == 'bearish']

    if bullish:
        logger.info("  BULLISH: %s", ', '.join(s['ticker'] for s in bullish))
    if bearish:
        logger.info("  BEARISH: %s", ', '.join(s['ticker'] for s in bearish))

    logger.info("=" * 60)

    return all_sentiments


if __name__ == '__main__':
    main()
