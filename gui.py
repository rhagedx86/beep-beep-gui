import tkinter as tk
from tkinter import ttk
import json
import os
import myNotebook as nb # noqa
from logutil import log
from datetime import datetime, timezone
from beep_beep_config import config
from commander_history import history_inst
import tkinter.font as tkFont




class SeenCommandersGUI:
    def __init__(self):
        self.initialized = False
        self.plugin_dir = None
        self.json_file_path = None
        self.sounds_dir = None
        self.seen_data = {}
        self.tree_items = {} 
        self.tree = None 
        self.name_vars = {}
        self.last_seen_vars = {}
        self.widgets = {}
        self.sound_vars = {}
        self.window = None
        self.parent = None
        self.row_offset = 0
        self.sound_files = []
        self.sort_field = "last_seen"
        self.sort_asc = False       
        self.refresh_interval = 5000        
        self.beep_inst = None
        self.ui_cache = {
            "name": {},
            "sound": {},
            "last_seen": {},
        }        
        
        
   

    def init_gui(self, plugin_dir, beep_inst):
        if self.initialized:
            raise RuntimeError("SeenCommandersGUI already initialized")

        self.plugin_dir = plugin_dir
        self.json_file_path = os.path.join(plugin_dir, "seen_commanders.json")
        self.sounds_dir = os.path.join(plugin_dir, "sounds")

        self.sound_files = self.get_sound_files()
        self.load_seen_commanders()

        self.beep_inst = beep_inst

        self.initialized = True
        log.info("SeenCommandersGUI initialized with plugin_dir: %s", plugin_dir)



    def get_sound_files(self):
        if not os.path.isdir(self.sounds_dir):
            return []
    
        files = sorted(
            f for f in os.listdir(self.sounds_dir)
            if os.path.isfile(os.path.join(self.sounds_dir, f))
            and f.lower().endswith((".wav", ".mp3"))
        )
    
        if "none.wav" not in files:
            files.append("none.wav")
    
        return files
    
    
    def load_seen_commanders(self):
        if not os.path.isfile(self.json_file_path) or os.path.getsize(self.json_file_path) == 0:
            self.seen_data = {}
            log.info("No seen_commanders.json found or file is empty, starting empty")
            return
        try:
            with open(self.json_file_path, "r") as f:
                self.seen_data = json.load(f)
        except Exception:
            log.exception("Failed to load seen_commanders.json, starting empty")
            self.seen_data = {}

    def format_time_ago(self, ts_iso: str) -> str:
        try:
            ts = datetime.fromisoformat(ts_iso)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = now - ts

            seconds = int(delta.total_seconds())
            minutes, sec = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            days, hours = divmod(hours, 24)

            if days > 0:
                return f"{days} d {hours} h ago"
            elif hours > 0:
                return f"{hours} h {minutes} min ago"
            elif minutes > 0:
                return f"{minutes} min {sec} s ago"
            else:
                return f"{seconds} s ago"
        except Exception:
            return ts_iso


    

    def build_plugin_button(self, parent):
        container = tk.Frame(parent)
        container.pack(padx=5, pady=5)
    
        btn_show = tk.Button(
            container,
            text="Beep Beep",
            command=lambda: self.open(parent)
        )
        btn_show.pack(side="left")
    
        def update_mute_button(muted):
            mute_btn.config(
                text="🔇" if muted else "🔊",
                bg="lightgrey" if muted else "SystemButtonFace",
                fg="black",
                relief="sunken" if muted else "raised"
            )
    
        def toggle_mute():
            new_value = not config.get_config("mute", False)
            config.set_config("mute", new_value)
            config.save_config()
            update_mute_button(new_value)
    
        muted = config.get_config("mute", False)
    
        mute_btn = tk.Button(
            container,
            width=2,
            command=toggle_mute
        )
        mute_btn.pack(side="left", padx=(4, 0))
        update_mute_button(muted)
    
        return container


    def open(self, parent):
        self.parent = parent
    
        x = config.get_config("seen_window_x", 50)
        y = config.get_config("seen_window_y", 50)
        width = config.get_config("seen_window_width", 800)
        height = config.get_config("seen_window_height", 400)
    
        width = max(100, width)
        height = max(100, height)
    
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.build_ui(self.window)
            return
    
        self.window = tk.Toplevel(parent)
        self.window.title("Seen Commanders")
    
        self.window.geometry(f"{width}x{height}+{x}+{y}")
        self.window.minsize(100, 100)  
    
        self.window.grid_rowconfigure(1, weight=1)
        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_columnconfigure(2, weight=1)
    
        self.build_ui(self.window)
        self.make_tree_editable()
        self.start_auto_refresh()
        self.attach_resize_listener()
        
        
        def enforce_column_limits(event):
            total_width = self.tree.winfo_width()

            limits = {
                "name": (int(0.2 * total_width), int(0.5 * total_width)),
                "sound": (int(0.15 * total_width), int(0.4 * total_width)),
                "last_seen": (int(0.1 * total_width), int(0.3 * total_width))
            }
            
            for col, (min_w, max_w) in limits.items():
                width = self.tree.column(col, "width")
                if width < min_w:
                    self.tree.column(col, width=min_w)
                elif width > max_w:
                    self.tree.column(col, width=max_w)
        
        self.tree.bind("<ButtonRelease-1>", enforce_column_limits)         
        enforce_column_limits(None)
        
    
    def attach_resize_listener(self):
        if not self.window or not self.window.winfo_exists():
            return
    
        self.resize_after_id = None 
    
        def on_resize(event):
            if self.resize_after_id is not None:
                self.window.after_cancel(self.resize_after_id)
    
            self.resize_after_id = self.window.after(300, save_window_geometry)
    
        def save_window_geometry():
            width = max(100, self.window.winfo_width())
            height = max(100, self.window.winfo_height())
            x = self.window.winfo_x()
            y = self.window.winfo_y()
    
            config.set_config("seen_window_x", x)
            config.set_config("seen_window_y", y)
            config.set_config("seen_window_width", width)
            config.set_config("seen_window_height", height)
            config.save_config()
    
            self.resize_after_id = None
    
        self.window.bind("<Configure>", on_resize)

    def make_tree_editable(self):
        self.tree.bind("<Double-1>", self.on_tree_double_click_popup)
        self.tree.bind("<Return>", self.on_tree_enter_pressed)
        

    def on_tree_enter_pressed(self, event):
        selection = self.tree.selection()
        if not selection:
            return
    
        row_id = selection[0]
        cmdr_id = next((k for k, v in self.tree_items.items() if v == row_id), None)
        if not cmdr_id:
            return
    
        bbox = self.tree.bbox(row_id)
        if bbox:
            x, y, width, height = bbox
            x_root = self.tree.winfo_rootx() + x + width // 2
            y_root = self.tree.winfo_rooty() + y + height // 2
        else:
            x_root = self.tree.winfo_rootx() + 50
            y_root = self.tree.winfo_rooty() + 50
    
        class FakeEvent:
            pass
    
        e = FakeEvent()
        e.y = y + height // 2
        e.x_root = x_root
        e.y_root = y_root
    
        self.on_tree_double_click_popup(e)        
    
    def on_tree_double_click_popup(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
    
        cmdr_id = next((k for k, v in self.tree_items.items() if v == row_id), None)
        if not cmdr_id:
            return
    
        info = self.seen_data[cmdr_id]
    
        popup = tk.Toplevel(self.window)
        popup.title(f"Edit Commander {info.get('name', 'unknown')}")
        popup.geometry(f"+{event.x_root}+{event.y_root}")
        popup.grab_set()
    
        tk.Label(popup, text="Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        name_var = tk.StringVar(value=info.get("name", "unknown"))
        name_entry = tk.Entry(popup, textvariable=name_var)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        name_entry.focus_set()
        name_entry.selection_range(0, tk.END)
        name_entry.icursor(0)
    
        tk.Label(popup, text="Sound:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        sound_var = tk.StringVar(value=info.get("sound", "neutral.wav"))
        combo = ttk.Combobox(popup, textvariable=sound_var, values=self.sound_files, state="readonly")
        combo.grid(row=1, column=1, padx=5, pady=5)
    
        def save_popup_changes():
            new_name = name_var.get()
            new_sound = sound_var.get()
    
            self.name_vars[cmdr_id].set(new_name)
            self.sound_vars[cmdr_id].set(new_sound)
    
            self.seen_data[cmdr_id]["name"] = new_name
            self.seen_data[cmdr_id]["sound"] = new_sound
    
            self.tree.set(row_id, "name", new_name)
            self.tree.set(row_id, "sound", new_sound)
    
            self.save_changes()  # always save
    
            sort_field = config.get_config("sort_field", "last_seen")
            sort_asc = config.get_config("sort_asc", False)
            self.sort_rows(sort_field, sort_asc)
    
            popup.destroy()
    
        tk.Button(popup, text="Save", command=save_popup_changes).grid(row=2, column=0, columnspan=2, pady=10)
    
        # Bind Enter in Name entry → move to combo
        def on_name_enter(event):
            combo.focus_set()
            combo.event_generate('<Down>')  # open the dropdown
            return "break"  # prevent default
    
        name_entry.bind("<Return>", on_name_enter)
    
        # Bind Enter in combo → save popup
        def on_combo_enter(event):
            save_popup_changes()
            return "break"
    
        combo.bind("<Return>", on_combo_enter)
       


    def build_ui(self, parent):
        sort_field = config.get_config("sort_field", "last_seen")
        sort_asc = config.get_config("sort_asc", False)
    
        if not hasattr(self, "tree") or not self.tree or not self.tree.winfo_exists() or self.tree.master != parent:
            for attr in ["scrollbar", "tree"]:
                if hasattr(self, attr) and getattr(self, attr) and getattr(self, attr).winfo_exists():
                    getattr(self, attr).destroy()
                    
            style = ttk.Style(parent)
            default_font = tkFont.nametofont("TkDefaultFont")
            row_height = default_font.metrics("linespace") + 4
            style.configure("Treeview", rowheight=row_height)
                    
    
            self.tree = ttk.Treeview(parent, columns=("name", "sound", "last_seen"), show="headings")
            self.tree.grid(row=1, column=0, columnspan=3, sticky="nsew")
            
            self.tree.heading("name", text="Name", anchor="w", command=lambda: self.on_header_click("name"))
            self.tree.heading("sound", text="Sound", anchor="w", command=lambda: self.on_header_click("sound"))
            self.tree.heading("last_seen", text="Last Seen", anchor="w", command=lambda: self.on_header_click("last_seen"))
            
            self.tree.column("name", anchor="w")
            self.tree.column("sound", anchor="w")
            self.tree.column("last_seen", anchor="w")
            
            self.scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
            self.tree.configure(yscroll=self.scrollbar.set)
            self.scrollbar.grid(row=1, column=3, sticky="ns")
    
            parent.grid_rowconfigure(1, weight=1)
            for col in range(3):
                parent.grid_columnconfigure(col, weight=1)
    
            self.widgets.clear()
            self.sound_vars.clear()
            self.name_vars.clear()
            self.last_seen_vars.clear()
            self.tree_items = {}
    
        for cmdr_id in self.seen_data:
            if cmdr_id not in getattr(self, "tree_items", {}):
                self.add_row(cmdr_id)
    
        self.sort_rows(sort_field, sort_asc)
        
        self.options_button = ttk.Button(
            parent,
            text="Options",
            command=self.open_options_popup
        )
        self.options_button.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(5, 5))
        
        parent.grid_rowconfigure(2, weight=0)        
       
    
    def open_options_popup(self):
        popup = tk.Toplevel(self.window)
        popup.title("Options")
        popup.transient(self.window)
        popup.grab_set()
    
        popup.geometry(
            f"+{self.window.winfo_rootx() + 50}+{self.window.winfo_rooty() + 50}"
        )
    
        options_frame = self.options_menu(popup)
    
        options_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
    
        popup.grid_rowconfigure(0, weight=1)
        popup.grid_columnconfigure(0, weight=1)
    
    
    def on_header_click(self, field):
        if getattr(self, "sort_field", None) == field:
            self.sort_asc = not self.sort_asc
        else:
            self.sort_field = field
            self.sort_asc = True if field != "last_seen" else False
    
        config.set_config("sort_field", self.sort_field)
        config.set_config("sort_asc", self.sort_asc)
        config.save_config()
    
        self.sort_rows(self.sort_field, self.sort_asc)
    
    
    def add_row(self, cmdr_id):
        info = self.seen_data[cmdr_id]
    
        if cmdr_id not in self.name_vars:
            self.name_vars[cmdr_id] = tk.StringVar(value=info.get("name", "unknown"))
        if cmdr_id not in self.sound_vars:
            sound = info.get("sound", "neutral.wav")
            if sound not in self.sound_files:
                sound = "neutral.wav" if "neutral.wav" in self.sound_files else (self.sound_files[0] if self.sound_files else "")
            self.sound_vars[cmdr_id] = tk.StringVar(value=sound)
        if cmdr_id not in self.last_seen_vars:
            self.last_seen_vars[cmdr_id] = tk.StringVar(value=self.format_time_ago(info.get("last_seen")))
    
        item = self.tree.insert("", "end", values=(
            self.name_vars[cmdr_id].get(),
            self.sound_vars[cmdr_id].get(),
            self.last_seen_vars[cmdr_id].get()
        ))
    
        if not hasattr(self, "tree_items"):
            self.tree_items = {}
        self.tree_items[cmdr_id] = item
 
        if not hasattr(self, "widgets"):
            self.widgets = {}
        self.widgets[cmdr_id] = {}
   

    def sort_rows(self, sort_field, sort_asc):
        def sort_key(cmdr_id):
            if sort_field == "name":
                return self.name_vars[cmdr_id].get().lower()
            elif sort_field == "sound":
                return self.sound_vars[cmdr_id].get().lower()
            elif sort_field == "last_seen":
                try:
                    ts = datetime.fromisoformat(self.seen_data[cmdr_id].get("last_seen", ""))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    return ts
                except Exception:
                    return datetime(1, 1, 1, tzinfo=timezone.utc)
            return cmdr_id
    
        sorted_ids = sorted(self.seen_data.keys(), key=sort_key, reverse=not sort_asc)
    
        for cmdr_id in sorted_ids:
            self.tree.move(self.tree_items[cmdr_id], "", "end")



    def add_or_update_commander(self, cmdr_id, info: dict, batch: bool = False):
        cmdr_id_str = str(cmdr_id)
        is_new = cmdr_id_str not in self.seen_data
    
        self.seen_data[cmdr_id_str] = info.copy()
    
        self.name_vars.setdefault(cmdr_id_str, tk.StringVar()).set(info.get("name", "unknown"))
        self.sound_vars.setdefault(cmdr_id_str, tk.StringVar()).set(info.get("sound", "neutral.wav"))
        self.last_seen_vars.setdefault(cmdr_id_str, tk.StringVar()).set(self.format_time_ago(info["last_seen"]))
    
        if is_new and self.window and self.window.winfo_exists():
            self.add_row(cmdr_id_str)
    
        if not batch and self.window and self.window.winfo_exists():
            self.refresh_gui()
    

    def save_changes(self):
        try:
            with open(self.json_file_path, "w") as f:
                json.dump(self.seen_data, f, indent=2)
        except Exception:
            log.exception("Failed to save JSON file: %s", self.json_file_path)


    
    def refresh_gui(self):
        if not getattr(self, "tree", None) or not self.tree.winfo_exists():
            return
    
        for cmdr_id, data in self.seen_data.items():
            item_id = self.tree_items.get(cmdr_id)
            new_time = self.format_time_ago(data["last_seen"])
    
            if item_id:
                self.tree.set(item_id, "last_seen", new_time)
            else:
                self.add_row(cmdr_id) 
    
        sort_field = config.get_config("sort_field", "last_seen")
        sort_asc = config.get_config("sort_asc", False)
        
        self.sort_rows(sort_field, sort_asc)
        self.save_changes()

        
    def start_auto_refresh(self):
        def refresh():
            self.refresh_gui()
            if self.window and self.window.winfo_exists():
                self.window.after(self.refresh_interval, refresh)
        refresh()
        

    def add_aggregated(self, new_data: dict):
        added = 0
        for cmdr_id, info in new_data.items():
            cmdr_id_str = str(cmdr_id)
    
            existing = self.seen_data.get(cmdr_id_str, {})
    
            self.seen_data[cmdr_id_str] = {
                "name": existing.get("name", "unknown"),
                "sound": existing.get("sound", "neutral.wav"),
                "last_seen": info["last_seen"],
            }
    
            if cmdr_id_str not in self.tree_items:
                added += 1
    
        if added:
            log.info(f"Added {added} new commanders from aggregation")
            self.save_changes()
            self.refresh_gui()


    def add_slider(self, frame, row, label, var, *, attr=None, from_=0, to=100):
        """Add a slider that automatically updates target.attr and saves to config."""
        tk.Label(frame, text=label).grid(row=row, column=0, padx=5, pady=5, sticky="w")
        slider = tk.Scale(frame, from_=from_, to=to, orient="horizontal", variable=var)
        slider.grid(row=row, column=1, padx=5, pady=5, sticky="ew")
    
        def on_change(*_):
            config.set_config(attr, var.get())
    
        def on_save(event=None):
            config.save_config()

        var.trace_add("write", on_change)
        slider.bind("<ButtonRelease-1>", on_save)
        return row + 1
    
    
    def add_checkbox(self, frame, row, text, var, *, target=None, attr=None):
        def on_toggle():
            v = var.get()
            if target and attr:
                setattr(target, attr, v)
            if attr:
                config.set_config(attr, v)
                config.save_config()
    
        chk = tk.Checkbutton(frame, text=text, variable=var, command=on_toggle)
        chk.grid(row=row, column=1, padx=5, pady=5, sticky="w")
        return row + 1
    
    
    def options_menu(self, parent):
        frame = nb.Frame(parent)
        frame.columnconfigure(1, weight=1)
        row = 0
    
        row = self.add_slider(frame, row, "Alert Volume (%)", tk.IntVar(value=config.get_config("volume", 100)), from_=0, to=100, attr="volume")
        tk.Button(frame, text="▶", command=lambda: self.beep_inst.play_sound("neutral.wav")).grid(row=row - 1, column=2, padx=5)
    
        row = self.add_slider(frame, row, "Sound Cooldown (sec)", tk.IntVar(value=config.get_config("cooldown", 15)), from_=1, to=15, attr="cooldown")
        row = self.add_slider(frame, row, "Check for Updates (sec)", tk.IntVar(value=config.get_config("poll_interval", 15)), from_=1, to=15,attr="poll_interval")
        row = self.add_slider(frame, row, "Wing Alert Cooldown (min)", tk.IntVar(value=config.get_config("wing_cooldown",60)), from_=1, to=1440, attr="wing_cooldown")
        row = self.add_checkbox(frame, row, "Notify on WingMember encounters", tk.BooleanVar(value=config.get_config("wing_notify", False)), attr="wing_notify")
    
        info_text = ("To add sounds, place them in the 'sounds' folder inside the plugin.\n"
                     "Only WAV and MP3 files are supported.\n"
                     "The default files 'foe.wav', 'friend.wav', and 'neutral.wav' must remain.\n"
                     "But can be replaced as long as file type and name are the same."
                     "Restart EDMC to load newly added sounds.\n\n"
                     "To edit a entry Double click, or select a row an hit enter.")
        tk.Message(frame, text=info_text, width=350).grid(row=row, column=0, columnspan=2, padx=5, pady=(10, 0))
    
        return frame





gui_inst = SeenCommandersGUI()
