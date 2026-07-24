def transliterate(text: str) -> str:
    """Транслитерация кириллицы в латиницу."""
    cyr2lat = {
        'а': '\x61', 'б': '\xB2', 'в': '\xB3', 'г': '\xB4', 'д': '\xE3', 'е': '\x65', 'ё': '\xB5',
        'ж': '\xB6', 'з': '\xB7', 'и': '\xB8', 'й': '\xB9', 'к': '\xBA', 'л': '\xBB', 'м': '\xBC',
        'н': '\xBD', 'о': '\x6F', 'п': '\xBE', 'р': '\x70', 'с': '\x63', 'т': '\xBF', 'у': '\x79',
        'ф': '\xE4', 'х': '\x78', 'ц': '\xE5', 'ч': '\xC0', 'ш': '\xC1', 'щ': '\xE6',
        'ъ': '\xC2', 'ы': '\xC3', 'ь': '\xC4', 'э': '\xC5', 'ю': '\xC6', 'я': '\xC7',
        'А': '\x41', 'Б': '\xA0', 'В': '\x42', 'Г': '\xA1', 'Д': '\xE0', 'Е': '\x45', 'Ё': '\xA2',
        'Ж': '\xA3', 'З': '\xA4', 'И': '\xA5', 'Й': '\xA6', 'К': '\x4B', 'Л': '\xA7', 'М': '\x4D',
        'Н': '\x48', 'О': '\x4F', 'П': '\xA8', 'Р': '\x50', 'С': '\x43', 'Т': '\x54', 'У': '\xA9',
        'Ф': '\xAA', 'Х': '\x58', 'Ц': '\xE1', 'Ч': '\xAB', 'Ш': '\xAC', 'Щ': '\xE2',
        'Ъ': '\xAD', 'Ы': '\xAE', 'Ь': '\x08', 'Э': '\xAF', 'Ю': '\xB0', 'Я': '\xB1'
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
