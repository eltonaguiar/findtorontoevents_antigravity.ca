# Consensus Analyzer - PowerShell Version
# Analyzes algorithm agreement patterns

$algorithms = @{
    'KIMI-MTF' = @{ Type = 'MINE'; Category = 'Multi-Timeframe' }
    'A1-TimeSeriesMomentum' = @{ Type = 'ACADEMIC'; Category = 'Momentum' }
    'A2-PairsTrading' = @{ Type = 'ACADEMIC'; Category = 'Mean Reversion' }
    'A3-SimplifiedML' = @{ Type = 'ACADEMIC'; Category = 'Machine Learning' }
    'A4-OpeningRangeBreakout' = @{ Type = 'ACADEMIC'; Category = 'Volatility' }
    'A5-VWAP' = @{ Type = 'ACADEMIC'; Category = 'Volume' }
    'S1-5MinMacro' = @{ Type = 'SOCIAL'; Category = 'Scalping' }
    'S2-RSIMACD' = @{ Type = 'SOCIAL'; Category = 'Oscillator' }
    'S3-WhaleShadow' = @{ Type = 'SOCIAL'; Category = 'On-Chain' }
    'S4-NarrativeVelocity' = @{ Type = 'SOCIAL'; Category = 'Sentiment' }
    'S5-PortfolioSpray' = @{ Type = 'SOCIAL'; Category = 'Risk Management' }
}

# Current predictions
$predictions = @{
    'POPCAT' = @{
        Price = 0.0515
        Predictions = @{
            'KIMI-MTF' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A1-TimeSeriesMomentum' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A2-PairsTrading' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
            'A3-SimplifiedML' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A4-OpeningRangeBreakout' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A5-VWAP' = @{ Signal = 'NEUTRAL'; Confidence = 'MEDIUM' }
            'S1-5MinMacro' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'S2-RSIMACD' = @{ Signal = 'NEUTRAL'; Confidence = 'MEDIUM' }
            'S3-WhaleShadow' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
            'S4-NarrativeVelocity' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'S5-PortfolioSpray' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
        }
    }
    'PENGU' = @{
        Price = 0.00670
        Predictions = @{
            'KIMI-MTF' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A1-TimeSeriesMomentum' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A2-PairsTrading' = @{ Signal = 'BUY'; Confidence = 'MEDIUM' }
            'A3-SimplifiedML' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A4-OpeningRangeBreakout' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A5-VWAP' = @{ Signal = 'SELL'; Confidence = 'MEDIUM' }
            'S1-5MinMacro' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'S2-RSIMACD' = @{ Signal = 'NEUTRAL'; Confidence = 'MEDIUM' }
            'S3-WhaleShadow' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'S4-NarrativeVelocity' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'S5-PortfolioSpray' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
        }
    }
    'DOGE' = @{
        Price = 0.0967
        Predictions = @{
            'KIMI-MTF' = @{ Signal = 'BUY'; Confidence = 'MEDIUM' }
            'A1-TimeSeriesMomentum' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A2-PairsTrading' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
            'A3-SimplifiedML' = @{ Signal = 'BUY'; Confidence = 'MEDIUM' }
            'A4-OpeningRangeBreakout' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'A5-VWAP' = @{ Signal = 'NEUTRAL'; Confidence = 'MEDIUM' }
            'S1-5MinMacro' = @{ Signal = 'BUY'; Confidence = 'HIGH' }
            'S2-RSIMACD' = @{ Signal = 'NEUTRAL'; Confidence = 'MEDIUM' }
            'S3-WhaleShadow' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
            'S4-NarrativeVelocity' = @{ Signal = 'BUY'; Confidence = 'MEDIUM' }
            'S5-PortfolioSpray' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
        }
    }
    'BTC' = @{
        Price = 68851
        Predictions = @{
            'KIMI-MTF' = @{ Signal = 'BUY'; Confidence = 'LOW' }
            'A1-TimeSeriesMomentum' = @{ Signal = 'BUY'; Confidence = 'MEDIUM' }
            'A2-PairsTrading' = @{ Signal = 'NEUTRAL'; Confidence = 'N/A' }
            'A3-SimplifiedML' = @{ Signal = 'BUY'; Confidence = 'MEDIUM' }
            'A4-OpeningRangeBreakout' = @{ Signal = 'BUY'; Confidence = 'MEDIUM' }
            'A5-VWAP' = @{ Signal = 'NEUTRAL'; Confidence = 'MEDIUM' }
            'S1-5MinMacro' = @{ Signal = 'BUY'; Confidence = 'MEDIUM' }
            'S2-RSIMACD' = @{ Signal = 'NEUTRAL'; Confidence = 'MEDIUM' }
            'S3-WhaleShadow' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
            'S4-NarrativeVelocity' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
            'S5-PortfolioSpray' = @{ Signal = 'NEUTRAL'; Confidence = 'LOW' }
        }
    }
}

