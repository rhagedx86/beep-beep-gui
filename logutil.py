# logutil.py
import logging
import os
import inspect
from config import appname # noqa


class Log:
    def __init__(self, debug=False):
        self.beep_logger = None
        self._init_logger(debug)

    def _init_logger(self, debug):
        frame = inspect.stack()[2]
        caller_file = frame.filename
        plugin_name = os.path.basename(os.path.dirname(caller_file))

        logger = logging.getLogger(f"{appname}.{plugin_name}")

        if not logger.hasHandlers():
            level = logging.DEBUG if debug else logging.INFO
            logger.setLevel(level)

            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - '
                '%(module)s:%(lineno)d:%(funcName)s: %(message)s'
            )
            formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
            formatter.default_msec_format = '%s.%03d'
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        self.beep_logger = logger

    def __getattr__(self, name):
        return getattr(self.beep_logger, name)

log = Log(debug=False)
