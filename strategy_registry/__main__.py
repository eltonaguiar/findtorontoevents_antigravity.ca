"""CLI entry point: python -m strategy_registry"""

import logging
from strategy_registry.registry import StrategyRegistry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def main():
    reg = StrategyRegistry()
    count = reg.process_all()
    print(f"[StrategyRegistry] Processed {count} envelope(s)")


if __name__ == "__main__":
    main()
