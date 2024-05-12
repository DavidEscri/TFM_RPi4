__author__ = "Jose David Escribano Orts"
__subsystem__ = "DisplayController"
__module__ = "displayController"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

from luma.core.interface.serial import i2c
from luma.oled.device import sh1107

from tfm_muaii_rpi4.Utils.utils import Service
from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import ContextVarsMgrSingleton, ContextVarsConst
from tfm_muaii_rpi4.Utils.display.displayUtils import DisplayUtils, DisplayOLEDConfig
from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class _DisplayController(Service):
    BAD_ROAD_COUNTER: int = 5
    GPS_COUNTER: int = 5
    SEATING_CAPACITY_COUNTER: int = 10

    def __init__(self, i2c_port=4, i2c_address=0x3C):
        super().__init__(__info__, is_thread=True)
        self._i2c_port = i2c_port
        self._i2c_address = i2c_address
        self._env = EnvSingleton()
        self._context_vars = ContextVarsMgrSingleton()
        self._serial_device: i2c = None
        self._oled_device: sh1107 = None
        self._display_utils: DisplayUtils = None
        self.sleep_period = 1

    def start(self):
        try:
            self._start_display()
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def _start_display(self) -> bool:
        try:
            # Configura la conexión I2C
            self._serial_device = i2c(port=self._i2c_port, address=self._i2c_address)
            # Inicializa el dispositivo OLED
            self._oled_device = sh1107(self._serial_device, rotate=0,
                                       width=DisplayOLEDConfig.WIDTH, height=DisplayOLEDConfig.HEIGHT)
            text_font_path = self._env.get_path(self._env.font_path)
            self._display_utils = DisplayUtils(self._oled_device, text_font_path)
            return True
        except Exception as e:
            Logs.get_logger().error(f"Error al iniciar Display OLED: {e}", extra=__info__)
            return False

    def stop(self):
        try:
            self._stop_display()
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def _stop_display(self) -> bool:
        try:
            # Se dibuja una imagen vacia y se terminan los recursos asociados al dispositivo OLED (incluido I2C)
            self._oled_device.cleanup()
            return True
        except Exception as e:
            Logs.get_logger().error(f"Error al terminar Display OLED: {e}", extra=__info__)
            return False

    def _run(self):
        bad_road_counter: int = self.BAD_ROAD_COUNTER
        gps_counter: int = self.GPS_COUNTER
        seating_capacity_counter = self.SEATING_CAPACITY_COUNTER
        max_vehicle_capacity = self._context_vars.get_context_var(ContextVarsConst.MAX_PERSONAS)
        while not super().need_stop():
            try:
                vehiculo_parado: bool = self._context_vars.get_context_var(ContextVarsConst.VEHICULO_PARADO)
                if vehiculo_parado and seating_capacity_counter > 0:
                    seating_capacity_counter -= 1
                    current_people = self._context_vars.get_context_var(ContextVarsConst.PERSONAS)
                    self._display_utils.display_seating_capacity(current_people, max_vehicle_capacity)
                else:
                    is_bad_road: bool = self._context_vars.get_context_var(ContextVarsConst.MAL_ESTADO_CARRETERA)
                    if is_bad_road and bad_road_counter > 0:
                        self._display_utils.display_road_bad_state()
                        bad_road_counter -= 1
                        if bad_road_counter == 0:
                            gps_counter = self.GPS_COUNTER
                    else:
                        current_speed: int = self._context_vars.get_context_var(ContextVarsConst.VELOCIDAD_ACTUAL)
                        max_speed: int = self._context_vars.get_context_var(ContextVarsConst.VELOCIDAD_MAXIMA)
                        location_info: str = self._context_vars.get_context_var(ContextVarsConst.UBICACION_INFO)
                        self._display_utils.display_geolocation(current_speed, max_speed, location_info)
                        gps_counter -= 1
                        if gps_counter == 0:
                            bad_road_counter = self.BAD_ROAD_COUNTER
                            gps_counter = self.GPS_COUNTER
                            seating_capacity_counter = self.SEATING_CAPACITY_COUNTER
                        elif bad_road_counter != 0:
                            bad_road_counter = self.BAD_ROAD_COUNTER
                super().sleep_period()
            except Exception as e:
                Logs.get_logger().error(f"Error hilo Display OLED: {e}", extra=__info__)


class DisplayControllerSingleton:
    __instance = None

    def __new__(cls):
        if DisplayControllerSingleton.__instance is None:
            DisplayControllerSingleton.__instance = _DisplayController()
        return DisplayControllerSingleton.__instance