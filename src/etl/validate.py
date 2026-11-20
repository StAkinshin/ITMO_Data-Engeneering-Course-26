"""Проверка обязательных полей публикаций перед записью."""

import pandas as pd


def validate(posts: pd.DataFrame) -> None:
    checks = {
        "пустой идентификатор": posts["id"].isna(),
        "повторный идентификатор": posts["id"].duplicated(keep=False) & posts["id"].notna(),
        "некорректная дата": posts["date"].isna(),
        "некорректная ссылка на пост": ~posts["link"].str.fullmatch(
            r"https?://(?:m\.)?vk\.com/wall-?\d+_\d+", na=False
        ),
        "пустой текст": posts["text"].fillna("").str.strip().eq(""),
    }
    errors = [f"{label} ({int(mask.sum())})" for label, mask in checks.items() if mask.any()]
    if errors:
        raise ValueError("Ошибки в данных: " + ", ".join(errors))
