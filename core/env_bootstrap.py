import os
import sys
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"  # корень проекта

REQUIRED_VARS = [
    ("SPOTIFY_CLIENT_ID", "Client ID (Spotify Developer Dashboard)"),
    ("SPOTIFY_CLIENT_SECRET", "Client Secret (Spotify Developer Dashboard)"),
    ("SPOTIFY_REDIRECT_URI", "Redirect URI, например http://127.0.0.1:8888/callback "
                              "(должен совпадать 1-в-1 с указанным в настройках приложения на Spotify)"),
]

OPTIONAL_VARS = [
    ("SPOTIFY_PROXY", "Прокси для доступа к Spotify API, если напрямую не открывается "
                       "(например socks5h://127.0.0.1:1080 или http://127.0.0.1:8080). "
                       "Если не нужен — просто Enter"),
]


def _read_existing(path: Path) -> dict:
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip()
    return values


def _write_env(path: Path, values: dict):
    # пишем только непустые значения — если человек пропустил опциональное
    # поле, не нужно засорять .env строкой "SPOTIFY_PROXY="
    lines = [f"{key}={val}" for key, val in values.items() if val]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_spotify_env() -> bool:
    """
    Проверяет .env. Если не хватает обязательных переменных и запуск
    интерактивный — спрашивает и сохраняет. Опциональные (SPOTIFY_PROXY)
    можно пропустить пустым вводом. Возвращает True, если конфиг готов
    к использованию, False — если Spotify придётся оставить выключенным
    на этот запуск.
    """
    existing = _read_existing(ENV_PATH)
    missing_required = [(n, d) for n, d in REQUIRED_VARS if not existing.get(n)]

    if not missing_required:
        return True

    if not sys.stdin.isatty():
        names = ", ".join(n for n, _ in missing_required)
        print(f"[env] Не хватает переменных для Spotify: {names}. "
              f"Spotify отключён. Запусти из терминала, чтобы настроить .env интерактивно.")
        return False

    print("=" * 50)
    print("Не найден .env (или он неполный) — нужна настройка Spotify API.")
    print("Данные бери здесь: https://developer.spotify.com/dashboard")
    print("=" * 50)

    answers = dict(existing)

    # --- обязательные ---
    for name, desc in missing_required:
        while True:
            value = input(f"{name} ({desc}): ").strip()
            if value:
                answers[name] = value
                break
            print("  Пусто нельзя, введи значение.")

    # --- опциональные (можно пропустить Enter'ом) ---
    for name, desc in OPTIONAL_VARS:
        if existing.get(name):
            continue  # уже задано раньше — не спрашиваем повторно
        value = input(f"{name} ({desc}): ").strip()
        if value:
            answers[name] = value

    _write_env(ENV_PATH, answers)
    print(f"[env] Сохранено в {ENV_PATH}")

    for key, val in answers.items():
        os.environ[key] = val

    return True