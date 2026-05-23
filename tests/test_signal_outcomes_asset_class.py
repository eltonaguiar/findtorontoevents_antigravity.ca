from genome.progressive_promotion import log_outcome_to_mysql
from paper_trading.mysql_sync import _resolve_asset_class


class _Cursor:
    def __init__(self) -> None:
        self.params = None

    def execute(self, _sql, params) -> None:
        self.params = params


class _Conn:
    def __init__(self) -> None:
        self.cur = _Cursor()
        self.committed = False

    def cursor(self):
        return self.cur

    def commit(self) -> None:
        self.committed = True


def test_paper_trading_mysql_asset_class_infers_non_crypto():
    assert _resolve_asset_class({"symbol": "EURUSD=X"}) == "FOREX"
    assert _resolve_asset_class({"symbol": "GC=F"}) == "FUTURES"
    assert _resolve_asset_class({"symbol": "AAPL"}) == "EQUITY"


def test_progressive_promotion_logs_inferred_asset_class():
    conn = _Conn()
    pick = {
        "symbol": "EURUSD=X",
        "direction": "LONG",
        "entry_price": 1.1,
        "tp": 1.2,
        "sl": 1.0,
        "opened_at": None,
        "strategy_id": "fx-test",
    }
    log_outcome_to_mysql(conn, pick, "WIN", 1.15, 1.2)
    assert conn.committed is True
    assert conn.cur.params[10] == "FOREX"
