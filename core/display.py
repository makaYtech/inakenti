def transliterate(text: str) -> str:
    """Транслитерация кириллицы в латиницу."""
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

def marquee(text: str, offset: int, width: int) -> tuple[str, int]:
    """Бегущая строка. Возвращает (строка, новый offset)."""
    if len(text) <= width:
        return text.center(width), offset
    padded = text + " " * (width - 8)
    start = offset % len(padded)
    return (padded * 2)[start:start + width], offset + 1

def build_player_display(state, player) -> str:
    """Сформировать строку для LCD в режиме PLAYER."""
    track_meta = player.get_metadata()
    track = transliterate(track_meta) if track_meta else ""
    status = player.get_status()
    volume = player.get_volume()

    icon = " "
    if status == "Playing":
        icon = " \x84"  # символ Play
    elif status == "Paused":
        icon = " \x82"  # символ Pause

    vol_str = f"{volume}%" if volume != "--" else "--%"

    frame, new_offset = marquee(track, state.scroll_offset, 16)
    state.scroll_offset = new_offset  # обновим offset в состоянии (имеет побочный эффект)

    l0 = frame.ljust(16)
    
    if state.volume_change:
        l1 = f"{icon}  \x93 CVol: {vol_str}".ljust(16)
    else:
        l1 = f"{icon}  \x93  Vol: {vol_str}".ljust(16)

    # Замена иконки громкости на другую, если трек лайкнут
    if state.has_like:
        l1 = l1.replace('\x93', '\x92', 1)

    return f"{l0}|{l1}\n"

def build_system_display(system) -> str:
    """Сформировать строку для LCD в режиме SERVICE."""
    name, val = system.get_current_metric_info()
    l0 = f"[SYS] {name}".ljust(16)
    l1 = val.ljust(16)
    return f"{l0}|{l1}\n"

def build_like_notification(liked: bool) -> str:
    """Всплывающее уведомление о лайке."""
    if liked:
        return "LIKED".ljust(16) + "\n"
    else:
        return "UNLIKED".ljust(16) + "\n"
