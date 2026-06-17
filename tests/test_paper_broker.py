from afk_trade.execution.paper import PaperBroker


def test_long_then_close_with_profit():
    b = PaperBroker(starting_balance=10_000)
    b.market_order("EURUSD", side=1, volume=1000, price=1.10)
    b.close("EURUSD", price=1.11)  # naik 0.01 * 1000 = +10
    assert round(b.balance, 2) == 10_010.0
    assert "EURUSD" not in b.positions


def test_reverse_position_realizes_pnl():
    b = PaperBroker(starting_balance=10_000)
    b.market_order("EURUSD", side=1, volume=1000, price=1.10)
    # Balik ke short di harga lebih tinggi -> realisasi untung dari long.
    b.market_order("EURUSD", side=-1, volume=1000, price=1.12)
    assert round(b.balance, 2) == 10_020.0
    assert b.positions["EURUSD"].side == -1


def test_equity_includes_unrealized():
    b = PaperBroker(starting_balance=10_000)
    b.market_order("EURUSD", side=1, volume=1000, price=1.10)
    eq = b.equity({"EURUSD": 1.105})  # +5 unrealized
    assert round(eq, 2) == 10_005.0


def test_invalid_side_raises():
    b = PaperBroker()
    try:
        b.market_order("EURUSD", side=0, volume=1, price=1.0)
        assert False, "harus melempar ValueError"
    except ValueError:
        pass
