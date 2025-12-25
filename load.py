import os
import tkinter as tk
from typing import Optional

from commander_history import history_inst
from beep_beep import beep_inst

from gui import gui_inst
from logutil import log
import myNotebook as nb  # noqa



def plugin_start3(plugin_dir):
    log.info("beep_beep plugin starting (%s)", plugin_dir)

    gui_inst.init_gui(plugin_dir, beep_inst)

    history_inst.aggregate_most_recent_commanders(first_run=True)

    aggregated = history_inst.aggregated_commanders
    
    log.info(aggregated)
    
    gui_inst.add_aggregated(aggregated)

    beep_inst.init_beepbeep(
        plugin_dir=plugin_dir,
        history_state_handles=[history_inst.history] if history_inst.history else []
    )

    history_inst.start_worker()
    beep_inst.ready = True
    

    return "Beep Beep"


def plugin_app(parent):
    gui_inst.build_plugin_button(parent)
    return parent


def plugin_prefs(parent: "nb.Notebook", cmdr: str, is_beta: bool) -> Optional["nb.Frame"]:
    return gui_inst.options_menu(parent)


def plugin_stop():
    history_inst.stop_worker()
    log.info("beep_beep plugin stopped")
