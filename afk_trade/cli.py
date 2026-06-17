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
    p.add_argument("--preset", default=None, help="preset pair, mis. 'xauusd' atau 'eurusd'")
    p.add_argument("--timeframe", default="H1")
    p.add_argument("--bars", type=int, default=2000)
    p.add_argument(
        "--mode", default="profit_factor",
        choices=["profit_factor", "winrate", "expectancy"],
        help="kriteria seleksi skenario",
    )
    p.add_argument("--threshold", type=float, default=0.80, help="ambang winrate (mode winrate)")
    p.add_argument("--pf-threshold", type=float, default=1.3, help="ambang profit factor (mode profit_factor)")
    p.add_argument("--balance", type=float, default=10_000.0, help="modal awal (paper)")
    p.add_argument("--min-trades", type=int, default=20)
    p.add_argument(
        "--no-validate", dest="validate", action="store_false",
        help="matikan validasi train/test (default: aktif)",
    )
    p.add_argument(
        "--test-ratio", type=float, default=0.3,
        help="fraksi bar terakhir untuk data test out-of-sample",
    )
    p.add_argument(
        "--vote-weight", default="profit_factor",
        choices=["equal", "profit_factor", "winrate", "expectancy"],
        help="bobot voting antar skenario terpilih",
    )
    p.add_argument(
        "--min-agreement", type=float, default=0.0,
        help="ambang konsensus voting 0-1; di bawahnya bot tahan diri (FLAT)",
    )
    p.add_argument(
        "--scale-by-confidence", action="store_true",
        help="skala ukuran posisi dengan derajat konsensus voting",
    )
    p.add_argument("--csv", default=None, help="path CSV OHLC (opsional)")
    p.add_argument(
        "--no-yfinance", dest="yfinance", action="store_false",
        help="jangan ambil data dari Yahoo Finance (default: coba bila terpasang)",
    )
    p.add_argument("--top", type=int, default=10, help="jumlah skenario teratas yang ditampilkan")
    p.add_argument("--live", action="store_true", help="(belum diaktifkan) gunakan broker live")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    overrides = dict(
        timeframe=args.timeframe,
        bars=args.bars,
        selection_mode=args.mode,
        win_threshold=args.threshold,
        pf_threshold=args.pf_threshold,
        min_trades=args.min_trades,
        starting_balance=args.balance,
        validate=args.validate,
        test_ratio=args.test_ratio,
        vote_weight=args.vote_weight,
        min_agreement=args.min_agreement,
        scale_by_confidence=args.scale_by_confidence,
        live=args.live,
    )
    if args.preset:
        config = BotConfig.preset(args.preset, **overrides)
    else:
        config = BotConfig(symbol=args.symbol, **overrides)

    if args.live:
        print("[!] Mode live belum diaktifkan demi keamanan. Jalan dalam paper trading.\n")

    df = get_data(
        config.symbol, config.timeframe, config.bars,
        csv_path=args.csv, allow_yfinance=args.yfinance,
    )
    span = f"{df['time'].iloc[0]} .. {df['time'].iloc[-1]}" if "time" in df else ""
    print(f"Data: {len(df)} bar untuk {config.symbol} {config.timeframe}  [{span}]\n")

    bot = TradingBot(config)
    report = bot.run(df)

    crit = {
        "profit_factor": f"profit factor >= {config.pf_threshold}",
        "winrate": f"winrate >= {config.win_threshold:.0%}",
        "expectancy": f"expectancy >= {config.min_expectancy}",
    }[config.selection_mode]

    print(f"Total skenario diuji : {len(report.all_results)}")
    print(f"Mode seleksi         : {config.selection_mode} ({crit}, min {config.min_trades} trade)\n")

    print(f"== Top {args.top} skenario (urut {config.selection_mode}) ==")
    for r in report.all_results[: args.top]:
        flag = "  <== TERPILIH" if r in report.winners else ""
        print(
            f"  WR={r.winrate:5.1%} | trades={r.n_trades:3d} | PF={r.profit_factor:6.2f} "
            f"| ret={r.total_return:+7.2%} | maxDD={r.max_drawdown:5.1%} | {r.label}{flag}"
        )

    print(f"\n== Skenario terpilih ({crit}) ==")
    if not report.winners:
        print("  (tidak ada skenario yang memenuhi ambang)")
    for w in report.winners:
        sig = {1: "LONG", -1: "SHORT", 0: "FLAT"}[w.last_signal]
        print(
            f"  PF={w.profit_factor:6.2f} | WR={w.winrate:5.1%} | ret={w.total_return:+7.2%} "
            f"| sinyal sekarang={sig:5s} | {w.label}"
        )

    if report.validated:
        n_robust = sum(1 for v in report.validation if v.robust)
        print(f"\n== Validasi out-of-sample (test {config.test_ratio:.0%} bar terakhir) ==")
        print(
            f"  Kandidat (lolos train): {len(report.validation)} | "
            f"ROBUST (lolos test juga): {n_robust}"
        )
        for v in report.validation:
            mark = "ROBUST " if v.robust else "gugur  "
            print(
                f"  [{mark}] train: WR={v.train.winrate:4.0%} PF={v.train.profit_factor:5.2f} "
                f"ret={v.train.total_return:+6.1%} | "
                f"test: WR={v.test.winrate:4.0%} PF={v.test.profit_factor:5.2f} "
                f"ret={v.test.total_return:+6.1%} tr={v.test.n_trades:3d} | {v.label}"
            )

    agg = report.aggregated
    net = {1: "LONG", -1: "SHORT", 0: "FLAT (tak ada konsensus)"}[agg.direction]
    print(f"\n== Voting agregasi (bobot: {agg.weight_scheme}) ==")
    print(
        f"  Suara   : {agg.n_long} LONG / {agg.n_short} SHORT / {agg.n_flat} FLAT"
    )
    print(
        f"  Bobot   : long={agg.long_weight:.2f} vs short={agg.short_weight:.2f}"
    )
    print(f"  Konsensus: {agg.confidence:.0%}  ->  KEPUTUSAN NET: {net}")

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
