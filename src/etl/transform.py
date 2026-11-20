"""Нормализация полей публикаций и расчёт текстовых признаков."""

import re

import pandas as pd

SOURCE_COLUMNS = (
    "id", "search_query", "city", "region", "source_type",
    "date", "author_link", "link", "text",
)


def transform(raw: pd.DataFrame) -> pd.DataFrame:
    missing = set(SOURCE_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"В CSV отсутствуют столбцы: {', '.join(sorted(missing))}")
    if raw.empty:
        raise ValueError("В CSV нет публикаций.")

    posts = raw.loc[:, list(SOURCE_COLUMNS)].astype("string")
    for column in posts.columns.drop("text"):
        posts[column] = posts[column].str.strip().replace("", pd.NA)
    posts["date"] = pd.to_datetime(posts["date"], format="%Y-%m-%d", errors="coerce")
    features = pd.DataFrame(
        [extract_text_features(value) for value in posts["text"]],
        index=posts.index,
    )
    return pd.concat([posts, features], axis=1)


def extract_text_features(text):
    if pd.isna(text):
        text = ""

    text = str(text)

    # Базовая токенизация
    words = re.findall(r'\b\w+\b', text.lower())
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]

    # Символьные признаки
    chars = len(text)
    letters = re.findall(r'[a-zA-Zа-яА-ЯёЁ]', text)
    uppercase = re.findall(r'[A-ZА-ЯЁ]', text)

    # Слова
    word_count = len(words)
    unique_words = len(set(words))

    # Ссылки, хештеги, упоминания
    urls = re.findall(r'https?://\S+|www\.\S+', text)
    hashtags = re.findall(r'#\w+', text)
    mentions = re.findall(r'@\w+', text)

    # Эмодзи (приближённый подсчёт)
    emojis = re.findall(
        r'[\U0001F300-\U0001FAFF'
        r'\U00002600-\U000027BF]',
        text
    )

    return {
        'text_char_count': chars,
        'text_word_count': word_count,
        'text_sentence_count': len(sentences),
        'text_paragraph_count': len(text.splitlines()),
        'text_avg_word_length': (
            sum(map(len, words)) / word_count if word_count else 0
        ),
        'text_avg_sentence_length': (
            word_count / len(sentences) if sentences else 0
        ),
        'text_unique_words': unique_words,
        'text_unique_word_ratio': (
            unique_words / word_count if word_count else 0
        ),
        'text_url_count': len(urls),
        'text_hashtag_count': len(hashtags),
        'text_mention_count': len(mentions),
        'text_emoji_count': len(emojis),
        'text_digit_count': sum(c.isdigit() for c in text),
        'text_punctuation_count': sum(
            not c.isalnum() and not c.isspace() for c in text
        ),
        'text_uppercase_ratio': (
            len(uppercase) / len(letters) if letters else 0
        ),
        'text_has_question': int('?' in text),
        'text_has_exclamation': int('!' in text),
        'text_is_uppercase': int(
            text.isupper() and bool(letters)
        ),
        'text_has_url': int(bool(urls)),
        'text_has_hashtag': int(bool(hashtags)),
        'text_has_emoji': int(bool(emojis)),
    }
