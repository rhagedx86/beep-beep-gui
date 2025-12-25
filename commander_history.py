import datetime
import json
import os
import re
import threading
from dataclasses import dataclass
from typing import Callable, List, Optional, Dict
from logutil import log
from beep_beep_config import config
import time


@dataclass
class CommanderAndTimestamp:
    commander_id: int
    timestamp: datetime.datetime


class CommanderHistory:
    def __init__(
        self,
        initial_state: Optional[List[CommanderAndTimestamp]] = None,
        name: str = "None"
    ):
        self.name = name
        self.cmdr_history: Dict[int, datetime.datetime] = {}
        self.listeners: List[Callable[[List[CommanderAndTimestamp]], None]] = []
        self.cmdr_history_prev: List[int] = []

        initial_state = initial_state or []
        for entry in initial_state:
            self.cmdr_history[entry.commander_id] = entry.timestamp

        self.most_recent_timestamp = max((e.timestamp for e in initial_state), default=datetime.datetime.min)

    def subscribe_new_listener(self, cb: Callable[[List[CommanderAndTimestamp]], None]):
        self.listeners.append(cb)

    def find_entry(self, commander_id: int) -> Optional[CommanderAndTimestamp]:
        if commander_id in self.cmdr_history:
            return CommanderAndTimestamp(commander_id, self.cmdr_history[commander_id])
        return None

    def emit_events(self):
        data = [CommanderAndTimestamp(cid, self.cmdr_history[cid]) for cid in self.calculate_current_commander_ids()]
        for cb in self.listeners:
            cb(data)

    def calculate_current_commander_ids(self) -> List[int]:
        return [cid for cid, ts in self.cmdr_history.items() if ts >= self.most_recent_timestamp]

    def push_new_state(self, entries: List[CommanderAndTimestamp]):
        needs_emit = [self.update_entry(entry) for entry in entries]
        calculated_state = self.calculate_current_commander_ids()
        is_subset = all(entry in self.cmdr_history_prev for entry in calculated_state)
        self.cmdr_history_prev = calculated_state.copy()
        if any(needs_emit) and not is_subset:
            self.emit_events()

    def update_entry(self, entry: CommanderAndTimestamp) -> bool:
        is_timestamp_newer = entry.timestamp > self.most_recent_timestamp
        if is_timestamp_newer:
            self.most_recent_timestamp = entry.timestamp
        is_entry_new = entry.commander_id not in self.cmdr_history
        self.cmdr_history[entry.commander_id] = entry.timestamp
        return is_timestamp_newer or is_entry_new

    def get_most_recent_timestamp(self) -> datetime.datetime:
        return self.most_recent_timestamp


class CommanderHistoryManager:
    def __init__(self):
        self.commander_history_dir = os.path.join(
            os.getenv("LOCALAPPDATA", ""), "Frontier Developments", "Elite Dangerous", "CommanderHistory"
        )

        self.last_modified_timestamp: datetime.datetime = datetime.datetime.min
        self.aggregated_commanders: Dict[str, Dict] = {}
        self.history: Optional[CommanderHistory] = None
        self.worker_thread: Optional[threading.Thread] = None
        self.worker_stop_event = threading.Event()

        
    @property
    def wing_notify(self):
        return config.get_config("wing_notify", True)
    
    @property
    def poll_interval(self):
        return config.get_config("poll_interval", 5)    
        
    @property
    def wing_cooldown(self):
        return config.get_config("wing_cooldown", 60)        

    @staticmethod
    def is_cmdr_history_file(name: str) -> bool:
        return re.match(r"^Commander\d*\.cmdrHistory$", name) is not None

    @staticmethod
    def check_if_file_is_newer_than_timestamp(filepath: str, timestamp: datetime.datetime) -> bool:
        return datetime.datetime.fromtimestamp(os.path.getmtime(filepath)) > timestamp

    def aggregate_most_recent_commanders(self, first_run=False) -> List[CommanderAndTimestamp]:
        try:
            abs_paths = [
                os.path.join(self.commander_history_dir, f)
                for f in os.listdir(self.commander_history_dir)
                if os.path.isfile(os.path.join(self.commander_history_dir, f)) and self.is_cmdr_history_file(f)
            ]
        except Exception as err:
            log.error("Failed to list directory %s", self.commander_history_dir)
            log.error(err)
            return []

        if not abs_paths:
            return []

        new_files = [f for f in abs_paths if self.check_if_file_is_newer_than_timestamp(f, self.last_modified_timestamp)]
        if first_run and not new_files:
            new_files = [max(abs_paths, key=os.path.getmtime)]

        if not new_files:
            self.last_modified_timestamp = datetime.datetime.now()
            return []

        newest_file = max(new_files, key=os.path.getmtime)

        try:
            with open(newest_file, "r") as f:
                data = json.load(f)
        except Exception as err:
            log.error("Failed to read json file %s. Skipping", newest_file)
            log.error(err)
            return []

        entries = []
        for entry in data.get("Interactions", []):
            interactions = entry.get("Interactions", [])
            if "Met" not in interactions:
                continue
            if not self.wing_notify and "WingMember" in interactions:
                continue
            ts = datetime.datetime.fromtimestamp(
                (datetime.datetime(1601, 1, 1) + datetime.timedelta(seconds=entry["Epoch"])).timestamp()
            )
            entries.append(CommanderAndTimestamp(entry["CommanderID"], ts))

        self.last_modified_timestamp = datetime.datetime.now()

        if not entries:
            return []

        if first_run and self.history is None:
            self.history = CommanderHistory(entries, os.path.basename(newest_file))
            for e in entries:
                self.aggregated_commanders[str(e.commander_id)] = {
                    "name": "unknown",
                    "sound": "neutral.wav",
                    "last_seen": e.timestamp.isoformat(),
                }
            return entries

        most_recent = self.history.get_most_recent_timestamp() if self.history else datetime.datetime.min
        new_entries = [e for e in entries if e.timestamp > most_recent]

        if new_entries and self.history:
            self.history.push_new_state(new_entries)
            for e in new_entries:
                self.aggregated_commanders[str(e.commander_id)] = {
                    "name": "unknown",
                    "sound": "neutral.wav",
                    "last_seen": e.timestamp.isoformat(),
                }
        return new_entries


    def start_worker(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        self.worker_stop_event.clear()

        if self.history:
            self.history.emit_events()

        self.worker_thread = threading.Thread(target=self.worker_loop, daemon=True, name="CommanderHistoryWorker")
        self.worker_thread.start()

    def stop_worker(self):
        self.worker_stop_event.set()
        if self.worker_thread:
            self.worker_thread.join(timeout=5)
            log.info("CommanderHistoryManager worker stopped.")

    def worker_loop(self):
        while not self.worker_stop_event.is_set():
            try:
                time.sleep(self.poll_interval)
                self.aggregate_most_recent_commanders()
            except Exception:
                log.exception("Exception in CommanderHistoryManager worker loop, continuing")
                continue

history_inst = CommanderHistoryManager()
