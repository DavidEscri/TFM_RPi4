__author__ = "Jose David Escribano Orts"
__subsystem__ = ""
__module__ = "TFMApp.py"
__version__ = "0.1"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import logging
import os
import sys
import LoadEnv
from tfm_muaii_rpi4.Main.startUpMgr import startUpMgrSingleton


def main():
    app = None
    try:
        logging.info("----INICIO DE SISTEMA----")
        logging.info("ENTORNO %s", os.getenv("APP_ENVIRONMENT"))
        logging.info("SETTING %s", os.getenv("APP_SETTINGS_PATH"))
        app = TFMApp()
        app.start()

    except Exception as e:
        logging.critical("Fatal exception raised: %s", e, exc_info=True)
        if not (app is None):
            app.stop()
        sys.exit()


class TFMApp:
    def __init__(self):
        self.start_up = startUpMgrSingleton()

    def start(self):
        self.start_up.start()

    def stop(self):
        self.start_up.stop()


if __name__ == '__main__':
    main()
