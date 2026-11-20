import argparse
import os

from dotenv import load_dotenv
from pandas import DataFrame
from pandas.api.types import is_float_dtype, is_integer_dtype
from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    URL,
    create_engine,
    func,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from etl.extract import extract
from etl.load import MAX_ROWS
from etl.main import DATASET_URL
from etl.transform import transform
from etl.validate import validate

TABLE_NAME = "akinshinsd"
DRIVERS = {"postgresql": "postgresql+psycopg", "mysql": "mysql+pymysql"}


def connection_url(database: str) -> URL:
    settings = ("DB_ENGINE", "DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD")
    missing = [name for name in settings if not os.environ.get(name)]
    if missing:
        raise ValueError("Не заданы переменные окружения: " + ", ".join(missing))

    driver = DRIVERS.get(os.environ["DB_ENGINE"])
    if driver is None:
        raise ValueError("DB_ENGINE должен быть postgresql или mysql.")
    try:
        port = int(os.environ["DB_PORT"])
    except ValueError:
        raise ValueError("DB_PORT должен быть целым числом от 1 до 65535.") from None
    if not 1 <= port <= 65535:
        raise ValueError("DB_PORT должен быть целым числом от 1 до 65535.")

    return URL.create(
        driver,
        host=os.environ["DB_HOST"],
        port=port,
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=database,
    )


def write_rows(engine: Engine, posts: DataFrame) -> int:
    if len(posts) != MAX_ROWS:
        raise ValueError(f"Для записи требуется ровно {MAX_ROWS} строк.")

    records = posts.assign(date=posts["date"].dt.strftime("%Y-%m-%d"))
    columns = []
    for name, dtype in records.dtypes.items():
        if name == "id":
            columns.append(Column(name, String(128), primary_key=True))
        elif is_integer_dtype(dtype):
            columns.append(Column(name, Integer))
        elif is_float_dtype(dtype):
            columns.append(Column(name, Float(53)))
        else:
            columns.append(Column(name, Text))

    table = Table(TABLE_NAME, MetaData(), *columns)
    rows = records.astype(object).where(records.notna(), None).to_dict("records")
    with engine.begin() as connection:
        table.create(connection, checkfirst=True)
        connection.execute(table.delete())
        connection.execute(table.insert(), rows)
        count = connection.scalar(select(func.count()).select_from(table))
        if count != MAX_ROWS:
            raise ValueError(f"Ожидалось {MAX_ROWS} строк в таблице, получено {count}.")
    return count


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, choices=("freezone", "homeworks"))
    parser.add_argument("--source", default=os.getenv("DATASET_URL") or DATASET_URL)
    args = parser.parse_args()

    try:
        url = connection_url(args.target)
        posts = transform(extract(args.source))
        validate(posts)
        engine = create_engine(url, hide_parameters=True)
        try:
            count = write_rows(engine, posts.head(MAX_ROWS))
        finally:
            engine.dispose()
    except SQLAlchemyError:
        parser.exit(
            1,
            "Ошибка записи в БД. Проверьте доступность сервера, параметры подключения "
            "и права на запись в выбранную базу. Подробности подключения скрыты.\n",
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"Ошибка: {error}\n")

    print(f"Записано {count} строк в {args.target}, таблица {TABLE_NAME}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
