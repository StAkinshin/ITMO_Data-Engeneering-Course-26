import os
import pandas as pd

from dotenv import load_dotenv

# ============================================================
# НАСТРОЙКИ
# ============================================================

load_dotenv()

DATASET_URL = os.getenv("DATASET_URL")
CORE_PATH = os.getenv("CORE_PATH")

DATA_PATH = os.path.join(CORE_PATH, "data")
OUTPUT_FILE = os.path.join(DATA_PATH, "VK_dataset.parquet")


# ============================================================
# ЗАГРУЗКА ДАТАСЕТА
# ============================================================

def load_dataset():
    """Загружает датасет по ссылке с Google Drive."""

    if not DATASET_URL:
        raise ValueError("Не найдена ссылка DATASET_URL в файле .env")

    try:
        print("Загрузка датасета с Google Drive...")

        df = pd.read_csv(
            DATASET_URL,
            sep=",",
            encoding="utf-8-sig",
            engine="python"
        )

        print("\nДатасет успешно загружен.")
        print(f"Количество строк: {len(df)}")
        print(f"Количество столбцов: {len(df.columns)}")

        return df

    except Exception as error:
        print(f"Ошибка загрузки датасета: {error}")
        raise


# ============================================================
# ПРИВЕДЕНИЕ ТИПОВ ДАННЫХ
# ============================================================

def convert_dtypes(df):
    """Приводит столбцы датасета к необходимым типам данных."""

    df = df.copy()

    # Текстовые признаки
    df["id"] = df["id"].astype("string")
    df["search_query"] = df["search_query"].astype("string")
    df["city"] = df["city"].astype("string")
    df["region"] = df["region"].astype("string")
    df["author_link"] = df["author_link"].astype("string")
    df["link"] = df["link"].astype("string")
    df["text"] = df["text"].astype("string")

    # Категориальные признаки
    df["source_type"] = df["source_type"].astype("category")
    df["text_has_url"] = df["text_has_url"].astype("category")
    df["text_has_hashtag"] = df["text_has_hashtag"].astype("category")
    df["text_has_emoji"] = df["text_has_emoji"].astype("category")

    # Дата
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    return df



# ============================================================
# СОХРАНЕНИЕ ДАТАСЕТА
# ============================================================

def save_dataset(df):
    """Сохраняет DataFrame в формате Parquet."""

    os.makedirs(DATA_PATH, exist_ok=True)

    try:
        df.to_parquet(
            OUTPUT_FILE,
            index = False,
            engine = "pyarrow"
        )

        print(f"\nДатасет сохранён: {OUTPUT_FILE}")

    except Exception as error:
        print(f"Ошибка сохранения датасета: {error}")
        raise


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

def main():

    df = load_dataset()

    print("\nПриведение типов данных...")

    df = convert_dtypes(df)

    print("\nТипы данных после преобразования:")
    print(df.dtypes)

    save_dataset(df)


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    main()