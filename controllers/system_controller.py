import subprocess
import os
import re

class SystemController:
    METRICS = [
        ("CPU", "_get_cpu"),
        ("GPU", "_get_gpu"),
        ("RAM", "_get_ram")
    ]

    def __init__(self):
        self.idx = 0

    def next_metric(self):
        self.idx = (self.idx + 1) % len(self.METRICS)

    def prev_metric(self):
        self.idx = (self.idx - 1) % len(self.METRICS)

    def get_current_metric_info(self):
        """Возвращает (name, value_str) для текущей метрики."""
        name, method_name = self.METRICS[self.idx]
        method = getattr(self, method_name)
        return name, method()

    def _get_cpu(self) -> str:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000.0
            r = subprocess.run(["top", "-bn1"], capture_output=True, text=True, timeout=2)
            usage = 0.0
            for line in r.stdout.splitlines():
                if "Cpu(s)" in line or "%Cpu" in line:
                    match = re.search(r'([\d.]+)[%]?\s*id', line)
                    if match:
                        idle = float(match.group(1).replace(',', '.'))
                        usage = 100.0 - idle
                        break
            return f"{temp:.0f} C  {usage:.1f}%"
        except Exception:
            return "N/A"

    def _get_gpu(self) -> str:
        try:
            for path in ["/sys/class/drm/card0/device/hwmon/hwmon0/temp1_input",
                         "/sys/class/thermal/thermal_zone1/temp"]:
                if os.path.exists(path):
                    with open(path) as f:
                        temp = float(f.read().strip()) / 1000.0
                    try:
                        usage = subprocess.check_output(
                            "cat /sys/class/drm/card*/device/gpu_busy_percent 2>/dev/null | head -n1",
                            shell=True, text=True
                        ).strip()
                    except Exception:
                        usage = "?"
                    return f"{temp:.0f} C  {usage}%"
        except Exception:
            pass
        return "N/A"

    def _get_ram(self) -> str:
        try:
            r = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=2)
            lines = r.stdout.splitlines()
            total, used = map(int, lines[1].split()[1:3])
            percent = int((used / total) * 100)
            # попытка получить human-readable available
            r2 = subprocess.run(["free", "-h"], capture_output=True, text=True)
            for line in r2.stdout.splitlines():
                parts = line.split()
                if parts and parts[0] == "Mem:":
                    available = parts[-1].replace("Gi", " Gb")
                    return f"{percent}%, {available}"
            return f"{percent}%"
        except Exception:
            return "N/A"
