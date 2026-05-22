import os
from dotenv import load_dotenv

load_dotenv()

# --- Serial ---
PORT = '/dev/ttyACM0'
BAUD = 115200
FRAME_DELAY = 0.25
RETRY_DELAY = 5

# --- Handshake & Keep-alive ---
HANDSHAKE_TIMEOUT = 3
PING_INTERVAL = 1
PONG_TIMEOUT = 0.5
MAX_MISSED_PONGS = 3

# --- Spotify ---
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
SPOTIFY_SCOPE = (
    "user-library-modify user-follow-modify playlist-modify-public "
    "user-library-read user-read-currently-playing"
)
SPOTIFY_CACHE_PATH = os.path.expanduser("~/spotify_cache")
