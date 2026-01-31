import datetime
import math
import os
import ctypes
import threading
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
    
    @property
    def sounds(self) -> int:
        return config.get_config("sounds", 1)

    def play_sound(self, filename: str):
        if self.mute:
            return

        dll_path = os.path.join(self.plugin_dir, "BeepBeepPlay.dll")
        sound_path = os.path.join(self.plugin_dir, "sounds", filename)

        if not os.path.isfile(dll_path):
            log.info("Can not find BeepBeepPlay.dll in %s", dll_path)
            return
        
        if not os.path.isfile(sound_path):
            log.info("Can not find sound in %s", sound_path)
            return
        
        vol = self.volume / 100.0
        

        try:
            dll = ctypes.CDLL(dll_path)
            dll.BeepBeepPlay.argtypes = [ctypes.c_char_p, ctypes.c_float]
            dll.BeepBeepPlay.restype = ctypes.c_int
            path_bytes = sound_path.encode("utf-8")
            dll.BeepBeepPlay(path_bytes, vol)

        except (OSError, AttributeError, TypeError) as e:
            log.error("Failed to play sound %s: %s", sound_path, e)
    
    
    
    #
    #
    #
    # def handle_event(self, info: dict | list[dict]):
    #     if not isinstance(info, list):
    #         info = [info]
    #
    #     now = datetime.datetime.utcnow()
    #     possible_sounds: list[str] = []
    #
    #
    #     for entry in info:
    #         cmdr_id = entry["commander_id"]
    #         existing = history_inst.seen_data.get(cmdr_id, {})
    #
    #         selected = existing.get("sound", sound_inst.neutral)
    #         if selected in ("none.wav", "none"):
    #             continue
    #
    #         possible_sounds.append(selected)
    #         history_inst.seen_data[cmdr_id] = existing
    #
    #     if possible_sounds:
    #         sound_to_play = next((s for s in possible_sounds if s != sound_inst.neutral), possible_sounds[0])
    #         self.last_beep = now
    #         self.play_sound(sound_to_play)
    #         history_inst.save_seen_commanders()
    
        
    def handle_event(self, info: dict | list[dict]):
        if not isinstance(info, list):
            info = [info]
    
        if not self.sounds:
            return
    
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
            self.last_beep = now
            history_inst.save_seen_commanders()
            self._schedule_sounds(possible_sounds)
        
    def _schedule_sounds(self, sounds: list[str]):
        max_sounds = self.sounds
        for i, sound_file in enumerate(sounds[:max_sounds]):
            threading.Timer(
                i * 0.2,
                lambda s=sound_file: self.play_sound(s)
            ).start()
           
beep_inst = BeepBeep()
