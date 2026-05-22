class AppState:
    def __init__(self):
        self.mode = "PLAYER"       # "PLAYER" or "SERVICE"
        self.svc_idx = 0           # индекс текущей метрики
        self.last_track = ""
        self.scroll_offset = 0
        self.current_track_uri = ""
        self.volume_change = False
        self.liked = ""            # "", "like", "unlike"
        self.has_like = False

    def toggle_mode(self):
        if self.mode == "PLAYER":
            self.mode = "SERVICE"
        else:
            self.mode = "PLAYER"
        self.svc_idx = 0
        self.scroll_offset = 0
        self.last_track = ""

    def toggle_volume_change(self):
        self.volume_change = not self.volume_change

    def reset_like_status(self):
        self.liked = ""
        self.has_like = False
