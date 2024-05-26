__author__ = "Jose David Escribano Orts"
__subsystem__ = "AccelController"
__module__ = "accelController"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import smbus2
import time

from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import ContextVarsMgrSingleton, ContextVarsConst
from tfm_muaii_rpi4.Utils.accelerometer.ADXL345 import ADXL345, RegistersADXL345
from tfm_muaii_rpi4.Utils.utils import Service

Logs = LogsSingleton()


class _AccelController(Service):
    I2C_BUS: int = 1
    DEVIATION_THRESHOLD: float = 2.0

    def __init__(self):
        super().__init__(__info__, is_thread=True)
        self._i2c_bus: smbus2.SMBus = None
        self._accel_module: ADXL345 = None
        self._context_vars = ContextVarsMgrSingleton()
        self.sleep_period = 1

    def start(self):
        try:
            while not super().need_stop():
                if not self._start_accel():
                    Logs.get_logger().warning("No se pudo inicializar el acelerómetro, próxima intento en 30 segundos",
                                              extra=__info__)
                    time.sleep(30)
                break
            super().start()
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def _start_accel(self) -> bool:
        try:
            if self._open_i2c_bus():
                self._accel_module = ADXL345(self._i2c_bus)
                return self._accel_module.set_configuration()
            return False
        except Exception as e:
            Logs.get_logger().error(f"Error al iniciar Acelerómetro: {e}", extra=__info__)
            return False

    def _open_i2c_bus(self) -> bool:
        try:
            if self._i2c_bus is None:
                self._i2c_bus = smbus2.SMBus(self.I2C_BUS)
                Logs.get_logger().info(f"Bus {self.I2C_BUS} del puerto I2C del acelerómetro abierto correctamente.",
                                       extra=__info__)
                return True
            elif isinstance(self._i2c_bus, smbus2.SMBus):
                Logs.get_logger().info("El bus I2C del acelerómetro ya estaba abierto.", extra=__info__)
                return True
            else:
                Logs.get_logger().warning("La inicialización del bus I2C del acelerómetro no se realizó correctamente",
                                          extra=__info__)
                return False
        except Exception as e:
            Logs.get_logger().error("Error al acceder al puerto I2C del acelerómetro: %s", e, extra=__info__)
            return False

    def stop(self):
        try:
            self._stop_accel()
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def _stop_accel(self) -> bool:
        try:
            if self._i2c_bus is None:
                Logs.get_logger().warning("El puerto I2C del acelerometro ya está cerrado o no funciona",
                                          extra=__info__)
                return False
            elif isinstance(self._i2c_bus, smbus2.SMBus):
                return self._close_i2c_bus()
            else:
                return False
        except Exception as e:
            Logs.get_logger().error("Error al cerrar el bus del acelerometro, %s", e, extra=__info__)
            return False

    def _close_i2c_bus(self) -> bool:
        try:
            self._i2c_bus.close()
            self._i2c_bus = None
            Logs.get_logger().info(f"Bus {self.I2C_BUS} del puerto I2C cerrado correctamente.", extra=__info__)
            return True
        except Exception as e:
            Logs.get_logger().error("Error al intentar cerrar el puerto I2C: %s", e, extra=__info__)
            return False

    def _run(self):
        try:
            mal_estado_counter: int = 0
            buen_estado_counter: int = 0
            max_counter: int = 5
            while not super().need_stop():
                all_axis_accel = self._accel_module.get_all_axis()
                z_axis_accel = all_axis_accel["eje_z"]
                if abs(z_axis_accel - RegistersADXL345.EARTH_GRAVITY) > self.DEVIATION_THRESHOLD:
                    mal_estado_counter += 1
                    buen_estado_counter = max(0, buen_estado_counter - 1)
                else:
                    buen_estado_counter = (buen_estado_counter + 1) if buen_estado_counter < max_counter else max_counter
                    if buen_estado_counter >= max_counter:
                        mal_estado_counter = 0
                    else:
                        mal_estado_counter = max(0, mal_estado_counter - 1)
                if mal_estado_counter >= max_counter:
                    buen_estado_counter = 0
                    self._context_vars.set_context_var(ContextVarsConst.MAL_ESTADO_CARRETERA, True)
                    Logs.get_logger().warning("Carretera en mal estado detectada", extra=__info__)
                else:
                    self._context_vars.set_context_var(ContextVarsConst.MAL_ESTADO_CARRETERA, False)
                super().sleep_period()
        except Exception as e:
            Logs.get_logger().error(f"Error hilo acelerómetro: {e}", extra=__info__)


class AccelControllerSingleton:
    __instance = None

    def __new__(cls):
        if AccelControllerSingleton.__instance is None:
            AccelControllerSingleton.__instance = _AccelController()
        return AccelControllerSingleton.__instance
