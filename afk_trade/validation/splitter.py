"""Pemisah data train/test untuk validasi out-of-sample.

Untuk data deret waktu, split harus **kronologis** (bukan acak): bagian awal
untuk train (mencari & memilih skenario), bagian akhir untuk test (menguji
apakah skenario tetap bagus pada data yang belum pernah dilihat).
"""

from __future__ import annotations

from typing import Tuple

import pandas as pd


def split_data(
    df: pd.DataFrame, test_ratio: float = 0.3
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Pisahkan df secara kronologis menjadi (train, test).

    Args:
        df: data OHLC terurut waktu.
        test_ratio: fraksi bar terakhir yang dipakai sebagai test (0..1).

    Returns:
        (train_df, test_df) dengan index direset.
    """
    if not (0.0 < test_ratio < 1.0):
        raise ValueError("test_ratio harus di antara 0 dan 1")
    n = len(df)
    split_idx = int(n * (1.0 - test_ratio))
    train = df.iloc[:split_idx].reset_index(drop=True)
    test = df.iloc[split_idx:].reset_index(drop=True)
    return train, test
