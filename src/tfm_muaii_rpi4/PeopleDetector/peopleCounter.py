__author__ = "Jose David Escribano Orts"
__subsystem__ = "PeopleDetector"
__module__ = "peopleCounter"
__version__ = "0.1"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import os
import cv2
import torch
import yaml

from picamera2 import Picamera2
from yolov5.models.experimental import attempt_load
from yolov5.utils.general import non_max_suppression, xyxy2xywh

from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import ContextVarsMgrSingleton, ContextVarsConst
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service

Logs = LogsSingleton()


class ImageDetectionConfig:
    # Tamaño para capturar la imagen para que se utilice todo el sensor óptico
    ORIGINAL_WIDTH = 1640
    ORIGINAL_HEIGHT = 1232
    ORIGINAL_SIZE = (ORIGINAL_WIDTH, ORIGINAL_HEIGHT)

    # Tamaño adaptado al utilizado en el set de entrenamiento de YOLOv5 para mejorar el resultadod e las predicciones
    NEW_WIDTH = 640
    NEW_HEIGHT = 640
    NEW_SIZE = (NEW_WIDTH, NEW_HEIGHT)

    # Formato de imagen
    FORMAT = "RGB888"

    # Límite inferior de confianza en las detecciones
    CONF_THRESHOLD: float = 0.1

    # Límite inferior para eliminar detecciones redundantes
    IOU_THRESHOLD: float = 0.5

    # Factor de filtro
    FILTER_FACTOR: float = 0.8


