import os

class SoundLoader:

    CORE = ["neutral", "friend", "foe"]

    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.sounds_dir = os.path.join(self.plugin_dir, "sounds")
        self.default_dir = os.path.join(self.sounds_dir, "default")
        self.sound_map: dict[str, str] = {}
        self.neutral: str | None = None
        self.load_sounds()

    def _newest_match(self, folder, base_name):
        if not os.path.isdir(folder):
            return None

        candidates = []
        for f in os.listdir(folder):
            name, ext = os.path.splitext(f)
            if name.lower() != base_name:
                continue
            if ext.lower() not in (".wav", ".mp3"):
                continue
            full = os.path.join(folder, f)
            if os.path.isfile(full):
                candidates.append(f)

        if not candidates:
            return None

        candidates.sort(
            key=lambda f: os.path.getmtime(os.path.join(folder, f)),
            reverse=True
        )
        return candidates[0]

    def load_sounds(self):
        for core in self.CORE:
            file = self._newest_match(self.sounds_dir, core)
            if file:
                self.sound_map[core] = file
                if core == "neutral":
                    self.neutral = file
            else:
                file = self._newest_match(self.default_dir, core)
                if file:
                    self.sound_map[core] = os.path.join("default", file)
                    if core == "neutral":
                        self.neutral = os.path.join("default", file)  

        if os.path.isdir(self.sounds_dir):
            for f in os.listdir(self.sounds_dir):
                full = os.path.join(self.sounds_dir, f)
                if not os.path.isfile(full):
                    continue
                name, ext = os.path.splitext(f)
                name = name.lower()
                if name in self.sound_map:
                    existing_file = os.path.join(self.sounds_dir, self.sound_map[name])
                    if os.path.getmtime(full) > os.path.getmtime(existing_file):
                        self.sound_map[name] = f
                else:
                    if ext.lower() in (".wav", ".mp3"):
                        self.sound_map[name] = f

        self.sound_map["none"] = "none"
        self.sound_files = list(self.sound_map.keys())
        
    def reload(self):
        self.load_sounds()

sound_inst = SoundLoader()
