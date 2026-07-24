import time
import sys
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


def main():
    state = AppState()
    serial = SerialHandler()
    system = SystemController()
    try:
        spotify = SpotifyService()
        print("Spotify service initialized")
    except Exception as e:
        print(f"Warning: Spotify service unavailable: {e}")
        print("Continuing without Spotify features (likes disabled).")
        spotify = None
    player = PlayerController(spotify)

    retry_time = 0.0

    try:
        while True:
            # --- Попытка подключения ---
            if not serial.is_connected():
                now = time.time()
                if now - retry_time > RETRY_DELAY:
                    if serial.connect():
                        state.last_track = ""
                        print("LCD Reconnected")
                    retry_time = now
                time.sleep(0.5)
                continue

            # --- Чтение команд от Arduino ---
            while True:
                line = serial.read_line()
                if line is None:
                    break
                serial.update_pong()  # любой приём = активность
                if "PONG" in line:
                    continue
                route_command(line, state, player, system, serial)

            # --- Обновление дисплея ---
            if state.liked in ("like", "unlike"):
                serial.write_line(build_like_notification(state.liked == "like"))
                time.sleep(1.0)
                state.reset_like_status()
            elif state.mode == "PLAYER":
                player.refresh_track_state(state)
                serial.write_line(build_player_display(state, player))
            else:  # SERVICE
                serial.write_line(build_system_display(system))

            # --- Keep-alive ---
            serial.send_keepalive_if_needed()
            if serial.check_keepalive_timeout():
                print("LCD Disconnected (keep-alive timeout)")
                serial.disconnect()
                continue

            time.sleep(FRAME_DELAY)

    except KeyboardInterrupt:
        print("\nDisconnecting...")
    finally:
        serial.disconnect()

if __name__ == "__main__":
    main()
