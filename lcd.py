import serial
import subprocess
import sys
import time
import os
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

PORT = '/dev/ttyACM0'
BAUD = 115200
FRAME_DELAY = 0.25
RETRY_DELAY = 5

# HANDSHAKE
HANDSHAKE_TIMEOUT = 3
PING_INTERVAL = 1
PONG_TIMEOUT = 0.5
MAX_MISSED_PONGS = 3

# SPOTIFY
load_dotenv()
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")

state = {
    "mode": "PLAYER",
    "svc_idx": 0,
    "last_track": "",
    "scroll_offset": 0,
    "curent_track_uri": "",
    "volume_change": False,
    "liked": "",
    "has_like": False
}

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-library-modify user-follow-modify playlist-modify-public user-library-read user-read-currently-playing",
    cache_path="./spotify_cache"
))

def like_track(track_id: str) -> str:
    print(track_id)
    if not track_id:
        return "No track ID provided"
    try:
        is_liked = sp.current_user_saved_tracks_contains(tracks=[track_id])[0]
        if is_liked:
            sp.current_user_saved_tracks_delete([track_id])
            state["liked"] = "unlike"
            return "Track unliked"
        else:
            sp.current_user_saved_tracks_add([track_id])
            state["liked"] = "like"
            state["has_like"] = False
            return "Track liked"
    except Exception as e:
        return f"Error liking track: {e}"

def like_checker(track_id: str):
    try:
        is_liked = sp.current_user_saved_tracks_contains(tracks=[track_id])[0]
        if is_liked == True:
            state["has_like"] = True
        else:
            state["has_like"] = False
    except Exception as e:
        print(f"Error checking like: {e}")

def transliterate(text):
    cyr2lat = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
    }
    return ''.join(cyr2lat.get(c, c) for c in text)

def get_cpu_info():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            r = subprocess.run(["top", "-bn1"], capture_output=True, text=True, timeout=2)
            for line in r.stdout.splitlines():
                if "Cpu(s)" in line or "%Cpu" in line:
                    match = re.search(r'([\d.]+)[%]?\s*id', line)
                    if match:
                        idle = float(match.group(1).replace(',', '.'))
                        usage = 100 - idle
                        break
            return f"{float(f.read().strip()) / 1000:.0f} C  {usage:.1f}%"
    except: return "N/A"

def get_gpu_info():
    try:
        for path in ["/sys/class/drm/card0/device/hwmon/hwmon0/temp1_input",
                     "/sys/class/thermal/thermal_zone1/temp"]:
            if os.path.exists(path):
                usage = subprocess.check_output(
                    "cat /sys/class/drm/card*/device/gpu_busy_percent 2>/dev/null | head -n1",
                    shell=True, text=True
                ).strip()
                with open(path) as f: return f"{float(f.read().strip()) / 1000:.0f} C  {usage}%"
    except: pass
    return "N/A"

def get_ram_usage():
    try:
        r = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=2)
        usage = subprocess.check_output(["free", "-h"], text=True)
        for line in usage.splitlines():
            parts = line.split()
            if parts and parts[0] == "Mem:":
                available = parts[-1]
                break
        total, used = map(int, r.stdout.splitlines()[1].split()[1:3])
        return f"{int((used / total) * 100)}%, {available.replace('Gi',' Gb')}"
    except: return "N/A"

# МЕТРИКИ ДЛЯ SERVICE MODE
SERVICE_METRICS = [
    ("CPU", get_cpu_info),
    ("GPU", get_gpu_info),
    ("RAM", get_ram_usage)
]

def safe_write(msg):
    global ser
    try:
        if ser and ser.is_open:
            ser.write(msg.encode('latin-1'))
    except (serial.SerialException, OSError):
        ser = None

# СКРОЛЛЕР
def marquee(text, offset, width):
    if len(text) <= width: return text.center(width), offset
    padded = text + " " * (width - 8)
    start = offset % len(padded)
    return (padded * 2)[start:start + width], offset + 1

