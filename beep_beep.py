import os
import datetime
from logutil import log
from typing import List, Optional
from commander_history import CommanderHistory, CommanderAndTimestamp
from gui import gui_inst
from beep_beep_config import config
import math
import ctypes
from pickle import FALSE


class BeepBeep:
    def __init__(self):
        self.initialized = False
        self.ready = False

    @property
    def volume(self):
        return config.get_config("volume", 100)


    @property
    def cooldown(self):
        return config.get_config("cooldown", False)


    @property
    def mute(self):
        return config.get_config("mute", False)



    def init_beepbeep(
        self,
        plugin_dir: str,
        history_state_handles: List[CommanderHistory]
    ):
        

        self.plugin_dir = plugin_dir
        self.last_beep = datetime.datetime.now()

        for entry in history_state_handles:
            entry.subscribe_new_listener(
                lambda data, name=entry.name: self.handle_event(data)
            )

        self.initialized = True



    def play_sound(self, filename: str):
        if not self.initialized:
            return
        if self.mute == True:
            return
        
        
        dll_path = os.path.join(self.plugin_dir, "PlayAudioDS.dll")
        sound_path = os.path.join(self.plugin_dir, "sounds", filename)

        if not os.path.isfile(dll_path):
            log.error("PlayAudioDS.dll not found: %s", dll_path)
            return

        if not os.path.isfile(sound_path):
            log.warning("Sound file not found: %s", sound_path)
            return

        linear = self.volume / 100.0
        vol = math.log10(1 + 9 * linear) 

        try:
            dll = ctypes.CDLL(dll_path)
            dll.PlayAudioDS.argtypes = [ctypes.c_char_p, ctypes.c_float]
            dll.PlayAudioDS.restype = ctypes.c_int

            path_bytes = sound_path.encode("utf-8")

            result = dll.PlayAudioDS(path_bytes, vol)

            if result != 0:
                log.error("PlayAudioDS failed with code %d", result)

        except Exception as e:
            log.error("Failed to play sound %s: %s", sound_path, e)



    def handle_event(self, data: List[CommanderAndTimestamp]):
        if not self.initialized:
            return
    
        now = datetime.datetime.now()
        delta = (now - self.last_beep).total_seconds()
    
        sound_to_play: Optional[str] = None
        fallback_neutral: Optional[str] = None
    
    
        for entry in data:
            cmdr_id = str(entry.commander_id)
            existing = gui_inst.seen_data.get(cmdr_id, {})
            ts = entry.timestamp.replace(microsecond=0)
    
            info = {
                "name": existing.get("name", "unknown"),
                "sound": existing.get("sound", "neutral.wav"),
                "last_seen": ts.isoformat(),
            }
    
            gui_inst.add_or_update_commander(cmdr_id, info, batch=True)
    
            sound_var = gui_inst.sound_vars.get(cmdr_id)
            selected = sound_var.get().lower() if sound_var else "neutral.wav"
    
            if selected == "none.wav":
                continue
            elif selected == "neutral.wav":
                if fallback_neutral is None:
                    fallback_neutral = selected
            elif sound_to_play is None:
                sound_to_play = selected
    
    
    
        if delta > self.cooldown and self.ready:
            if sound_to_play is None and fallback_neutral:
                sound_to_play = fallback_neutral
    
            log.info(f"Playing ??? {data}")
            if sound_to_play:
                self.last_beep = now
                self.play_sound(sound_to_play)



beep_inst = BeepBeep()
