# logutil.py
import logging
import os
import inspect
from config import appname # noqa

class Log:
    instance = None

    def __new__(cls, debug=False):
        if cls.instance is None:
            cls.instance = super().__new__(cls)
            cls.instance._init_logger(debug)
        return cls.instance

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
