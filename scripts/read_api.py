import os
import json
import time
import logging
import vk_api
import pandas as pd

from datetime import datetime, timedelta
from dotenv import load_dotenv
from vk_api.exceptions import ApiError, VkApiError


# ============================================================
# НАСТРОЙКИ
# ============================================================

load_dotenv()

VK_TOKEN = os.getenv("VK_SERVICE_TOKEN")
CORE_PATH = os.getenv("CORE_PATH")

if not VK_TOKEN:
    raise ValueError("Не найден VK_SERVICE_TOKEN в файле .env")

if not CORE_PATH:
    raise ValueError("Не найден CORE_PATH в файле .env")

DATA_PATH = os.path.join(CORE_PATH, "data")
INPUT_FILENAME = os.path.join(DATA_PATH, "queries.json")
OUTPUT_FILE = os.path.join(DATA_PATH, "VK_dataset.csv")
LOG_FILE = os.path.join(DATA_PATH, "vk_parser.log")

MAX_POSTS_PER_QUERY = 100
DAYS_TO_CHECK = 365
REQUEST_COUNT = 200
REQUEST_DELAY = 0.5

COLUMNS = [
    "id",
    "search_query",
    "city",
    "region",
    "source_type",
    "date",
    "author_link",
    "link",
    "text"
]


# ============================================================
# ЛОГИРОВАНИЕ
# ============================================================

