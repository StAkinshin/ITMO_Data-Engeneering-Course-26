
import os
import pandas as pd
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CORE_PATH = os.getenv("CORE_PATH")
DATA_PATH = os.path.join(CORE_PATH, "data")
INPUT_PATH = os.path.join(DATA_PATH, "VK_dataset.csv")
OUTPUT_PATH = os.path.join(DATA_PATH, "VK_dataset_with-text-features.csv")

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


def add_text_features(input_path, output_path):
    df = pd.read_csv(input_path)

    # Проверяем наличие колонки text
    if 'text' not in df.columns:
        raise ValueError("В датасете отсутствует колонка 'text'")

    # Извлекаем признаки
    features = df['text'].apply(extract_text_features)

    # Добавляем признаки к исходному датасету
    features_df = pd.DataFrame(features.tolist(), index=df.index)
    df = pd.concat([df, features_df], axis=1)

    # Сохраняем результат
    df.to_csv(output_path, index=False, encoding='utf-8-sig')

    print(f"Готово! Обработано постов: {len(df)}")
    print(f"Добавлено признаков: {len(features_df.columns)}")
    print(f"Результат сохранён в: {output_path}")


if __name__ == '__main__':
    add_text_features(INPUT_PATH, OUTPUT_PATH)
