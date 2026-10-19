"""Command-line interface for the combined-book paper-trade module."""
from __future__ import annotations

import argparse

from combined_book.ledger import append_month_row, init_ledger, load_ledger, save_ledger
from combined_book.rules import RULES_HASH, RULES_MARKDOWN, verify_rules_hash


def _cmd_hash_check(_args):
    ok = verify_rules_hash()
    print(f"RULES_HASH={RULES_HASH}")
    print(f"hash_valid={ok}")
    return 0 if ok else 1


def _cmd_init_ledger(args):
    init_ledger(args.positions, args.path, capital=args.capital, date_closed=args.date)
    print(f"ledger initialized -> {args.path}")
    return 0


def _cmd_report(_args):
    print(RULES_MARKDOWN)
    print(f"RULES_HASH={RULES_HASH}")
    return 0


def _cmd_backtest(args):
    from combined_book.simulator import run_backtest
    from combined_book.fetch import get_daily_closes, UNIVERSE
    symbols = [s for s in UNIVERSE if s != "PUT"]  # PUT is an index, not an ETF
    result = run_backtest(
        lambda: get_daily_closes(symbols, cache_dir=args.cache),
        vol_cap=args.vol_cap,
        start=args.start,
        end=args.end,
    )
    stats = result["stats"]
    print(f"n_months={stats['n_months']}")
    print(f"cagr={stats['cagr']:.4f}")
    print(f"annualized_sharpe={stats['annualized_sharpe']:.4f}")
    print(f"max_dd={stats['max_dd']:.4f}")
    print(f"pf={stats['pf']:.4f}")
    print(f"win_rate={stats['win_rate']:.4f}")
    return 0


def _cmd_gates(args):
    from combined_book.gates import evaluate_go_live, evaluate_kill
    ledger = load_ledger(args.path)
    returns = [r["return"] for r in ledger["monthly_returns"]]
    from combined_book.simulator import compute_stats
    stats = compute_stats(__import__("pandas").Series(returns))
    go, go_checks = evaluate_go_live(stats)
    killed, kill_checks = evaluate_kill(stats)
    print(f"go_live={go} checks={go_checks}")
    print(f"kill={killed} kills={kill_checks}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="combined_book")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("hash-check").set_defaults(func=_cmd_hash_check)

    p_init = sub.add_parser("init-ledger")
    p_init.add_argument("--path", default="combined_book/data/ledger.json")
    p_init.add_argument("--capital", type=float, default=100_000.0)
    p_init.add_argument("--date", default="2026-09-30")
    p_init.add_argument("--positions", default="{\"put_write\":0.40,\"trend\":0.35,\"quality_value\":0.19,\"cash\":0.06}")
    p_init.set_defaults(func=_cmd_init_ledger)

    p_bt = sub.add_parser("backtest")
    p_bt.add_argument("--vol-cap", type=float, default=0.05)
    p_bt.add_argument("--start", default=None)
    p_bt.add_argument("--end", default=None)
    p_bt.add_argument("--cache", default=None)
    p_bt.set_defaults(func=_cmd_backtest)

    p_g = sub.add_parser("gates")
    p_g.add_argument("--path", default="combined_book/data/ledger.json")
    p_g.set_defaults(func=_cmd_gates)

    p_r = sub.add_parser("report")
    p_r.set_defaults(func=_cmd_report)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
