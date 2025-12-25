import os
import json
import threading

PLUGIN_CONFIG_FILE = "beepbeep_config.json"

class BeepBeepConfig:
    def __init__(self, plugin_dir: str):
        self.plugin_dir = plugin_dir
        self.lock = threading.Lock()
        self.config = {}

    def load_config(self):
        path = os.path.join(self.plugin_dir, PLUGIN_CONFIG_FILE)
        if os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                with self.lock:
                    self.config.update(data)
            except Exception:
                return False

    def save_config(self):
        path = os.path.join(self.plugin_dir, PLUGIN_CONFIG_FILE)
        try:
            with self.lock:
                with open(path, "w") as f:
                    json.dump(self.config, f, indent=2)
            return True
        except Exception:
            return False

    def get_config(self, attr: str, default=None):
        with self.lock:
            return self.config.get(attr, default)

    def set_config(self, attr: str, value):
        with self.lock:
            self.config[attr] = value


plugin_dir = os.path.dirname(__file__)
config = BeepBeepConfig(plugin_dir)
config.load_config()
