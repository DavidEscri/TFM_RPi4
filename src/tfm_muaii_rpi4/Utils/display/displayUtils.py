__author__ = "Jose David Escribano Orts"
__subsystem__ = "Utils"
__module__ = "displayUtils"
__version__ = "1.0"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

from luma.oled.device import sh1107
from PIL import Image, ImageDraw, ImageFont

from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import DefaultVarsConst
from tfm_muaii_rpi4.Logger.logger import LogsSingleton

Logs = LogsSingleton()


class DisplayOLEDConfig:
    # Tamaño de la pantalla OLED (128 x 128)
    WIDTH = 128
    HEIGHT = 128

    # Tamaño de la señal de tráfico en relación al tamaño de la pantalla
    TRAFFIC_SIGN_SIZE = WIDTH // 2  # 64x64


class DisplayUtils:
    def __init__(self, device: sh1107, font_path: str):
        if not isinstance(device, sh1107):
            raise Exception("El modelo del display es diferente al sh1107")
        self.__device = device
        self.__text_font = font_path

    def clear_display(self):
        """
        Borra el contenido de la pantalla
        :return:
        """
        self.__device.clear()

    def __display_image(self, image: Image):
        """
        Muestra una imagen en la pantalla OLED
        :param image: Imagen a mostrar
        :return:
        """
        self.__device.display(image)

    def display_seating_capacity(self, current_passengers, max_capacity):
        image = Image.new("1", (DisplayOLEDConfig.WIDTH, DisplayOLEDConfig.HEIGHT), "black")
        draw = ImageDraw.Draw(image)
        if int(current_passengers) > int(max_capacity):
            Logs.get_logger().warning("Mostrando imagen de aforo máximo superado en display OLED", extra=__info__)
            triangle_height = 60
            triangle_width = 70
            triangle_top_x = (DisplayOLEDConfig.WIDTH - triangle_width) // 2
            triangle_top_y = 10

            # Coordenadas de los vértices del triángulo
            triangle_vertices = [
                (triangle_top_x, triangle_top_y + triangle_height),
                (triangle_top_x + triangle_width, triangle_top_y + triangle_height),
                (triangle_top_x + triangle_width // 2, triangle_top_y)
            ]

            # Dibujar el triángulo de advertencia
            draw.polygon(triangle_vertices, fill="white")

            exclamation_font = ImageFont.load_default(size=45)
            exclamation_width, exclamation_height = draw.textbbox((0, 0), "!", font=exclamation_font)[2:]
            exclamation_x = triangle_top_x + (triangle_width - exclamation_width) // 2
            exclamation_y = triangle_top_y + 5 + (triangle_height - exclamation_height) // 2
            draw.text((exclamation_x, exclamation_y), "!", font=exclamation_font, fill="black")

            text_x = (DisplayOLEDConfig.WIDTH - 64) // 2
            text_y = (DisplayOLEDConfig.HEIGHT - 64) + 15
            info_font = ImageFont.truetype(self.__text_font, 16)
            # Texto a mostrar
            text_seating_capacity = f"Límite de ocupación superado ({current_passengers}/{max_capacity})"
            # Dividir el texto en líneas para que quepa en la pantalla
            lines = self.__split_text_into_lines(draw, text_seating_capacity, info_font)
            self.__draw_text_lines(draw, info_font, lines, text_x, text_y)
            self.__display_image(image)
            return
        Logs.get_logger().info(f"Mostrando imagen de aforo actual ({current_passengers}/{max_capacity}) "
                               f"en display OLED", extra=__info__)
        top_text = "Aforo actual:"
        top_info_font = ImageFont.truetype(self.__text_font, 25)
        top_text_bbox = draw.textbbox((0, 0), str(top_text), font=top_info_font)
        top_text_width = top_text_bbox[2] - top_text_bbox[0]
        top_text_height = top_text_bbox[3] - top_text_bbox[1]
        top_text_x = (DisplayOLEDConfig.WIDTH - top_text_width) // 2
        top_text_y = top_text_height - 7  # Un pequeño margen desde la parte superior
        draw.text((top_text_x, top_text_y), top_text, font=top_info_font, fill="white")

        info_font = ImageFont.truetype(self.__text_font, 45)
        text_seating_capacity = f"{current_passengers}/{max_capacity}"
        lines = self.__split_text_into_lines(draw, text_seating_capacity, info_font)
        text_x = DisplayOLEDConfig.WIDTH // 2
        text_y = (DisplayOLEDConfig.HEIGHT // 2) - 10
        self.__draw_text_lines(draw, info_font, lines, text_x, text_y)
        self.__display_image(image)

    def display_geolocation(self, current_speed, speed_limit, location_info):
        self.__draw_speed_limit(speed_limit, current_speed, location_info)

    def display_road_bad_state(self):
        Logs.get_logger().warning("Mostrando mal estado de la carretera en display OLED", extra=__info__)
        image = Image.new("1", (DisplayOLEDConfig.WIDTH, DisplayOLEDConfig.HEIGHT), "black")
        draw = ImageDraw.Draw(image)

        triangle_height = 60
        triangle_width = 70
        triangle_top_x = (DisplayOLEDConfig.WIDTH - triangle_width) // 2
        triangle_top_y = 10

        # Coordenadas de los vértices del triángulo
        triangle_vertices = [
            (triangle_top_x, triangle_top_y + triangle_height),
            (triangle_top_x + triangle_width, triangle_top_y + triangle_height),
            (triangle_top_x + triangle_width // 2, triangle_top_y)
        ]

        # Dibujar el triángulo de advertencia
        draw.polygon(triangle_vertices, fill="white")

        exclamation_font = ImageFont.load_default(size=45)
        exclamation_width, exclamation_height = draw.textbbox((0, 0), "!", font=exclamation_font)[2:]
        exclamation_x = triangle_top_x + (triangle_width - exclamation_width) // 2
        exclamation_y = triangle_top_y + 5 + (triangle_height - exclamation_height) // 2
        draw.text((exclamation_x, exclamation_y), "!", font=exclamation_font, fill="black")

        text_x = (DisplayOLEDConfig.WIDTH - 64) // 2
        text_y = (DisplayOLEDConfig.HEIGHT - 64) + 15  # Ajuste hacia arriba
        info_font = ImageFont.truetype(self.__text_font, 20)
        # Texto a mostrar
        text_bad_road_state = "Carretera en mal estado"
        # Dividir el texto en líneas para que quepa en la pantalla
        lines = self.__split_text_into_lines(draw, text_bad_road_state, info_font)
        self.__draw_text_lines(draw, info_font, lines, text_x, text_y)
        self.__display_image(image)

    def __draw_speed_limit(self, speed_limit, current_speed, location_info: str):
        """
        Se dibuja la pantalla según los valores de máxima velocidad y la actual. Si no hay velocidad actual, no hay
        servicio GPS. Si no hay límite de velocidad, puede ser que no esté registrado. Si existen ambos, se comparan,
        si se supera la velocidad máxima, se avisa al conductor, en caso contrario, se informa de la carretera por la
        que se está circulando.
        :param speed_limit: Límite de velocidad de la carretera para dibujar su señal
        :param current_speed: Velocidad actual
        :return:
        """
        image = Image.new("1", (DisplayOLEDConfig.WIDTH, DisplayOLEDConfig.HEIGHT), "black")
        draw = ImageDraw.Draw(image)

        if current_speed is None:
            image = self.__geolocation_error(draw, image)
            Logs.get_logger().warning("Mostrando imagen de GPS no disponible en display OLED", extra=__info__)
            self.__display_image(image)
            return

        if speed_limit == DefaultVarsConst.MAX_SPEED:
            image = self.__speed_limit_error(draw, image, current_speed)
            Logs.get_logger().warning("Mostrando imagen de velocidad actual en display OLED", extra=__info__)
            self.__display_image(image)
            return

        # Coordenadas para la esquina inferior izquierda (señal de tráfico)
        top_left_x = 0
        top_left_y = DisplayOLEDConfig.HEIGHT - DisplayOLEDConfig.TRAFFIC_SIGN_SIZE

        draw.ellipse(
            (top_left_x, top_left_y, top_left_x + DisplayOLEDConfig.TRAFFIC_SIGN_SIZE,
             top_left_y + DisplayOLEDConfig.TRAFFIC_SIGN_SIZE),
            fill="white",
            outline="black"
        )

        inner_circle_margin = 10  # Margen para el círculo interior
        draw.ellipse(
            (top_left_x + inner_circle_margin, top_left_y + inner_circle_margin,
             top_left_x + DisplayOLEDConfig.TRAFFIC_SIGN_SIZE - inner_circle_margin,
             top_left_y + DisplayOLEDConfig.TRAFFIC_SIGN_SIZE - inner_circle_margin),
            fill="white",
            outline="black"
        )
        #TODO: Eliminar todo lo relacionado con top_text, dejar directamente el texto de cuando se supera o no el límite.
        info_font = ImageFont.truetype(self.__text_font, 13)
        # Determinar el texto superior en función de si se supera el límite de velocidad
        if current_speed > speed_limit:
            Logs.get_logger().info("Mostrando imagen de limite de velocidad superado en display OLED", extra=__info__)
            top_text = "Atencion:"
            next_top_text = "Limite de velocidad superado"
        else:
            Logs.get_logger().info("Mostrando información sobre la ubicación actual en el display OLED", extra=__info__)
            top_text = "Conduciendo por:"
            next_top_text = location_info  # "Autovia del mediterraneo, Almoradi (Alicante)"

        # Dibujar el texto superior
        top_text_bbox = draw.textbbox((0, 0), str(top_text), font=info_font)
        top_text_width = top_text_bbox[2] - top_text_bbox[0]
        top_text_height = top_text_bbox[3] - top_text_bbox[1]
        top_text_x = (DisplayOLEDConfig.WIDTH - top_text_width) // 2
        top_text_y = top_text_height - 7  # Un pequeño margen desde la parte superior
        draw.text((top_text_x, top_text_y), top_text, font=info_font, fill="white")

        # Dividir el texto en líneas para que quepa en la pantalla
        road_font = ImageFont.truetype(self.__text_font, 16)
        lines = self.__split_text_into_lines(draw, next_top_text, road_font)
        self.__draw_text_lines(draw, road_font, lines, (DisplayOLEDConfig.WIDTH - top_text_width) // 2, top_text_y + top_text_height + 5)

        # Dibujar el texto del límite de velocidad
        max_speed_font = ImageFont.truetype(self.__text_font, 22)
        text_bbox = draw.textbbox((0, 0), str(speed_limit), font=max_speed_font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        text_x = top_left_x + (DisplayOLEDConfig.TRAFFIC_SIGN_SIZE - text_width) // 2
        text_y = top_left_y - 4 + (DisplayOLEDConfig.TRAFFIC_SIGN_SIZE - text_height) // 2
        draw.text((text_x, text_y), str(speed_limit), font=max_speed_font, fill="black")

        # Área para el texto de la velocidad actual y "km/h"
        text_area_size = 64
        text_area_x = DisplayOLEDConfig.WIDTH - text_area_size
        text_area_y = DisplayOLEDConfig.HEIGHT - text_area_size

        # Dibujar el texto de la velocidad actual
        current_speed_font = ImageFont.truetype(self.__text_font, 28)
        text_current_speed = str(current_speed)
        cs_bbox = draw.textbbox((0, 0), text_current_speed, font=current_speed_font)
        cs_width = cs_bbox[2] - cs_bbox[0]
        cs_height = cs_bbox[3] - cs_bbox[1]

        # Dibujar el texto "km/h"
        text_km_h = "km/h"
        kmh_bbox = draw.textbbox((0, 0), text_km_h, font=info_font)
        kmh_width = kmh_bbox[2] - kmh_bbox[0]
        kmh_height = kmh_bbox[3] - kmh_bbox[1]

        # Calcular la posición vertical para centrar ambos textos juntos
        total_text_height = cs_height + kmh_height
        cs_y = text_area_y - 4 + (total_text_height) // 2
        kmh_y = cs_y + cs_height + 8

        # Calcular la posición horizontal para centrar el texto de la velocidad actual
        cs_x = text_area_x + (text_area_size - cs_width) // 2

        # Calcular la posición horizontal para centrar el texto "km/h"
        kmh_x = text_area_x + (text_area_size - kmh_width) // 2
        # Dibujar los textos
        draw.text((cs_x, cs_y), text_current_speed, font=current_speed_font, fill="white")
        draw.text((kmh_x, kmh_y), text_km_h, font=info_font, fill="white")

        self.__display_image(image)

    def __geolocation_error(self, draw: ImageDraw, image: Image) -> Image:
        """
        Se dibuja una imagen donde se muestra un mensaje de aviso ya que el servicio de geolocalización no está
        disponible. No se dispone de velocidad máxima ni actual.
        :param draw: Dibujo
        :param image: Imagen
        :return:
        """
        triangle_height = 60
        triangle_width = 70
        triangle_top_x = (DisplayOLEDConfig.WIDTH - triangle_width) // 2
        triangle_top_y = 10

        # Coordenadas de los vértices del triángulo
        triangle_vertices = [
            (triangle_top_x, triangle_top_y + triangle_height),
            (triangle_top_x + triangle_width, triangle_top_y + triangle_height),
            (triangle_top_x + triangle_width // 2, triangle_top_y)
        ]

        # Dibujar el triángulo de advertencia
        draw.polygon(triangle_vertices, fill="white")

        exclamation_font = ImageFont.load_default(size=45)
        exclamation_width, exclamation_height = draw.textbbox((0, 0), "!", font=exclamation_font)[2:]
        exclamation_x = triangle_top_x + (triangle_width - exclamation_width) // 2
        exclamation_y = triangle_top_y + 5 + (triangle_height - exclamation_height) // 2
        draw.text((exclamation_x, exclamation_y), "!", font=exclamation_font, fill="black")

        text_x = (DisplayOLEDConfig.WIDTH - 64) // 2
        text_y = (DisplayOLEDConfig.HEIGHT - 64) + 15  # Ajuste hacia arriba
        info_font = ImageFont.truetype(self.__text_font, 20)
        # Texto a mostrar
        text_geolocation = "Geolocalizacion no disponible"
        # Dividir el texto en líneas para que quepa en la pantalla
        lines = self.__split_text_into_lines(draw, text_geolocation, info_font)
        self.__draw_text_lines(draw, info_font, lines, text_x, text_y)
        return image

    def __speed_limit_error(self, draw: ImageDraw, image: Image, current_speed: int) -> Image:
        """
        Se dibuja una imagen donde solo se muestra la velocidad actual, ya que no se disponde de la velocidad máxima, y
        por tanto, tampoco se dispone de información sobre la carretera.
        :param draw: Dibujo
        :param image: Imagen
        :return:
        """
        text_x = (DisplayOLEDConfig.WIDTH - 64) // 2
        text_y = (DisplayOLEDConfig.HEIGHT - 64) // 5

        info_font = ImageFont.truetype(self.__text_font, 32)
        current_speed_font = ImageFont.truetype(self.__text_font, 42)

        # Texto de la velocidad actual
        text_current_speed = str(current_speed)
        cs_bbox = draw.textbbox((0, 0), text_current_speed, font=current_speed_font)
        cs_width = cs_bbox[2] - cs_bbox[0]
        cs_height = cs_bbox[3] - cs_bbox[1]
        # Texto "km/h"
        text_km_h = "km/h"
        kmh_bbox = draw.textbbox((0, 0), text_km_h, font=info_font)
        kmh_width = kmh_bbox[2] - kmh_bbox[0]
        kmh_height = kmh_bbox[3] - kmh_bbox[1]

        total_text_height = cs_height + kmh_height
        cs_x = text_x + (64 - cs_width) // 2
        cs_y = text_y - 4 + (total_text_height) // 2
        kmh_x = text_x + (64 - kmh_width) // 2
        kmh_y = cs_y + cs_height + 8

        draw.text((cs_x, cs_y), text_current_speed, font=current_speed_font, fill="white")
        draw.text((kmh_x, kmh_y), text_km_h, font=info_font, fill="white")
        return image

    @staticmethod
    def __split_text_into_lines(draw: ImageDraw, text: str, font: ImageFont) -> list:
        """
        Se divide el texto en diferentes lineas para que quepa en el tamaño de la pantalla (128x128 pixeles)
        :param draw: Dibujo
        :param text: Texto completo a escribir
        :param font: Fuente utilizada
        :return:
        """
        lines = []
        words = text.split()
        while words:
            line = ''
            while words and draw.textbbox((0, 0), line + words[0], font=font)[2] <= DisplayOLEDConfig.WIDTH:
                line += (words.pop(0) + ' ')
            lines.append(line)
        return lines

    @staticmethod
    def __draw_text_lines(draw: ImageDraw, font: ImageFont, lines: list, x: int, y: int):
        """
        Dibuja, en base a las coordenadas dadas, el texto dividido por lineas.
        :param draw: Dibujo
        :param font: Fuente utilizada
        :param lines: Texto dividido en lineas
        :param x: Posición en el eje X
        :param y: Posición en el eje y
        :return:
        """
        y_offset = y
        for line in lines:
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            line_height = line_bbox[3] - line_bbox[1]
            line_x = (DisplayOLEDConfig.WIDTH - line_width) // 2
            draw.text((line_x, y_offset), line, font=font, fill="white")
            y_offset += line_height + 2  # Añadir un pequeño espacio entre líneas
