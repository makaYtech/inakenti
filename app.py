import time
from core.env_bootstrap import ensure_spotify_env

ensure_spotify_env()

from config.settings import FRAME_DELAY, RETRY_DELAY
from core.state_manager import AppState
from core.serial_handler import SerialHandler
from core.command_router import route_command
from core.display import (
    build_player_display, build_system_display, build_like_notification
)
from services.spotify_service import SpotifyService
from controllers.player_controller import PlayerController
from controllers.system_controller import SystemController

# ... остальное без изменений


def main():
    state = AppState()
    serial = SerialHandler()
    system = SystemController()
    spotify = None
    retry_time = 0.0
    spotify_retry_time = 0.0
    SPOTIFY_RETRY_INTERVAL = 30.0  # пробовать переподключить Spotify раз в 30с

    spotify = try_init_spotify()
    player = PlayerController(spotify)

    try:
        while True:
            try:
                # переинициализация Spotify, если он упал/не поднялся при старте
                if player.spotify is None:
                    now = time.time()
                    if now - spotify_retry_time > SPOTIFY_RETRY_INTERVAL:
                        player.spotify = try_init_spotify()
                        spotify_retry_time = now

                if not serial.is_connected():
                    now = time.time()
                    if now - retry_time > RETRY_DELAY:
                        if serial.connect():
                            state.last_track = ""
                            print("LCD Reconnected")
                        retry_time = now
                    time.sleep(0.5)
                    continue

                while True:
                    line = serial.read_line()
                    if line is None:
                        break
                    serial.update_pong()
                    if "PONG" in line:
                        continue
                    route_command(line, state, player, system, serial)

                if state.liked in ("like", "unlike"):
                    serial.write_line(build_like_notification(state.liked == "like"))
                    time.sleep(1.0)
                    state.reset_like_status()
                elif state.mode == "PLAYER":
                    player.refresh_track_state(state)
                    serial.write_line(build_player_display(state, player))
                else:
                    serial.write_line(build_system_display(system))

                serial.send_keepalive_if_needed()
                if serial.check_keepalive_timeout():
                    print("LCD Disconnected (keep-alive timeout)")
                    serial.disconnect()
                    continue

                time.sleep(FRAME_DELAY)

            except KeyboardInterrupt:
                raise
            except Exception:
                print("Unhandled error in main loop iteration, continuing")
                time.sleep(FRAME_DELAY)

    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        serial.disconnect()


def try_init_spotify():
    try:
        s = SpotifyService()
        print("Spotify service initialized")
        return s
    except Exception as e:
        print(f"Warning: Spotify service unavailable: {e}")
        return None

if __name__ == "__main__":
    main()
