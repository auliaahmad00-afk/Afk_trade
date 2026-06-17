"""Afk_trade - bot trading yang memilih skenario berdasarkan probabilitas (winrate).

Alur utama:
1. Hasilkan banyak skenario strategi (kombinasi strategi + parameter).
2. Backtest tiap skenario pada data historis -> hitung winrate (probabilitas menang).
3. Pilih skenario dengan winrate di atas ambang (default 80%) dan jumlah trade cukup.
4. Eksekusi sinyal terbaru dari skenario terpilih lewat broker (paper trading dulu).
"""

from .config import BotConfig

__all__ = ["BotConfig"]
__version__ = "0.1.0"