function Get-Consensus($assetPredictions) {
    $buyCount = 0
    $sellCount = 0
    $neutralCount = 0
    $highConfBuy = 0
    
    foreach ($pred in $assetPredictions.Values) {
        switch ($pred.Signal) {
            'BUY' { 
                $buyCount++
                if ($pred.Confidence -eq 'HIGH') { $highConfBuy++ }
            }
            'SELL' { $sellCount++ }
            'NEUTRAL' { $neutralCount++ }
        }
    }
    
    $total = $buyCount + $sellCount + $neutralCount
    $maxCount = [math]::Max($buyCount, [math]::Max($sellCount, $neutralCount))
    $signal = if ($buyCount -eq $maxCount) { 'BUY' } elseif ($sellCount -eq $maxCount) { 'SELL' } else { 'NEUTRAL' }
    $strength = [math]::Round(($maxCount / $total) * 100, 1)
    
    return @{
        Signal = $signal
        BuyCount = $buyCount
        SellCount = $sellCount
        NeutralCount = $neutralCount
        HighConfBuy = $highConfBuy
        Strength = $strength
    }
}

function Get-CorrelationMatrix($predictions) {
    $algos = $predictions['POPCAT'].Predictions.Keys
    $matrix = @{}
    
    foreach ($algo1 in $algos) {
        $matrix[$algo1] = @{}
        foreach ($algo2 in $algos) {
            if ($algo1 -eq $algo2) {
                $matrix[$algo1][$algo2] = 1.0
                continue
            }
            
            $agreements = 0
            $total = 0
            
            foreach ($asset in $predictions.Keys) {
                $sig1 = $predictions[$asset].Predictions[$algo1].Signal
                $sig2 = $predictions[$asset].Predictions[$algo2].Signal
                if ($sig1 -eq $sig2) { $agreements++ }
                $total++
            }
            
            $matrix[$algo1][$algo2] = [math]::Round($agreements / $total, 2)
        }
    }
    
    return $matrix
}

function Find-Clusters($matrix) {
    $clusters = @()
    $assigned = @{}
    
    foreach ($algo1 in $matrix.Keys) {
        if ($assigned.ContainsKey($algo1)) { continue }
        
        $cluster = @($algo1)
        $assigned[$algo1] = $true
        
        foreach ($algo2 in $matrix[$algo1].Keys) {
            if ($algo1 -ne $algo2 -and $matrix[$algo1][$algo2] -ge 0.7 -and !$assigned.ContainsKey($algo2)) {
                $cluster += $algo2
                $assigned[$algo2] = $true
            }
        }
        
        if ($cluster.Count -gt 1) {
            $clusters += ,$cluster
        }
    }
    
    return $clusters
}

function Get-BestPairs($matrix) {
    $pairs = @()
    $algoList = $matrix.Keys | Sort-Object
    
    for ($i = 0; $i -lt $algoList.Count; $i++) {
        for ($j = $i + 1; $j -lt $algoList.Count; $j++) {
            $pairs += [PSCustomObject]@{
                Algo1 = $algoList[$i]
                Algo2 = $algoList[$j]
                Agreement = $matrix[$algoList[$i]][$algoList[$j]]
            }
        }
    }
    
    return $pairs | Sort-Object Agreement -Descending | Select-Object -First 10
}