os.makedirs(DATA_PATH, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# ============================================================
# ПОДГОТОВКА ЗАПРОСОВ
# ============================================================

def load_queries():
    """Загружает поисковые запросы из JSON."""

    if not os.path.exists(INPUT_FILENAME):
        raise FileNotFoundError(
            f"Не найден файл с запросами: {INPUT_FILENAME}"
        )

    with open(INPUT_FILENAME, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "JSON должен содержать список запросов."
        )

    queries = []

    for item in data:
        if isinstance(item, dict):
            query = item.get("query", "")
            city = item.get("city", "")
            region = item.get("region", "")

        else:
            continue

        if query and str(query).strip():
            queries.append({
                "query": str(query).strip(),
                "city": city,
                "region": region
            })

    if not queries:
        raise ValueError(
            "Список запросов пуст. Проверьте queries.json."
        )

    logger.info(f"Загружено поисковых запросов: {len(queries)}")

    return queries


# ============================================================
# ПОДКЛЮЧЕНИЕ К VK API
# ============================================================

def connect_vk():
    logger.info("Подключение к VK API...")

    try:
        session = vk_api.VkApi(
            token=VK_TOKEN,
            api_version="5.199"
        )

        vk = session.get_api()

        logger.info("Подключение успешно.")
        return vk

    except Exception as error:
        logger.exception(f"Ошибка подключения: {error}")
        raise


# ============================================================
# ФОРМАТИРОВАНИЕ ПОСТА
# ============================================================

def format_post(post, query, city, region):
    """Приводит пост к формату датасета."""

    owner_id = post.get("owner_id")
    post_id = post.get("id")

    if owner_id is None or post_id is None:
        return None

    if owner_id > 0:
        author_link = f"https://vk.com/id{owner_id}"
    else:
        author_link = f"https://vk.com/public{abs(owner_id)}"

    return {
        "id": f"{owner_id}_{post_id}",
        "search_query": query,
        "city": city,
        "region": region,
        "source_type": "newsfeed",
        "date": datetime.fromtimestamp(
            post["date"]
        ).strftime("%Y-%m-%d"),
        "author_link": author_link,
        "link": f"https://vk.com/wall{owner_id}_{post_id}",
        "text": post.get("text", "").replace("\n", " ")[:5000]
    }


# ============================================================
# ПОИСК ПОСТОВ
# ============================================================

def search_posts(vk, query, city, region, limit_date):
    """Ищет посты и подробно логирует процесс."""

    results = []
    seen_links = set()

    start_from = None
    page = 0

    stats = {
        "received": 0,
        "old_posts": 0,
        "empty_text": 0,
        "duplicates": 0,
        "accepted": 0
    }

    logger.info("=" * 60)
    logger.info(f"ПОИСКОВЫЙ ЗАПРОС: {query}")
    logger.info("=" * 60)

    while len(results) < MAX_POSTS_PER_QUERY:
        page += 1

        try:
            params = {
                "q": query,
                "count": REQUEST_COUNT,
                "extended": 1,
                "start_time": int(limit_date.timestamp()),
                "end_time": int(datetime.now().timestamp())
            }

            if start_from:
                params["start_from"] = start_from

            logger.info(
                f"Запрос страницы {page}. "
                f"Получено ранее: {len(results)}"
            )

            response = vk.newsfeed.search(**params)

            if not isinstance(response, dict):
                logger.error(
                    f"Неожиданный формат ответа VK: "
                    f"{type(response)}"
                )
                break

            items = response.get("items", [])

            logger.info(
                f"Ответ VK: total_count="
                f"{response.get('total_count', 'не указан')}, "
                f"items={len(items)}"
            )

            if page == 1 and items:
                logger.info(
                    f"Пример полученного поста: "
                    f"{str(items[0])[:500]}"
                )

            if not items:
                logger.warning(
                    "VK вернул пустой список постов. "
                    "Поиск завершён."
                )
                break

            stats["received"] += len(items)

            for post in items:
                post_date = datetime.fromtimestamp(post["date"])

                if post_date < limit_date:
                    stats["old_posts"] += 1
                    continue

                post_data = format_post(
                    post, query, city, region
                )

                if post_data is None:
                    continue

                if not post_data["text"].strip():
                    stats["empty_text"] += 1
                    continue

                if post_data["link"] in seen_links:
                    stats["duplicates"] += 1
                    continue

                results.append(post_data)
                seen_links.add(post_data["link"])

                stats["accepted"] += 1

                if len(results) >= MAX_POSTS_PER_QUERY:
                    break

            logger.info(
                f"Страница {page}: "
                f"добавлено постов: {len(results)}, "
                f"всего получено: {stats['received']}"
            )

            if len(results) >= MAX_POSTS_PER_QUERY:
                logger.info("Достигнут лимит постов.")
                break

            next_from = response.get("next_from")

            if not next_from:
                logger.info(
                    "VK не вернул next_from. "
                    "Дальнейших страниц нет."
                )
                break

            start_from = next_from

            time.sleep(REQUEST_DELAY)

        except ApiError as error:
            logger.error(
                f"ОШИБКА VK API | "
                f"Запрос: {query} | "
                f"Код: {error.code} | "
                f"Описание: {error}"
            )
            break

        except VkApiError as error:
            logger.exception(
                f"ОШИБКА VK API | Запрос: {query}: {error}"
            )
            break

        except Exception as error:
            logger.exception(
                f"НЕОЖИДАННАЯ ОШИБКА | "
                f"Запрос: {query}: {error}"
            )
            break

    logger.info("-" * 60)
    logger.info(f"РЕЗУЛЬТАТ ЗАПРОСА: {query}")
    logger.info(f"Получено от VK: {stats['received']}")
    logger.info(f"Старых постов: {stats['old_posts']}")
    logger.info(f"Постов без текста: {stats['empty_text']}")
    logger.info(f"Дубликатов: {stats['duplicates']}")
    logger.info(f"Добавлено: {stats['accepted']}")
    logger.info("-" * 60)

    return results


# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================

def main():

    logger.info("=" * 60)
    logger.info("ЗАПУСК VK PARSER")
    logger.info("=" * 60)

    try:
        queries = load_queries()
        vk = connect_vk()
    except Exception as error:
        logger.critical(f"Не удалось начать сбор: {error}")
        return
    limit_date = datetime.now() - timedelta(
        days=DAYS_TO_CHECK
    )
    logger.info(
        f"Период сбора: с {limit_date.strftime('%Y-%m-%d')} "
        f"по {datetime.now().strftime('%Y-%m-%d')}"
    )
    all_posts = []
    seen_links = set()

    for index, query_data in enumerate(queries, 1):
        query = query_data["query"]
        city = query_data["city"]
        region = query_data["region"]

        logger.info(
            f"\nЗАПРОС {index}/{len(queries)}"
        )

        posts = search_posts(
            vk=vk,
            query=query,
            city=city,
            region=region,
            limit_date=limit_date
        )

        for post in posts:

            if post["link"] not in seen_links:
                all_posts.append(post)
                seen_links.add(post["link"])

        logger.info(
            f"Итого по запросу '{query}': {len(posts)}"
        )

        time.sleep(1)

    # ========================================================
    # СОХРАНЕНИЕ ДАТАСЕТА
    # ========================================================

    logger.info("=" * 60)
    logger.info("СОХРАНЕНИЕ РЕЗУЛЬТАТОВ")
    logger.info("=" * 60)

    df = pd.DataFrame(
        all_posts,
        columns=COLUMNS
    )

    try:
        df.to_csv(
            OUTPUT_FILE,
            index=False,
            encoding="utf-8-sig"
        )

        logger.info(f"Всего собрано постов: {len(df)}")
        logger.info(f"Файл сохранён: {OUTPUT_FILE}")

        if df.empty:
            logger.warning(
                "ДАТАСЕТ ПУСТОЙ! "
                "Проверьте ошибки выше в логе."
            )

        else:
            logger.info(
                f"Уникальных запросов: "
                f"{df['search_query'].nunique()}"
            )

            logger.info(
                f"Диапазон дат: "
                f"{df['date'].min()} — {df['date'].max()}"
            )

            logger.info("\nПервые 5 строк датасета:")
            logger.info("\n" + df.head().to_string())

    except Exception as error:
        logger.exception(
            f"Ошибка сохранения CSV: {error}"
        )

    logger.info("=" * 60)
    logger.info("РАБОТА ПАРСЕРА ЗАВЕРШЕНА")
    logger.info("=" * 60)


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":
    main()