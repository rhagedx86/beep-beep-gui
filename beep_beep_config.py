import os
import json
import threading

class BeepBeepConfig:
    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.config_file = "beepbeep_config.json"
        self.lock = threading.Lock()
        self.config = {}
        self.load_config()

    def load_config(self):
        path = os.path.join(self.plugin_dir, self.config_file)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                with self.lock:
                    self.config.update(data)
                    
            except (OSError, json.JSONDecodeError):
                pass

    def save_config(self):
        path = os.path.join(self.plugin_dir, self.config_file)
        try:
            with self.lock:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.config, f, indent=2)
                    
        except (OSError, json.JSONDecodeError):
            pass

    def get_config(self, attr: str, default=None):
        with self.lock:
            return self.config.get(attr, default)

    def set_config(self, attr: str, value):
        with self.lock:
            self.config[attr] = value

config = BeepBeepConfig()