function Compare-Categories($predictions, $algorithms) {
    $results = @{
        ACADEMIC = @{ BUY = 0; SELL = 0; NEUTRAL = 0; Total = 0 }
        SOCIAL = @{ BUY = 0; SELL = 0; NEUTRAL = 0; Total = 0 }
        MINE = @{ BUY = 0; SELL = 0; NEUTRAL = 0; Total = 0 }
    }
    
    foreach ($asset in $predictions.Keys) {
        foreach ($algo in $predictions[$asset].Predictions.Keys) {
            $type = $algorithms[$algo].Type
            $signal = $predictions[$asset].Predictions[$algo].Signal
            $results[$type][$signal]++
            $results[$type].Total++
        }
    }
    
    foreach ($type in $results.Keys) {
        $total = $results[$type].Total
        if ($total -gt 0) {
            $results[$type].BuyPct = [math]::Round($results[$type].BUY / $total * 100, 1)
            $results[$type].SellPct = [math]::Round($results[$type].SELL / $total * 100, 1)
            $results[$type].NeutralPct = [math]::Round($results[$type].NEUTRAL / $total * 100, 1)
        }
    }
    
    return $results
}

# Main Analysis
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   CONSENSUS ANALYSIS SYSTEM" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Per-asset consensus
Write-Host "CONSENSUS BY ASSET:" -ForegroundColor Yellow
Write-Host "-------------------"
foreach ($asset in $predictions.Keys) {
    $cons = Get-Consensus $predictions[$asset].Predictions
    $color = if ($cons.Signal -eq 'BUY') { 'Green' } elseif ($cons.Signal -eq 'SELL') { 'Red' } else { 'Gray' }
    Write-Host ("  {0}: {1} ({2}% strength) - {3} BUY / {4} SELL / {5} NEUTRAL" -f 
        $asset, $cons.Signal, $cons.Strength, $cons.BuyCount, $cons.SellCount, $cons.NeutralCount) -ForegroundColor $color
}

# Calculate correlations
$matrix = Get-CorrelationMatrix $predictions

Write-Host ""
Write-Host "ALGORITHM AGREEMENT MATRIX:" -ForegroundColor Yellow
Write-Host "---------------------------"
$algoList = $matrix.Keys | Sort-Object
$header = "              "
foreach ($a in $algoList) {
    $short = $a.Substring(0, [math]::Min(4, $a.Length))
    $header += "$short  "
}
Write-Host $header
foreach ($a1 in $algoList) {
    $line = "$($a1.Substring(0, [math]::Min(14, $a1.Length))).PadRight(14)"
    foreach ($a2 in $algoList) {
        $val = $matrix[$a1][$a2]
        $color = if ($val -ge 0.8) { 'Green' } elseif ($val -ge 0.5) { 'Yellow' } else { 'Gray' }
        Write-Host ("{0,4:F0}% " -f ($val * 100)) -ForegroundColor $color -NoNewline
    }
    Write-Host ""
}

# Best pairs
Write-Host ""
Write-Host "TOP ALGORITHM PAIRS (Highest Agreement):" -ForegroundColor Yellow
Write-Host "----------------------------------------"
$bestPairs = Get-BestPairs $matrix
foreach ($pair in $bestPairs | Select-Object -First 5) {
    $color = if ($pair.Agreement -ge 0.8) { 'Green' } elseif ($pair.Agreement -ge 0.6) { 'Yellow' } else { 'White' }
    Write-Host ("  {0} + {1}: {2}% agreement" -f $pair.Algo1, $pair.Algo2, [math]::Round($pair.Agreement * 100)) -ForegroundColor $color
}

