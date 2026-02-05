import os

class SoundLoader:
    def __init__(self):
        self.plugin_dir = os.path.dirname(__file__)
        self.sounds_dir = os.path.join(self.plugin_dir, "sounds")
        self.sound_files = []
        self.neutral = None
        self.load_sounds()

    def load_sounds(self):
        if not os.path.isdir(self.sounds_dir):
            self.sound_files = []
            self.neutral = None
            return

        all_files = [
            f for f in os.listdir(self.sounds_dir)
            if os.path.isfile(os.path.join(self.sounds_dir, f))
            and f.lower().endswith((".wav", ".mp3"))
        ]

        final_sounds = []

        for core in ["neutral", "friend", "foe"]:
            candidates = [f for f in all_files if f.lower().startswith(core + ".")]
            if candidates:
                candidates.sort(
                    key=lambda f: os.path.getmtime(os.path.join(self.sounds_dir, f)),
                    reverse=True
                )
                newest = candidates[0]
                final_sounds.append(newest)
                if core == "neutral":
                    self.neutral = newest
                all_files = [f for f in all_files if not f.lower().startswith(core + ".")]

        
        final_sounds.extend(all_files)
        final_sounds.append("none")
        self.sound_files = final_sounds
  
sound_inst = SoundLoader()
