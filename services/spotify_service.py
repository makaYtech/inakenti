import sys
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config.settings import (
    SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI, SPOTIFY_SCOPE, SPOTIFY_CACHE_PATH,
    SPOTIFY_PROXY,
)


class SpotifyAuthError(Exception):
    """Не удалось авторизоваться / подключиться к Spotify."""


class SpotifyService:
    def __init__(self):
        session = requests.Session()
        if SPOTIFY_PROXY:
            session.proxies = {"http": SPOTIFY_PROXY, "https": SPOTIFY_PROXY}

        auth_manager = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE,
            cache_path=SPOTIFY_CACHE_PATH,
            open_browser=False,
            requests_session=session,
        )

        # Если кэша токена ещё нет вообще (первый запуск) — понадобится
        # интерактивный ввод (input()). Делать это молча в фоне/systemd нельзя,
        # там либо зависнет, либо упадёт без объяснений.
        if not auth_manager.get_cached_token() and not sys.stdin.isatty():
            raise SpotifyAuthError(
                "Нет сохранённого токена Spotify, а запуск не интерактивный. "
                "Запусти программу один раз вручную из консоли, пройди авторизацию — "
                "после этого токен закэшируется и фоновый запуск будет работать сам."
            )

        self.sp = spotipy.Spotify(
            auth_manager=auth_manager,
            requests_timeout=5,
            retries=1,
            requests_session=session,
        )

        # Форсируем реальный обмен токена ПРЯМО СЕЙЧАС, один раз, здесь —
        # а не лениво при первом is_liked()/like_track() внутри главного цикла.
        try:
            self.sp.current_user()
        except requests.exceptions.ConnectionError as e:
            raise SpotifyAuthError(
                f"Нет сети до Spotify (accounts.spotify.com недоступен напрямую с этой машины). "
                f"Похоже, нужен прокси/VPN — см. переменную SPOTIFY_PROXY. Исходная ошибка: {e}"
            ) from e
        except Exception as e:
            raise SpotifyAuthError(f"Не удалось авторизоваться в Spotify: {e}") from e

    def like_track(self, track_id: str) -> str:
        print(f"like_track: {track_id}")
        if not track_id:
            return "No track ID provided"
        try:
            is_liked = self.sp.current_user_saved_tracks_contains(tracks=[track_id])[0]
            if is_liked:
                self.sp.current_user_saved_tracks_delete([track_id])
                return "unlike"
            else:
                self.sp.current_user_saved_tracks_add([track_id])
                return "like"
        except Exception as e:
            return f"Error liking track: {e}"

    def is_liked(self, track_id: str) -> bool:
        try:
            return self.sp.current_user_saved_tracks_contains(tracks=[track_id])[0]
        except Exception as e:
            print(f"Error checking like: {e}")
            return False