# МАРШРУТИЗАЦИЯ КОМАНД
def route_cmd(cmd):
    cmd = cmd.strip()
    global state
    if cmd == "MODE":
        state["mode"] = "SERVICE" if state["mode"] == "PLAYER" else "PLAYER"
        state["svc_idx"] = 0
        state["scroll_offset"] = 0
        state["last_track"] = ""
        mode_name = "SERVICE MODE" if state["mode"] == "SERVICE" else "PLAYER MODE"
        ser.write(f"{'':<16}|{mode_name}\n".encode())
        time.sleep(1.0)
        print(f"Режим -> {state['mode']}")
        return
    if cmd == "V":
        state["volume_change"] = not state["volume_change"]
    if state["mode"] == "PLAYER":
        if state["volume_change"]:
            if cmd == "P": subprocess.call(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"])
            elif cmd == "N": subprocess.call(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"])
            elif cmd == "C": subprocess.call(["playerctl", "-p", "spotify", "play-pause"])
            elif cmd == "LIKE":
                result = like_track(state["curent_track_uri"])
                print(result)
        else:
            if cmd == "N": subprocess.call(["playerctl", "-p", "spotify", "next"]); state["last_track"] = ""
            elif cmd == "P": subprocess.call(["playerctl", "-p", "spotify", "previous"]); state["last_track"] = ""
            elif cmd == "C": subprocess.call(["playerctl", "-p", "spotify", "play-pause"]); state["last_track"] = ""
            elif cmd == "LIKE":
                result = like_track(state["curent_track_uri"])
                print(result)

    elif state["mode"] == "SERVICE":  # SERVICE MODE
        if cmd == "N": state["svc_idx"] = (state["svc_idx"] + 1) % len(SERVICE_METRICS)
        elif cmd == "P": state["svc_idx"] = (state["svc_idx"] - 1) % len(SERVICE_METRICS)

# ОБНОВЛЕНИЕ ДИСПЛЕЯ
def update_display():
    global state
    if state["liked"] == "":
        if state["mode"] == "PLAYER":
            track = get_spotify_metadata()
            if track:
                track = transliterate(track)
            status = get_spotify_status()
            volume = get_curent_volume()
            state["curent_track_uri"] = get_spotify_track_uri()
            if track and track != state["last_track"]:
                state["last_track"] = track
                state["scroll_offset"] = 0
                like_checker(state["curent_track_uri"])
            if state["has_like"] == False:
                if track:
                    icon = f" {chr(0x84)}" if status == "Playing" else f" {chr(0x82)}" if status == "Paused" else " "
                    frame, state["scroll_offset"] = marquee(track, state["scroll_offset"], 16)
                    vol_str = f"{volume}%" if int(volume) >= 0 else "--%"
                    l0 = f"{frame}".ljust(16)
                    if state["volume_change"]:
                        l1 = f"{icon}  {chr(0x93)} CVol: {vol_str}".ljust(16)
                    else:
                        l1 = f"{icon}  {chr(0x93)}  Vol: {vol_str}".ljust(16)
                    safe_write(f"{l0}|{l1}\n")
            else:
                if track:
                    icon = f" {chr(0x84)}" if status == "Playing" else f" {chr(0x82)}" if status == "Paused" else " "
                    frame, state["scroll_offset"] = marquee(track, state["scroll_offset"], 16)
                    vol_str = f"{volume}%" if int(volume) >= 0 else "--%"
                    l0 = f"{frame}".ljust(16)
                    if state["volume_change"]:
                        l1 = f"{icon}  {chr(0x92)} CVol: {vol_str}".ljust(16)
                    else:
                        l1 = f"{icon}  {chr(0x92)}  Vol: {vol_str}".ljust(16)
                    safe_write(f"{l0}|{l1}\n")
        else:
            name, func = SERVICE_METRICS[state["svc_idx"]]
            val = func()
            l0 = f"[SYS] {name}".ljust(16)
            l1 = val.ljust(16)
            safe_write(f"{l0}|{l1}\n")
    elif state["liked"] == "like":
        l0 = f"LIKED".ljust(16)
        safe_write(f"{l0}\n")
        time.sleep(1.0)
        state["liked"] = ""
    elif state["liked"] == "unlike":
        l0 = f"UNLIKED".ljust(16)
        safe_write(f"{l0}\n")
        time.sleep(1.0)
        state["liked"] = ""

# PLAYERCTL ХЕЛПЕРЫ
def get_spotify_metadata():
    try:
        r = subprocess.run(["playerctl", "-p", "spotify", "metadata", "-f", "{{artist}} - {{title}}"],
                           capture_output=True, text=True, timeout=2)
        if r.returncode == 0:
            txt = r.stdout.strip()
            return ' '.join(txt.split()) if txt != "-" else None
    except: pass
    return None

def get_spotify_status():
    try:
        r = subprocess.run(["playerctl", "-p", "spotify", "status"],
                           capture_output=True, text=True, timeout=2)
        if r.returncode == 0: return r.stdout.strip()
    except: pass
    return None

def get_spotify_track_uri():
    try:
        r = subprocess.run(["playerctl", "-p", "spotify", "metadata", "-f", "{{mpris:trackid}}"],
                           capture_output=True, text=True, timeout=2)
        if r.returncode == 0:
            #print((r.stdout.strip())[19:])
            return (r.stdout.strip())[19:]
    except: pass
    return None

def get_curent_volume():
    try:
        r = subprocess.run(["pamixer", "--get-volume"], capture_output=True, text=True, timeout=2)
        if r.returncode == 0: return r.stdout.strip()
    except: pass
    return None

def do_handshake(ser):
    try:
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        ser.timeout = HANDSHAKE_TIMEOUT

        ser.write(b"SYN\n")
        start = time.time()
        while time.time() - start < HANDSHAKE_TIMEOUT:
            line = ser.readline().decode('latin-1', errors='ignore')
            if not line: continue
            print(line)
            if "SYN_ACK" in line:
                ser.write(b"ACK\n")
                return True

    except (serial.SerialException, OSError) as e: 
        print(e)
        return False

def try_connection():
    try:
        s = serial.Serial(PORT, BAUD, timeout=0.1)
        print("Port is open")
        time.sleep(0.5)
        if do_handshake(s):
            print("Handshake OK")
            return s
        else:
            print("Handshake Failed")
            s.close()
            return None
    except serial.SerialException: return None

# MAIN
if __name__ == "__main__":
    ser = None
    retry_time = 0
    last_ping = 0
    last_pong = 0

    try:
        while True:
            if ser is None or not ser.is_open:
                now = time.time()
                if now - retry_time > RETRY_DELAY:
                    ser = try_connection()
                    if ser:
                        state["last_track"] = ""
                        last_pong = now
                        last_ping = now
                        print("LCD Reconnected")
                    retries = now
                time.sleep(0.5)
                continue

            try:
                while ser.in_waiting > 0:
                    line = ser.readline().decode('latin-1', errors='ignore')
                    if not line: continue
                    last_pong = time.time()
                    if "PONG" in line:
                        pass
                    else:
                        route_cmd(line)
                update_display()

                now = time.time()
                if now - last_ping > PING_INTERVAL:
                    ser.write(b"PING\n")
                    last_ping = now

                if now - last_pong > MAX_MISSED_PONGS * PONG_TIMEOUT:
                    raise serial.SerialException("Keep-alive timeout")
                time.sleep(FRAME_DELAY)
            except (serial.SerialException, OSError) as e:
                print("LCD Disconnected")
                try:
                    ser.close()
                except:
                    pass
                ser = None
                continue
    except KeyboardInterrupt:
        print("\n Disconnecting...")
    finally:
        if ser and ser.is_open:
            try:
                ser.write(b"EXIT\n")
                ser.flush()
            except Exception: pass
            ser.close()
