import subprocess
from services.spotify_service import SpotifyService
from core.state_manager import AppState

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
                ["pamixer", "--get-volume"],
                capture_output=True, text=True, timeout=2
            )
            if r.returncode == 0:
                return r.stdout.strip()
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
        result = self.spotify.like_track(track_uri)
        if result == "like":
            state.liked = "like"
            state.has_like = True
        elif result == "unlike":
            state.liked = "unlike"
            state.has_like = False

    def refresh_track_state(self, state: AppState):
        """Обновить состояние, связанное с текущим треком (скролл, URI, лайк)."""
        track = self.get_metadata()
        state.current_track_uri = self.get_track_uri()
        if track and track != state.last_track:
            state.last_track = track
            state.scroll_offset = 0
            # проверить лайк при смене трека
            state.has_like = self.spotify.is_liked(state.current_track_uri)
