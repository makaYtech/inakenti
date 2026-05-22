import time

def route_command(cmd: str, state, player, system, serial):
    cmd = cmd.strip()
    if not cmd:
        return

    if cmd == "MODE":
        state.toggle_mode()
        mode_name = "SERVICE MODE" if state.mode == "SERVICE" else "PLAYER MODE"
        serial.write_line(f"{'':<16}|{mode_name}\n")
        time.sleep(1.0)  # оригинальная пауза для отображения
        print(f"Режим -> {state.mode}")
        return

    if cmd == "V":
        state.toggle_volume_change()
        return

    if state.mode == "PLAYER":
        if state.volume_change:
            if cmd == "P": player.volume_down()
            elif cmd == "N": player.volume_up()
            elif cmd == "C": player.play_pause()
            elif cmd == "LIKE": player.like_current_track(state.current_track_uri, state)
        else:
            if cmd == "N": player.next_track()
            elif cmd == "P": player.previous_track()
            elif cmd == "C": player.play_pause()
            elif cmd == "LIKE": player.like_current_track(state.current_track_uri, state)
            # После смены трека сбрасываем last_track для обновления
            if cmd in ("N", "P", "C"):
                state.last_track = ""

    elif state.mode == "SERVICE":
        if cmd == "N": system.next_metric()
        elif cmd == "P": system.prev_metric()
