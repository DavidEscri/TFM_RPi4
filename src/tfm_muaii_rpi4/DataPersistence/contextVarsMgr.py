__author__ = "Jose David Escribano Orts"
__subsystem__ = "DataPersistence"
__module__ = "contextVarsMgr"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import os

from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service

Logs = LogsSingleton()


class ContextVarsConst:
    PEOPLE = "people"
    COORDENADAS_GPS = "coordenadas_gps"
    SATELITES_GNSS = "satelites_gnss"
    PRECISION_GNSS = "precision_gnss"


class _ContextVarsMgr(Service):
    def __init__(self):
        super().__init__(__info__)
        try:
            self._initDefaultContextVars()
        except Exception as e:
            super().critical_error(e, "init")

    def _initDefaultContextVars(self):
        self._contextVarDict: dict = {}
        self._contextVarDict.setdefault(ContextVarsConst.PEOPLE, 0)
        self._contextVarDict.setdefault(ContextVarsConst.COORDENADAS_GPS, dict())
        self._contextVarDict.setdefault(ContextVarsConst.SATELITES_GNSS, 0)
        self._contextVarDict.setdefault(ContextVarsConst.PRECISION_GNSS, 0)

    def start(self):
        try:
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        try:
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def set_context_var(self, var: str, value: any) -> None:
        self._contextVarDict[var] = value
        os.environ[var] = str(value)

    def get_context_var(self, var: str) -> any:
        if var in self._contextVarDict:
            return self._contextVarDict[var]
        else:
            context_var: str = os.getenv(var)
            if context_var is None:
                Logs.get_logger().error(f"No se encontró la variable de contexto: {var}", extra=__info__)
            return context_var


class ContextVarsMgrSingleton:
    __instance = None

    def __new__(cls):
        if ContextVarsMgrSingleton.__instance is None:
            ContextVarsMgrSingleton.__instance = _ContextVarsMgr()
        return ContextVarsMgrSingleton.__instance