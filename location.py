import time
from logutil import log

class Location:
    def __init__(self):
        self.state = None
        self.prev_state = None
        self.system = None
        self.prev_system = None
        self.instance = {}
        self.wing = False
        self.jump_ts = None
        self.wing_join = None
        self.jump_backup = {}


    def set_wing(self, in_wing: bool):
        self.wing = in_wing

    def set(self, state, system):
        if state == -1 and system != self.system:
            self.instance = {}
            
        self.prev_system = self.system
        self.prev_state = self.state
        self.state = state
        self.system = system

    def get(self):
        return self.state, self.system

    def get_instance(self):
        return self.instance
    
    def add_instance(self, id_, state=None, system=None):
        if state is None:
            state = -1
        if system is None:
            system = "Unknown"
    
        here = (system == self.system and state == self.state)
    
        self.instance[id_] = {
            "state": state,
            "system": system,
            "here": here
        }
         
    def jump(self):
        if self.prev_system != self.system:
            self.jump_ts = time.time()
            self.jump_backup = self.instance.copy()
            self.instance.clear()
            
        else:
            self.jump_ts = None
            self.jump_backup = {}
            
    def wing_changed(self): 
        self.wing_join = time.time()
        
location = Location()
