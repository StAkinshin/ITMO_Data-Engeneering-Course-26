"""Чтение исходного CSV из локального файла или по прямой ссылке."""

from urllib.parse import urlsplit
from urllib.request import urlopen

import pandas as pd


def extract(source: str) -> pd.DataFrame:
    options = {"encoding": "utf-8-sig", "dtype": "string", "keep_default_na": False}
    if urlsplit(source).scheme in {"http", "https"}:
        with urlopen(source, timeout=60) as response:
            return pd.read_csv(response, **options)
    return pd.read_csv(source, **options)
