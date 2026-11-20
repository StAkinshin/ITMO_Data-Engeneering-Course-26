"""Командная строка ETL для датасета публикаций ВКонтакте."""

import argparse
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

from .extract import extract
from .load import MAX_ROWS, load
from .transform import transform
from .validate import validate

DATASET_URL = "https://drive.google.com/uc?export=download&id=1YPNkX6ElmOaTOVze2l-uAtU4jS1q5ZHX"


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Подготовить публикации ВКонтакте и записать выборку в SQLite.",
    )
    parser.add_argument("--database", required=True, type=Path, help="Путь к файлу SQLite.")
    parser.add_argument(
        "--source",
        default=os.getenv("DATASET_URL") or DATASET_URL,
        help="Путь к CSV или прямая ссылка на него.",
    )
    parser.add_argument(
        "--limit", type=int, default=MAX_ROWS, help="Число строк для записи, от 1 до 100.",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= MAX_ROWS:
        parser.error(f"--limit должен быть от 1 до {MAX_ROWS}.")

    try:
        posts = transform(extract(args.source))
        validate(posts)
        count = load(posts.head(args.limit), args.database)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.exit(1, f"Ошибка ETL: {error}\n")
    print(f"Записано {count} из {len(posts)} строк в {args.database} (таблица vk_posts).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
