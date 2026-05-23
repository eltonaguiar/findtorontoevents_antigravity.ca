"""Build the expanded GITHUB_STRATS.MD by concatenating original + 5 research files + 6 elite files."""
import os

os.chdir(r"e:\findtorontoevents_antigravity.ca")

# Read original file
with open("GITHUB_STRATS.MD", "r", encoding="utf-8") as f:
    original = f.read()

lines = original.split("\n")
start_idx = 0
for i, line in enumerate(lines):
    if line.startswith("## 1. Market Microstructure"):
        start_idx = i
        break

original_body = "\n".join(lines[start_idx:])

# Read header
with open("GITHUB_STRATS_NEW.MD", "r", encoding="utf-8") as f:
    header = f.read()

# Read all 5 research files
doc_files = [
    "40_EQUITY_STRATEGIES_CATALOG.md",
    "40_NEW_TRADING_STRATEGIES.md",
    "40_CRYPTO_DEFI_STRATEGIES.md",
    "40_NEW_TRADING_STRATEGIES_V2.md",
    "40_ADVANCED_TRADING_STRATEGIES.md",
]
docs = {}
for fname in doc_files:
    with open(f"docs/{fname}", "r", encoding="utf-8") as f:
        docs[fname] = f.read()

# Read 6 elite strategy files
elite_files = [
    "elite_100_equity_factor.md",
    "elite_100_crypto_defi.md",
    "elite_100_fi_fx_commodities.md",
    "elite_100_options_ml.md",
    "elite_100_macro_systematic.md",
    "elite_100_microstructure_altdata.md",
]
elite_docs = {}
for fname in elite_files:
    with open(f"docs/{fname}", "r", encoding="utf-8") as f:
        elite_docs[fname] = f.read()

divider = "# " + "=" * 63

parts = []
parts.append(header)
parts.append("")
parts.append(original_body)
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART II — EQUITY STRATEGIES (49 New)")
parts.append(divider)
parts.append("")
parts.append(docs["40_EQUITY_STRATEGIES_CATALOG.md"])
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART III — FIXED INCOME, FX & COMMODITIES (40 New)")
parts.append(divider)
parts.append("")
parts.append(docs["40_NEW_TRADING_STRATEGIES.md"])
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART IV — CRYPTO & DEFI (40 New)")
parts.append(divider)
parts.append("")
parts.append(docs["40_CRYPTO_DEFI_STRATEGIES.md"])
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART V — OPTIONS/VOL, ML & ALT DATA (40 New)")
parts.append(divider)
parts.append("")
parts.append(docs["40_NEW_TRADING_STRATEGIES_V2.md"])
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART VI — CROSS-ASSET MACRO, MICROSTRUCTURE & SYSTEMATIC (40 New)")
parts.append(divider)
parts.append("")
parts.append(docs["40_ADVANCED_TRADING_STRATEGIES.md"])
parts.append("")
parts.append("")

# Elite strategy files (Parts VII-XII)
parts.append(divider)
parts.append("# PART VII — ELITE EQUITY & FACTOR STRATEGIES (100 New)")
parts.append(divider)
parts.append("")
parts.append(elite_docs["elite_100_equity_factor.md"])
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART VIII — ELITE CRYPTO & DEFI STRATEGIES (100 New)")
parts.append(divider)
parts.append("")
parts.append(elite_docs["elite_100_crypto_defi.md"])
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART IX — ELITE FIXED INCOME, FX & COMMODITIES (100 New)")
parts.append(divider)
parts.append("")
parts.append(elite_docs["elite_100_fi_fx_commodities.md"])
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART X — ELITE OPTIONS, VOLATILITY, ML & AI (100 New)")
parts.append(divider)
parts.append("")
parts.append(elite_docs["elite_100_options_ml.md"])
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART XI — ELITE MACRO, CTA & SYSTEMATIC (100 New)")
parts.append(divider)
parts.append("")
parts.append(elite_docs["elite_100_macro_systematic.md"])
parts.append("")
parts.append("")
parts.append(divider)
parts.append("# PART XII — ELITE MICROSTRUCTURE, CROSS-ASSET ARB & ALTERNATIVE (100 New)")
parts.append(divider)
parts.append("")
parts.append(elite_docs["elite_100_microstructure_altdata.md"])
parts.append("")
parts.append("")

# Master summary
parts.append(divider)
parts.append("# MASTER SUMMARY")
parts.append(divider)
parts.append("")
parts.append("## Strategy Count by Category")
parts.append("")
parts.append("| Part | Category | Count |")
parts.append("|------|----------|-------|")
parts.append("| I | Market Microstructure, Cross-Asset, Alt Data, DeFi, On-Chain, NFT, Derivatives, Behavioral, Market Structure, Regime, ML | ~100 |")
parts.append("| II | Equity: Factor, StatArb, Event-Driven, Sector Rotation, Earnings, Institutional, Microstructure, Cross-Asset, Quant, Special Situations, Regime-Adaptive | 49 |")
parts.append("| III | Fixed Income (20) + FX (10) + Commodities (10) | 40 |")
parts.append("| IV | Crypto: On-Chain, DeFi, Derivatives, Cross-Chain, Sentiment, MEV, Tokenomics | 40 |")
parts.append("| V | Options/Volatility (15) + Machine Learning (15) + Alt Data (10) | 40 |")
parts.append("| VI | Cross-Asset Macro (15) + Microstructure (10) + Systematic Portfolio (15) | 40 |")
parts.append("| VII | Elite Equity & Factor (Deep Value, Momentum, Quality, Size, StatArb, Event, Sector, Earnings, Multi-Factor, Anomaly) | 100 |")
parts.append("| VIII | Elite Crypto & DeFi (On-Chain, DeFi Protocol, Derivatives, Cross-Exchange, Sentiment, MEV, Tokenomics, Cross-Chain, Microstructure, Regime) | 100 |")
parts.append("| IX | Elite FI, FX & Commodities (Yield Curve, Credit, G10 FX, EM FX, Energy, Metals, Agriculture, Cross-Sector, Multi-Asset, Advanced) | 100 |")
parts.append("| X | Elite Options/Vol (Trading, Income, Directional, Exotic) + ML/AI (Supervised, Unsupervised/RL, NLP, Generative, Alt Data, Ensemble) | 100 |")
parts.append("| XI | Elite Macro (Rates, FX, Cross-Asset) + CTA/Trend + Systematic Equity (Factors, Timing) + Systematic FI + Risk Mgmt + Alt Systematic + Portfolio Construction | 100 |")
parts.append("| XII | Elite Microstructure (Order Book, Cross-Asset) + StatArb + Alternative Assets + Cross-Asset Arb + Behavioral + Geopolitical + Screening + Tax + EM/Frontier | 100 |")
parts.append("| **TOTAL** | | **~909** |")
parts.append("")
parts.append("---")
parts.append("")
parts.append("*Document compiled for the Antigravity Alpha Engine research pipeline. All strategies require live-market validation before capital allocation.*")

complete = "\n".join(parts)
with open("GITHUB_STRATS.MD", "w", encoding="utf-8") as f:
    f.write(complete)

total_lines = complete.count("\n") + 1
h3_count = complete.count("\n### ")
byte_size = len(complete.encode("utf-8"))
print(f"Total lines: {total_lines}")
print(f"Strategy headings (###): {h3_count}")
print(f"File size: {byte_size:,} bytes")
