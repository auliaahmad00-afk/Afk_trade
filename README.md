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
4. **Seleksi** (`afk_trade/selection`): saring skenario menurut **mode** terpilih,
   selalu dengan syarat `jumlah trade ≥ min_trades` (agar statistik valid —
   mencegah skenario 100% dari hanya 2 trade ikut terpilih):
   - `profit_factor` (default): `profit_factor ≥ pf_threshold` (mis. 1.3).
   - `winrate`: `winrate ≥ win_threshold` (mis. 0.80).
   - `expectancy`: `ekspektasi profit per trade ≥ ambang`.
5. **Validasi** (`afk_trade/validation`): data dibagi **kronologis** menjadi
   train (awal) & test (akhir). Skenario dipilih di **train**, lalu diuji ulang
   di **test** (data yang belum dilihat). Hanya skenario yang **tetap lolos di
   test** (disebut *robust*) yang diteruskan. Ini menyaring skenario yang cuma
   "kebetulan bagus" di masa lalu (overfitting).
6. **Agregasi** (`afk_trade/aggregation`): skenario robust **memberi suara
   (voting berbobot)** untuk menghasilkan **satu keputusan net**
   (LONG/SHORT/FLAT). Mencegah skenario berlawanan saling menetralkan.
7. **Eksekusi** (`afk_trade/execution`): kirim **satu order net** ke broker.
   Default `PaperBroker` (simulasi).

### Validasi out-of-sample (lawan overfitting)

Memilih skenario "terbaik" dari ratusan kombinasi di data historis sangat rawan
**overfitting** — bagus di masa lalu, gagal ke depan. Bot melawannya dengan
**train/test split**:

- `--test-ratio` (default 0.3): fraksi bar **terakhir** jadi data test.
- Skenario dipilih hanya pada train, lalu **dikonfirmasi** pada test.
- *Robust* = lolos kriteria di train **dan** test. Hanya yang robust dieksekusi.
- Sinyal & bobot voting diambil dari hasil **test** (out-of-sample) agar jujur.
- Matikan dengan `--no-validate` (tidak disarankan untuk live).

Contoh nyata dari simulasi XAUUSD: dari 6 kandidat yang lolos train, hanya 2
yang robust — 4 sisanya (PF train 1.15–1.24) **ambruk di test** (PF < 1, return
negatif). Tepat skenario overfit itu yang ditolak.

### Agregasi sinyal (voting)

Daripada tiap skenario terpilih kirim order sendiri (berisiko saling
berlawanan & menetralkan), bot menggabungkan suaranya:

- Tiap skenario menyumbang suara LONG/SHORT/FLAT sesuai sinyal terakhirnya.
- Suara dibobot dengan `--vote-weight`:
  `profit_factor` (default) | `winrate` | `expectancy` | `equal`.
- Arah net = sisi dengan total bobot terbesar. Seri -> FLAT.
- **Konsensus** = `|bobot_long − bobot_short| / total`. Bila di bawah
  `--min-agreement`, bot **tahan diri** (FLAT) karena suara terbelah.
- `--scale-by-confidence` mengecilkan ukuran posisi saat konsensus lemah.

### Strategi yang tersedia

| Nama | Jenis | Ide |
|------|-------|-----|
| `ma_cross` | trend | MA cepat vs MA lambat |
| `rsi_reversion` | mean-reversion | beli oversold, jual overbought |
| `breakout` | breakout | tembus tertinggi/terendah N bar |
| `macd` | **trend-following** | garis MACD vs garis sinyal |
| `supertrend` | **trend-following** | ikut tren berbasis band ATR |
| `momentum` | **trend-following** | ikut momentum + filter EMA |

### ⚠️ Winrate vs trend-following

Strategi **trend-following** (supertrend/macd/momentum) biasanya winrate-nya
**rendah (~35–45%)** tapi **profitable** karena membiarkan tren besar berjalan.
Filter "winrate ≥ 80%" akan **menolak** strategi-strategi ini. Karena itu mode
seleksi default adalah **`profit_factor`**, bukan winrate. Gunakan mode `winrate`
hanya jika fokus pada strategi mean-reversion.

## Instalasi

```bash
pip install -r requirements.txt
```

## Menjalankan

```bash
# Emas (XAUUSD) dengan preset siap-pakai, modal $100, seleksi profit factor:
python -m afk_trade.cli --preset xauusd --balance 100

# EURUSD dengan mode winrate 80% (cocok untuk mean-reversion):
python -m afk_trade.cli --symbol EURUSD --mode winrate --threshold 0.80

# Seleksi profit factor (default) dengan ambang sendiri:
python -m afk_trade.cli --preset xauusd --mode profit_factor --pf-threshold 1.4

# Pakai data CSV sendiri (kolom: time,open,high,low,close,volume):
python -m afk_trade.cli --csv data_xauusd.csv --preset xauusd
```

Opsi penting:

| Flag             | Arti                                                    | Default |
|------------------|---------------------------------------------------------|---------|
| `--symbol`       | pair, mis. `EURUSD`, `XAUUSD`                           | EURUSD  |
| `--preset`       | preset pair: `xauusd` / `eurusd`                       | —       |
| `--timeframe`    | `M15`, `H1`, `H4`, `D1` …                              | H1      |
| `--bars`         | jumlah bar historis untuk backtest                     | 2000    |
| `--mode`         | `profit_factor` / `winrate` / `expectancy`             | profit_factor |
| `--threshold`    | ambang winrate (mode winrate)                          | 0.80    |
| `--pf-threshold` | ambang profit factor (mode profit_factor)              | 1.3     |
| `--balance`      | modal awal paper trading ($)                           | 10000   |
| `--min-trades`   | jumlah trade minimal agar statistik dipercaya          | 20      |
| `--test-ratio`   | fraksi bar terakhir untuk test out-of-sample           | 0.3     |
| `--no-validate`  | matikan validasi train/test                            | (aktif) |
| `--vote-weight`  | bobot voting: `profit_factor`/`winrate`/`expectancy`/`equal` | profit_factor |
| `--min-agreement`| ambang konsensus voting 0–1 (di bawahnya FLAT)         | 0.0     |
| `--scale-by-confidence` | skala posisi dengan derajat konsensus           | off     |
| `--csv`          | path file CSV OHLC                                     | —       |

### Preset XAUUSD (emas)

`BotConfig.preset("xauusd")` mengaktifkan profil emas: strategi trend-following
diprioritaskan, spread lebih lebar, mode seleksi profit factor, dan **leverage
1:100** (tanpa leverage, akun $100 tak cukup membuka posisi emas seharga ~$2.300).

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