class _PeopleCounter(Service):

    def __init__(self, show_image=False):
        super().__init__(__info__, is_thread=True)
        self._env = EnvSingleton()
        self._context_vars_mgr = ContextVarsMgrSingleton()

        self.__smoothed_person_count: int = 0  # Inicializar el contador suavizado
        self.__show_image: bool = show_image
        self.__classes: list = []
        self.__init_camara()

        self.sleep_period = 0.5

    def __init_camara(self):
        self.__device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_path = self._env.get_path(self._env.yolo_models_path)
        model_file = os.path.join(model_path, "yolov5n.pt")
        self.__model = attempt_load(model_file, device=self.__device).eval()

        if self.__show_image:
            self.__load_yaml()

        self.__camera = Picamera2()
        camera_config = self.__camera.create_preview_configuration(
            main={
                "size": ImageDetectionConfig.ORIGINAL_SIZE,
                "format": ImageDetectionConfig.FORMAT
            }
        )
        self.__camera.configure(camera_config)

    def __load_yaml(self):
        class_path = self._env.get_path(self._env.yolo_classes_path)
        class_file = os.path.join(class_path, "coco.yaml")
        with open(class_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self.__classes = data["names"]

    def start(self):
        try:
            self.__camera.start()
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        try:
            self.__camera.stop()
            if self.__show_image:
                cv2.destroyAllWindows()
            super().stop()
        except Exception as e:
            super().critical_error(e, "stop")

    def _run(self):
        try:
            if not self.__camera.is_open:
                raise Exception("La camara no está lista para capturar imagenes.")

            while not super().need_stop():
                frame = self.__camera.capture_array()
                if frame is None:
                    Logs.get_logger().error("Error al leer el fotograma de la camara", extra=__info__)
                else:
                    frame = cv2.flip(frame, 0)
                    self.__process_frame(frame)
                    if self.__show_image:
                        cv2.namedWindow("Picamera2 - Object Detection", cv2.WINDOW_NORMAL)
                        cv2.imshow("Picamera 2 - Object Detection", frame)
                        if cv2.waitKey(1) & 0xFF == ord('q'):
                            self.stop()
                super().sleep_period()
        except Exception as e:
            Logs.get_logger().error(f"Error en el run del detector de personas: {e}", extra=__info__)
            super().critical_error(e, "_run")

    # def _run_test_images(self):
    #     try:
    #         image_folder = self._env.get_path(self._env.images_test_path)
    #         image_files = [f for f in os.listdir(image_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]
    #
    #         for image_file in image_files:
    #             image_path = os.path.join(image_folder, image_file)
    #             frame = cv2.imread(image_path)
    #
    #             if frame is not None:
    #                 self.__process_frame(frame)
    #                 Logs.get_logger().info(f"Recuento de personas: {round(self._person_count)}", extra=__info__)
    #             else:
    #                 Logs.get_logger().error(f"Error al leer la imagen: {image_path}", extra=__info__)
    #
    #             super().sleep_period()
    #
    #     except Exception as e:
    #         Logs.get_logger().error(f"Error en la ejecución del detector de personas: {e}", extra=__info__)
    #         super().critical_error(e, "_run")

    def __process_frame(self, frame):
        prediction = self.__detect(frame)
        if prediction is not None and len(prediction) > 0:
            person_count = len(prediction)
            if self.__show_image:
                for detection in prediction:
                    prediction[:, :4] = xyxy2xywh(prediction[:, :4])
                    x, y, w, h = detection[:4]
                    confidence = detection[4].item()  # Obtenemos la confianza de la prediccion
                    class_id = int(detection[5].item())
                    label = self.__classes[class_id]
                    self._draw_bounding_box(frame, (x, y, w, h), label, confidence)
            self.__update_people_count(person_count)

    def __detect(self, frame):
        img = torch.from_numpy(frame).to(self.__device)
        img = img.float() / 255.0
        img = img.permute(2, 0, 1).unsqueeze(0)  # Cambiar el orden de los canales y agregar dimensión batch
        with torch.no_grad():
            img = torch.nn.functional.interpolate(img, size=ImageDetectionConfig.NEW_SIZE, mode='bilinear', align_corners=False)
            pred = self.__model(img)[0]
            return non_max_suppression(pred, ImageDetectionConfig.CONF_THRESHOLD, ImageDetectionConfig.IOU_THRESHOLD, classes=[0])[0]

    @staticmethod
    def _draw_bounding_box(frame, bbox, label, confidence):
        x, y, w, h = bbox
        scale_x = ImageDetectionConfig.ORIGINAL_WIDTH / ImageDetectionConfig.NEW_WIDTH
        scale_y = ImageDetectionConfig.ORIGINAL_HEIGHT / ImageDetectionConfig.NEW_HEIGHT
        x1, y1, x2, y2 = int((x - w / 2) * scale_x), int((y - h / 2) * scale_y), int((x + w / 2) * scale_x), int((y + h / 2) * scale_y)

        cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)
        cv2.putText(frame, f"{label}: {confidence:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    def __update_people_count(self, person_count):
        Logs.get_logger().debug(f"Nueva detección de personas {self.get_current_people()} -> {person_count}",
                                extra=__info__)
        if self.get_current_people() == 0:  # Se le da mayor importancia a las nuevas personas detectadas
            self.__smoothed_person_count = (
                (1 - ImageDetectionConfig.FILTER_FACTOR) * self.__smoothed_person_count + ImageDetectionConfig.FILTER_FACTOR * person_count
            )
        else: # Se le da mayor importancia a las personas anteriormente detectadas
            self.__smoothed_person_count = (
                    ImageDetectionConfig.FILTER_FACTOR * self.__smoothed_person_count + (1 - ImageDetectionConfig.FILTER_FACTOR) * person_count
            )
        self.__set_current_people()

    def __set_current_people(self):
        self._context_vars_mgr.set_context_var(ContextVarsConst.PERSONAS, self.get_current_people())

    def get_current_people(self):
        return round(self.__smoothed_person_count)


class PeopleCounterSingleton:
    __instance = None

    def __new__(cls):
        if PeopleCounterSingleton.__instance is None:
            PeopleCounterSingleton.__instance = _PeopleCounter()
        return PeopleCounterSingleton.__instance
