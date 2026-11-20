"""Транзакционная запись итоговой выборки в SQLite."""

import sqlite3
from contextlib import closing
from pathlib import Path

import pandas as pd
from pandas.api.types import is_float_dtype, is_integer_dtype

MAX_ROWS = 100


def load(posts: pd.DataFrame, database: Path) -> int:
    if not 1 <= len(posts) <= MAX_ROWS:
        raise ValueError(f"Для загрузки требуется от 1 до {MAX_ROWS} строк.")

    records = posts.assign(date=posts["date"].dt.strftime("%Y-%m-%d"))
    definitions = []
    for column, dtype in records.dtypes.items():
        if column == "id":
            definitions.append('"id" TEXT NOT NULL PRIMARY KEY')
        elif is_integer_dtype(dtype):
            definitions.append(f'"{column}" INTEGER')
        elif is_float_dtype(dtype):
            definitions.append(f'"{column}" REAL')
        else:
            definitions.append(f'"{column}" TEXT')
    placeholders = ", ".join("?" for _ in definitions)
    rows = records.astype(object).where(records.notna(), None)

    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DROP TABLE IF EXISTS vk_posts")
        connection.execute(f"CREATE TABLE vk_posts ({', '.join(definitions)})")
        connection.executemany(
            f"INSERT INTO vk_posts VALUES ({placeholders})",
            rows.itertuples(index=False, name=None),
        )
    return len(records)
