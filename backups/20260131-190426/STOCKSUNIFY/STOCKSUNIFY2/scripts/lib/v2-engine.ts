/**
 * STOCKSUNIFY2: Scientific Engine
 */

import { fetchMultipleStocks, fetchStockData } from './stock-data-fetcher-enhanced';
import { scoreRAR, scoreVAM, scoreLSP, scoreScientificCANSLIM, scoreAdversarialTrend, V2Pick } from './strategies';

const V2_UNIVERSE = [
    'SPY', 'AAPL', 'MSFT', 'NVDA', 'AMZN', 'GOOGL', 'META', 'TSLA',
    'AVGO', 'COST', 'V', 'MA', 'NFLX', 'AMD', 'LRCX',
    'JPM', 'UNH', 'LLY', 'JNJ', 'PG', 'XOM', 'CAT', 'GE',
    'COIN', 'MSTR', 'UPST', 'AFRM', 'PLTR', 'SOFI',
    'GME', 'AMC', 'SNDL', 'MULN', 'XELA', 'HSTO'
];

export async function generateScientificPicks(): Promise<{ picks: V2Pick[], regime: any }> {
    console.log('📡 Engine: Fetching Market Regime Baseline (SPY)...');
    const spyData = await fetchStockData('SPY');

    let spySMA200 = 0;
    if (spyData?.history && spyData.history.length >= 200) {
        const closes = spyData.history.map(h => h.close);
        // Calculate SMA200 using the last 200 closing prices
        spySMA200 = closes.slice(-200).reduce((a, b) => a + b, 0) / 200;
    }

    const regime = {
        symbol: 'SPY',
        price: spyData?.price || 0,
        sma200: spySMA200,
        status: (spyData?.price || 0) > spySMA200 ? 'BULLISH' : 'BEARISH'
    };

    console.log('📡 Engine: Fetching Strategic Universe...');
    const allData = await fetchMultipleStocks(V2_UNIVERSE);

    const stockPool = allData.filter(d => d.symbol !== 'SPY');
    const v2Picks: V2Pick[] = [];

    console.log('🔬 Engine: Running Interrogations...');
    for (const data of stockPool) {
        const rar = scoreRAR(data, spyData || undefined);
        if (rar) v2Picks.push(rar);

        const vam = scoreVAM(data);
        if (vam) v2Picks.push(vam);

        const lsp = scoreLSP(data);
        if (lsp) v2Picks.push(lsp);

        const scs = scoreScientificCANSLIM(data, spyData || undefined);
        if (scs) v2Picks.push(scs);

        const at = scoreAdversarialTrend(data);
        if (at) v2Picks.push(at);
    }

    v2Picks.sort((a, b) => b.score - a.score);
    return {
        picks: v2Picks.slice(0, 25),
        regime
    };
}

