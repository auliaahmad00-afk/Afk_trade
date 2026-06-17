# Afk_trade

Bot trading **forex** yang bekerja dengan menjalankan **banyak skenario strategi**,
menghitung **probabilitas menang (winrate)** tiap skenario lewat backtest, lalu
**otomatis mengeksekusi** skenario yang winrate-nya **di atas ambang (default 80%)**.

Saat ini eksekusi memakai **paper trading** (uang virtual) demi keamanan. Koneksi
ke broker forex sungguhan lewat **MetaTrader5** sudah disiapkan dan tinggal
diaktifkan saat kamu siap.

## Cara kerja (alur)

```
   Data OHLC            Scenario               Backtest             Selection           Execution
 ┌────────────┐   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────┐   ┌──────────────┐
 │ MT5 / CSV  │ → │ banyak kombinasi │ → │ hitung winrate   │ → │ winrate ≥ 80%│ → │ paper broker │
 │ / sintetis │   │ strategi+param   │   │ (probabilitas)   │   │ & trade cukup│   │ (atau live)  │
 └────────────┘   └──────────────────┘   └──────────────────┘   └──────────────┘   └──────────────┘
```

1. **Data** (`afk_trade/data`): ambil OHLC. Urutan fallback otomatis:
   MetaTrader5 → CSV → data sintetis. Jadi bot bisa diuji **tanpa** MT5/internet.
2. **Skenario** (`afk_trade/scenarios`): hasilkan ratusan kombinasi strategi +
   parameter dari sebuah grid.
3. **Backtest** (`afk_trade/backtest`): untuk tiap skenario, hitung winrate,
   profit factor, total return, max drawdown. **Winrate = probabilitas menang.**
4. **Seleksi** (`afk_trade/selection`): ambil skenario dengan
   `winrate ≥ ambang` **dan** `jumlah trade ≥ min_trades` (agar winrate valid
   secara statistik — mencegah skenario 100% dari hanya 2 trade ikut terpilih).
5. **Eksekusi** (`afk_trade/execution`): kirim sinyal terbaru tiap skenario
   pemenang ke broker. Default `PaperBroker` (simulasi).

## Instalasi

```bash
pip install -r requirements.txt
```

## Menjalankan

```bash
# Pakai ambang 80% sesuai keinginan:
python -m afk_trade.cli --symbol EURUSD --timeframe H1 --threshold 0.80 --min-trades 20

# Uji konsep cepat dengan ambang lebih longgar (data sintetis):
python -m afk_trade.cli --threshold 0.65 --min-trades 15

# Pakai data CSV sendiri (kolom: time,open,high,low,close,volume):
python -m afk_trade.cli --csv data_eurusd.csv --threshold 0.80
```

Opsi penting:

| Flag           | Arti                                              | Default |
|----------------|---------------------------------------------------|---------|
| `--symbol`     | pair, mis. `EURUSD`                               | EURUSD  |
| `--timeframe`  | `M15`, `H1`, `H4`, `D1` …                         | H1      |
| `--bars`       | jumlah bar historis untuk backtest               | 2000    |
| `--threshold`  | ambang winrate (0–1). **0.80 = 80%**             | 0.80    |
| `--min-trades` | jumlah trade minimal agar winrate dipercaya      | 20      |
| `--csv`        | path file CSV OHLC                               | —       |

## Pakai dari kode

```python
from afk_trade import BotConfig
from afk_trade.bot import TradingBot

config = BotConfig(symbol="EURUSD", timeframe="H1", win_threshold=0.80, min_trades=20)
bot = TradingBot(config)
report = bot.run()                      # ambil data, backtest, seleksi, eksekusi (paper)

for w in report.winners:
    print(w.winrate, w.label, "sinyal:", w.last_signal)
print(report.broker_summary)
```

## Menambah strategi sendiri

Tambahkan kelas di `afk_trade/strategies/library.py`, daftarkan di
`STRATEGY_REGISTRY`, dan beri grid parameter di
`afk_trade/scenarios/generator.py`. Strategi hanya perlu mengembalikan Series
sinyal `{-1, 0, 1}` per bar.

## Mengaktifkan MT5 (live) — saat kamu siap

1. Jalankan di Windows dengan MetaTrader5 terpasang & login.
2. `pip install MetaTrader5`.
3. Implementasikan broker live (`afk_trade/execution`) memakai `mt5.order_send`,
   meniru antarmuka `Broker`, lalu masukkan ke `TradingBot(broker=...)`.

Saat ini flag `--live` sengaja **belum mengeksekusi uang asli** sebagai pengaman.

## Test

```bash
pytest -q
```

## ⚠️ Catatan penting

- **Winrate tinggi di backtest ≠ jaminan profit masa depan.** Risiko overfitting
  besar saat mencari skenario terbaik di data historis. Selalu uji di paper
  trading / data baru (out-of-sample) sebelum live.
- Winrate bukan satu-satunya ukuran — perhatikan juga **profit factor** dan
  **max drawdown** (keduanya sudah dihitung).
- Trading forex berisiko tinggi. Gunakan dengan tanggung jawab sendiri.
