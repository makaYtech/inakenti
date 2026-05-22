import spotipy
from spotipy.oauth2 import SpotifyOAuth
from config.settings import (
    SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET,
    SPOTIFY_REDIRECT_URI, SPOTIFY_SCOPE, SPOTIFY_CACHE_PATH
)

class SpotifyService:
    def __init__(self):
        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=SPOTIFY_SCOPE,
            cache_path=SPOTIFY_CACHE_PATH
        ))

    def like_track(self, track_id: str) -> str:
        """Поставить / убрать лайк. Возвращает статусное сообщение."""
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
        """Проверить, лайкнут ли трек. Ошибки проглатываем, возвращаем False."""
        try:
            return self.sp.current_user_saved_tracks_contains(tracks=[track_id])[0]
        except Exception as e:
            print(f"Error checking like: {e}")
            return False