# Find clusters
$clusters = Find-Clusters $matrix
Write-Host ""
Write-Host "ALGORITHM CLUSTERS (70%+ agreement):" -ForegroundColor Yellow
Write-Host "------------------------------------"
if ($clusters.Count -eq 0) {
    Write-Host "  No tight clusters found (algorithms are diverse)" -ForegroundColor Gray
} else {
    $i = 1
    foreach ($cluster in $clusters) {
        Write-Host "  Cluster $i`: $($cluster -join ', ')" -ForegroundColor Green
        $i++
    }
}

# Category comparison
$catComp = Compare-Categories $predictions $algorithms
Write-Host ""
Write-Host "CATEGORY BIAS COMPARISON:" -ForegroundColor Yellow
Write-Host "-------------------------"
foreach ($cat in $catComp.Keys) {
    $color = switch ($cat) {
        'ACADEMIC' { 'Cyan' }
        'SOCIAL' { 'Magenta' }
        'MINE' { 'Yellow' }
    }
    Write-Host ("  {0}: {1}% BUY | {2}% SELL | {3}% NEUTRAL" -f 
        $cat, $catComp[$cat].BuyPct, $catComp[$cat].SellPct, $catComp[$cat].NeutralPct) -ForegroundColor $color
}

# Meta-consensus
Write-Host ""
Write-Host "META-ANALYSIS: WHO FOLLOWS THE CROWD?" -ForegroundColor Yellow
Write-Host "--------------------------------------"
$metaConsensus = @{}
foreach ($asset in $predictions.Keys) {
    $cons = Get-Consensus $predictions[$asset].Predictions
    foreach ($algo in $predictions[$asset].Predictions.Keys) {
        if (!$metaConsensus.ContainsKey($algo)) {
            $metaConsensus[$algo] = @{ WithMajority = 0; AgainstMajority = 0; Total = 0 }
        }
        if ($predictions[$asset].Predictions[$algo].Signal -eq $cons.Signal) {
            $metaConsensus[$algo].WithMajority++
        } else {
            $metaConsensus[$algo].AgainstMajority++
        }
        $metaConsensus[$algo].Total++
    }
}

$sortedMeta = $metaConsensus.GetEnumerator() | Sort-Object { 
    $_.Value.WithMajority / $_.Value.Total 
} -Descending

foreach ($entry in $sortedMeta) {
    $conformity = [math]::Round($entry.Value.WithMajority / $entry.Value.Total * 100, 0)
    $color = if ($conformity -ge 80) { 'Green' } elseif ($conformity -ge 50) { 'Yellow' } else { 'Red' }
    Write-Host ("  {0}: {1}% conformity ({2}/{3} with majority)" -f 
        $entry.Key, $conformity, $entry.Value.WithMajority, $entry.Value.Total) -ForegroundColor $color
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   KEY INSIGHTS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Calculate consensus performance prediction
$highConsensusAssets = @()
$lowConsensusAssets = @()
foreach ($asset in $predictions.Keys) {
    $cons = Get-Consensus $predictions[$asset].Predictions
    if ($cons.Strength -ge 60) {
        $highConsensusAssets += $asset
    } else {
        $lowConsensusAssets += $asset
    }
}

Write-Host ""
Write-Host "HIGH CONSENSUS PICKS (60%+ agreement):" -ForegroundColor Green
Write-Host "  $($highConsensusAssets -join ', ')"
Write-Host "  Theory: Higher consensus = higher probability of success"

Write-Host ""
Write-Host "LOW CONSENSUS/CONFLICTED PICKS:" -ForegroundColor Yellow
Write-Host "  $($lowConsensusAssets -join ', ')"
Write-Host "  Theory: Lower consensus = more uncertainty, higher variance"

Write-Host ""
Write-Host "ALGORITHM DIVERGENCE ALERT:" -ForegroundColor Red
$a5PENGU = $predictions['PENGU'].Predictions['A5-VWAP'].Signal
Write-Host "  A5-VWAP is the ONLY SELL on PENGU (all others BUY)"
Write-Host "  This is a MEAN REVERSION vs MOMENTUM conflict"
Write-Host ""
