import datetime
import math
import os
import ctypes
from logutil import log
from beep_beep_config import config
from commander_history import history_inst
from sound_loader import sound_inst

class BeepBeep:
    def __init__(self):
        self.last_beep = datetime.datetime.min
        self.plugin_dir = os.path.dirname(__file__)

    @property
    def volume(self) -> float:
        return config.get_config("volume", 100)

    @property
    def mute(self) -> bool:
        return config.get_config("mute", False)

    
    def play_sound(self, filename: str):
        if self.mute:
            return

        dll_path = os.path.join(self.plugin_dir, "PlayAudioDS.dll")
        sound_path = os.path.join(self.plugin_dir, "sounds", filename)

        if not os.path.isfile(dll_path):
            log.info("Can not find PlayAudioDS.dll in %s", dll_path)
            return
        
        if not os.path.isfile(sound_path):
            log.info("Can not find sound in %s", sound_path)
            return
        

        linear = self.volume / 100.0
        vol = math.log10(1 + 9 * linear)

        try:
            dll = ctypes.CDLL(dll_path)
            dll.PlayAudioDS.argtypes = [ctypes.c_char_p, ctypes.c_float]
            dll.PlayAudioDS.restype = ctypes.c_int
            path_bytes = sound_path.encode("utf-8")
            dll.PlayAudioDS(path_bytes, vol)

        except (OSError, AttributeError, TypeError) as e:
            log.error("Failed to play sound %s: %s", sound_path, e)
    
    def handle_event(self, info: dict | list[dict]):
        if not isinstance(info, list):
            info = [info]
    
        now = datetime.datetime.utcnow()
        possible_sounds: list[str] = []
    
        for entry in info:
            cmdr_id = entry["commander_id"]
            existing = history_inst.seen_data.get(cmdr_id, {})
    
            selected = existing.get("sound", sound_inst.neutral)
            if selected in ("none.wav", "none"):
                continue
    
            possible_sounds.append(selected)
            history_inst.seen_data[cmdr_id] = existing
    
        if possible_sounds:
            sound_to_play = next((s for s in possible_sounds if s != sound_inst.neutral), possible_sounds[0])
            self.last_beep = now
            self.play_sound(sound_to_play)
            history_inst.save_seen_commanders()
       
       
beep_inst = BeepBeep()
