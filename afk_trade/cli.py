"""Antarmuka command-line untuk menjalankan bot.

Contoh:
    python -m afk_trade.cli --symbol EURUSD --timeframe H1 --threshold 0.8
"""

from __future__ import annotations

import argparse

from .bot import TradingBot
from .config import BotConfig
from .data.feed import get_data


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Afk_trade - bot trading berbasis probabilitas skenario")
    p.add_argument("--symbol", default="EURUSD")
    p.add_argument("--timeframe", default="H1")
    p.add_argument("--bars", type=int, default=2000)
    p.add_argument("--threshold", type=float, default=0.80, help="ambang winrate (0-1)")
    p.add_argument("--min-trades", type=int, default=20)
    p.add_argument("--csv", default=None, help="path CSV OHLC (opsional)")
    p.add_argument("--top", type=int, default=10, help="jumlah skenario teratas yang ditampilkan")
    p.add_argument("--live", action="store_true", help="(belum diaktifkan) gunakan broker live")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = BotConfig(
        symbol=args.symbol,
        timeframe=args.timeframe,
        bars=args.bars,
        win_threshold=args.threshold,
        min_trades=args.min_trades,
        live=args.live,
    )

    if args.live:
        print("[!] Mode live belum diaktifkan demi keamanan. Jalan dalam paper trading.\n")

    df = get_data(config.symbol, config.timeframe, config.bars, csv_path=args.csv)
    print(f"Data: {len(df)} bar untuk {config.symbol} {config.timeframe}\n")

    bot = TradingBot(config)
    report = bot.run(df)

    print(f"Total skenario diuji : {len(report.all_results)}")
    print(f"Ambang winrate       : {config.win_threshold:.0%} (min {config.min_trades} trade)\n")

    print(f"== Top {args.top} skenario (berdasarkan winrate) ==")
    for r in report.all_results[: args.top]:
        flag = "  <== TERPILIH" if r in report.winners else ""
        print(
            f"  {r.winrate:6.1%} | trades={r.n_trades:3d} | PF={r.profit_factor:5.2f} "
            f"| ret={r.total_return:+7.2%} | {r.label}{flag}"
        )

    print(f"\n== Skenario terpilih (winrate >= {config.win_threshold:.0%}) ==")
    if not report.winners:
        print("  (tidak ada skenario yang memenuhi ambang)")
    for w in report.winners:
        sig = {1: "LONG", -1: "SHORT", 0: "FLAT"}[w.last_signal]
        print(f"  {w.winrate:6.1%} | sinyal sekarang={sig:5s} | {w.label}")

    print("\n== Eksekusi (paper) ==")
    if not report.executed:
        print("  (tidak ada order dieksekusi)")
    for o in report.executed:
        side = "BUY" if o.side == 1 else "SELL"
        print(f"  {side} {o.volume} {o.symbol} @ {o.price:.5f}  <- {o.label}")

    print("\n== Ringkasan akun ==")
    for k, v in report.broker_summary.items():
        print(f"  {k}: {v}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
