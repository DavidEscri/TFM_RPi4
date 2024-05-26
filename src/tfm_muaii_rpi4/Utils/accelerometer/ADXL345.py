__author__ = "Jose David Escribano Orts"
__subsystem__ = "Utils"
__module__ = "ADXL345"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import smbus2
import time
from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class RegistersADXL345:
    ADDRESS: int = 0x53

    DATA_FORMAT = 0x31
    BANDWIDTH_RATE_REG = 0x2C
    POWER_CTL = 0x2D
    ENABLE_MEASURE = 0x08
    DISABLE_MEASURE = 0x00

    SCALE_MULTIPLIER: int = 0.0039
    EARTH_GRAVITY: int = 9.80665

    BANDWIDTH_RATE_1600HZ = 0x0F
    BANDWIDTH_RATE_800HZ = 0x0E
    BANDWIDTH_RATE_400HZ = 0x0D
    BANDWIDTH_RATE_200HZ = 0x0C
    BANDWIDTH_RATE_100HZ = 0x0B
    BANDWIDTH_RATE_50HZ = 0x0A  # Data rate = 100 Hz
    BANDWIDTH_RATE_25HZ = 0x09

    RANGE_2G = 0x00
    RANGE_4G = 0x01
    RANGE_8G = 0x02
    RANGE_16G = 0x03

    DATAX0 = 0x32
    DATAX1 = 0x33
    DATAY0 = 0x34
    DATAY1 = 0x35
    DATAZ0 = 0x36
    DATAZ1 = 0x37


class ADXL345:
    def __init__(self, bus: smbus2.SMBus):
        # DATASHEET: https://www.sparkfun.com/datasheets/Sensors/Accelerometer/ADXL345.pdf
        self.bus = bus

    def set_configuration(self):
        """
        Set ADXL345 configuration.
        """
        try:
            self._set_bandwidth_rate(RegistersADXL345.BANDWIDTH_RATE_50HZ)
            self._set_data_range()
            self._enable_measurement()
            time.sleep(1)
            Logs.get_logger().info(f"Configuracion del acelerómetro seteada correctamente", extra=__info__)
            return True
        except Exception as e:
            Logs.get_logger().error(f"Error al setear la configuracion del acelerómetro: %s", e, extra=__info__)
            return False

    def _set_bandwidth_rate(self, rate: int):
        """
        ADXL345 address, 0x53(83)
        Select bandwidth rate register, 0x2C(44)
        0x0A(10) -> 00001010
        Normal operation, output data rate = 100 Hz
        """
        try:
            self.bus.write_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.BANDWIDTH_RATE_REG, rate)
            Logs.get_logger().info(f"Frecuencia de salida de datos configurada a {rate} Hz (1/3)", extra=__info__)
        except Exception as e:
            Logs.get_logger().error(f"No se pudo configurar la frecuencia de salida de datos a {rate} Hz (1/3): %s", e,
                                    extra=__info__)

    def _set_data_range(self):
        """
        ADXL345 address, 0x53(83)
        Select data format register, 0x31(49)
        0x08(08) -> 00001000
        Self test disabled, 4-wire SPI interface, Full resolution, right justified mode, Range = +/-2g
        """
        try:
            self.bus.write_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.DATA_FORMAT, 0x08)
            time.sleep(0.5)
            Logs.get_logger().info(f"Rango +/- 2G configurado en el acelerómetro (2/3)", extra=__info__)
        except Exception as e:
            Logs.get_logger().error(f"No se pudo configurar el rango del acelerómetro a +/- 2G (2/3): %s", e,
                                    extra=__info__)

    def _enable_measurement(self, enable: bool = True):
        """
        ADXL345 address, 0x53(83)
        Select power control register, 0x2D(45)
        Enable: 0x08(08) -> 00001000
        Inactivity and activity are concurrent, auto sleep disabled, measurement enabled, normal mode, frequency of 8 Hz
        of readings in sleep mode.

        Disable: 0x00(00) -> 00000000
        Inactivity and activity are concurrent, auto sleep disabled, measurement enabled, sleep mode, frequency of 8 Hz
        of readings in sleep mode.
        """
        try:
            if enable:
                self.bus.write_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.POWER_CTL,
                                         RegistersADXL345.ENABLE_MEASURE)
                Logs.get_logger().info(f"Medición habilitada en el acelerómetro (3/3)", extra=__info__)
            else:
                self.bus.write_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.POWER_CTL,
                                         RegistersADXL345.DISABLE_MEASURE)
                Logs.get_logger().info(f"Medición deshabilitada en el acelerómetro", extra=__info__)
        except Exception as e:
            Logs.get_logger().error(f"No se pudo habilitar la medición en el acelerómetro (3/3): %s", e,
                                    extra=__info__)

    def get_axis_x(self) -> int:
        """
        # ADXL345 address, 0x53(83)
        # Read data back from 0x32(50), 2 bytes: X-Axis LSB, X-Axis MSB
        """
        data0 = self.bus.read_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.DATAX0)
        data1 = self.bus.read_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.DATAX1)
        # Convert the data to 10-bits
        xAccl = ((data1 & 0x03) * 256) + data0
        if xAccl > 511:
            xAccl -= 1024
        return xAccl

    def get_axis_y(self) -> int:
        """
        # ADXL345 address, 0x53(83)
        # Read data back from 0x34(52), 2 bytes: Y-Axis LSB, Y-Axis MSB
        """
        data0 = self.bus.read_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.DATAY0)
        data1 = self.bus.read_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.DATAY1)
        # Convert the data to 10-bits
        yAccl = ((data1 & 0x03) * 256) + data0
        if yAccl > 511:
            yAccl -= 1024
        return yAccl

    def get_axis_z(self) -> int:
        """
        # ADXL345 address, 0x53(83)
        # Read data back from 0x36(54), 2 bytes: Z-Axis LSB, Z-Axis MSB
        """
        data0 = self.bus.read_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.DATAZ0)
        data1 = self.bus.read_byte_data(RegistersADXL345.ADDRESS, RegistersADXL345.DATAZ1)

        # Convert the data to 10-bits
        zAccl = ((data1 & 0x03) * 256) + data0
        if zAccl > 511:
            zAccl -= 1024
        return zAccl

    @staticmethod
    def convert_10bits_to_ms2(accel: int) -> int:
        """
        Convierte el valor de aceleración recibido a m/s²
        :param accel: Aceleración expresada en un número con un valor máximo de 10 bits.
        :type accel: int
        :return: Aceleración expresada en m/s²
        :rtype: int
        """
        accel_ms2 = accel * RegistersADXL345.SCALE_MULTIPLIER * RegistersADXL345.EARTH_GRAVITY
        return round(accel_ms2, 4)

    def get_all_axis(self) -> dict:
        return {"eje_x": self.convert_10bits_to_ms2(self.get_axis_x()),
                "eje_y": self.convert_10bits_to_ms2(self.get_axis_y()),
                "eje_z": self.convert_10bits_to_ms2(self.get_axis_z())}