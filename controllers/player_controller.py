import subprocess
import re
from services.spotify_service import SpotifyService
from core.state_manager import AppState
from core.display import transliterate

class PlayerController:
    def __init__(self, spotify: SpotifyService):
        self.spotify = spotify

    # --- Управление плеером ---
    def next_track(self):
        subprocess.call(["playerctl", "-p", "spotify", "next"])

    def previous_track(self):
        subprocess.call(["playerctl", "-p", "spotify", "previous"])

    def play_pause(self):
        subprocess.call(["playerctl", "-p", "spotify", "play-pause"])

    def volume_up(self):
        subprocess.call(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"])

    def volume_down(self):
        subprocess.call(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"])

    # --- Информация о треке ---
    def get_metadata(self) -> str | None:
        try:
            r = subprocess.run(
                ["playerctl", "-p", "spotify", "metadata", "-f", "{{artist}} - {{title}}"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                txt = r.stdout.strip()
                return ' '.join(txt.split()) if txt != "-" else None
        except Exception:
            pass
        return None

    def get_display_metadata(self, raw_fallback: str | None) -> str | None:
        """
        Готовая строка 'Artist - Title' для показа на LCD.
        Если доступен Spotify API — берём оттуда настоящие символы и сами
        транслитерируем. Если нет — берём playerctl как есть (он уже в латинице).
        """
        if self.spotify is not None:
            meta = self.spotify.get_current_track_meta()
            if meta:
                artist, title = meta
                raw = f"{artist} - {title}".strip(" -")
                return transliterate(raw)
        return transliterate(raw_fallback) if raw_fallback else None

    def get_status(self) -> str | None:
        try:
            r = subprocess.run(
                ["playerctl", "-p", "spotify", "status"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                return r.stdout.strip()
        except Exception:
            pass
        return None

    def get_volume(self) -> str:
        try:
            r = subprocess.run(
                ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                output = r.stdout.strip()
                # Ищем число с плавающей точкой (например, 0.45)
                match = re.search(r'(\d+\.\d+)', output)
                if match:
                    vol_float = float(match.group(1))
                    vol_percent = int(vol_float * 100)   # переводим в проценты
                    return str(vol_percent)
                else:
                    return "--"
        except Exception:
            pass
        return "--"

    def get_track_uri(self) -> str:
        try:
            r = subprocess.run(
                ["playerctl", "-p", "spotify", "metadata", "-f", "{{mpris:trackid}}"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                # убираем префикс "spotify:track:"
                return r.stdout.strip()[19:]
        except Exception:
            pass
        return ""

    # --- Лайки ---
    def like_current_track(self, track_uri: str, state: AppState):
        if self.spotify is None or not track_uri:
            return
        result = self.spotify.like_track(track_uri)
        if result == "like":
            state.liked = "like"
            state.has_like = True
        elif result == "unlike":
            state.liked = "unlike"
            state.has_like = False

    def refresh_track_state(self, state: AppState):
        """Обновить состояние, связанное с текущим треком (скролл, URI, лайк, текст на экране)."""
        raw_track = self.get_metadata()  # дешёвый локальный вызов playerctl — только для детекта смены трека
        state.current_track_uri = self.get_track_uri()

        if raw_track and raw_track != state.last_track:
            state.last_track = raw_track
            state.scroll_offset = 0
            state.display_track = self.get_display_metadata(raw_track) or raw_track
            if self.spotify is not None and state.current_track_uri:
                state.has_like = self.spotify.is_liked(state.current_track_uri)
            else:
                state.has_like = False
        elif not raw_track:
            state.last_track = ""
            state.display_track = ""
