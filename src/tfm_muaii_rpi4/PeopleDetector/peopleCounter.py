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


class _PeopleCounter(Service):
    CONF_THRESHOLD: float = 0.1
    IOU_THRESHOLD: float = 0.5
    FILTER_FACTOR: float = 0.8

    def __init__(self, show_image=False):
        super().__init__(__info__, is_thread=True)
        self._env = EnvSingleton()
        self._context_vars_mgr = ContextVarsMgrSingleton()

        self.__smoothed_person_count: int = 0  # Inicializar el contador suavizado
        self.__show_image: bool = show_image
        self.__classes: list = []
        self.__init_camara()

        self.sleep_period = 1

    def __init_camara(self):
        self.__device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_path = self._env.get_path(self._env.yolo_models_path)
        model_file = os.path.join(model_path, "yolov5n.pt")
        self.__model = attempt_load(model_file, device=self.__device)
        self.__model.to(self.__device).eval()

        class_path = self._env.get_path(self._env.yolo_classes_path)
        class_file = os.path.join(class_path, "coco.yaml")
        self._load_yaml(class_file)

        self.__camera = Picamera2()
        camera_config = self.__camera.create_preview_configuration(main={"size": (640, 480), "format": "RGB888" })
        self.__camera.configure(camera_config)

    def _load_yaml(self, yaml_file):
        with open(yaml_file, "r", encoding="utf-8") as f:
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
                    self.__process_frame(frame)
                super().sleep_period()
        except Exception as e:
            Logs.get_logger().error(f"Error en el run del detector de personas: {e}", extra=__info__)
            super().critical_error(e, "_run")

    # def _run_cv2(self):
    #     try:
    #         cap = cv2.VideoCapture(0)
    #
    #         if not cap.isOpened():
    #             Logs.get_logger().critical("No se pudo abrir la cámara para obtener imagenes.", extra=__info__)
    #             raise Exception("No se pudo abrir la cámara para obtener imagenes.")
    #
    #         while not super().need_stop():
    #             ret, frame = cap.read()
    #             if not ret:
    #                 Logs.get_logger().error("Error al leer el fotograma de la camara", extra=__info__)
    #             else:
    #                 self.__process_frame(frame)
    #                 Logs.get_logger().info(f"Recuento de personas: {round(self.__smoothed_person_count)}",
    #                                        extra=__info__)
    #             super().sleep_period()
    #
    #         cap.release()
    #         cv2.destroyAllWindows()
    #     except Exception as e:
    #         Logs.get_logger().error(f"Error en el run del detector de personas: {e}", extra=__info__)
    #         super().critical_error(e, "_run")

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
        pred = self.__detect(frame)
        if pred is not None and len(pred) > 0:
            # det = pred  # Todas las detecciones
            # det[:, :4] = xyxy2xywh(det[:, :4])  # Convertir coordenadas a xywh

            #xywh = det[:, :4].tolist()
            labels_detected = pred[:, 5].int().tolist()
            # confidences = pred[:, 4].tolist()

            # for label, confidence, bbox in zip(labels, confidences, xywh):
            #     object_name = self.__classes[label]
            #     # print(f"Object detected: {object_name}, Confidence: {confidence:.2f}, Bounding Box: {bbox}")
            #     self._draw_bounding_box(frame, bbox, object_name, confidence)

            self.__count_people(labels_detected)

            # Mostrar el frame con las detecciones
            # if self.__show_image:
            #     cv2.imshow("YOLOv5 Object Detection", frame)
            #
            #     # Salir al presionar 'q'
            #     if cv2.waitKey(1) & 0xFF == ord('q'):
            #         self.stop()

    def __detect(self, frame):
        img = torch.from_numpy(frame).to(self.__device)
        img = img.float() / 255.0
        img = img.permute(2, 0, 1).unsqueeze(0)  # Cambiar el orden de los canales y agregar dimensión batch

        pred = self.__model(img)[0]
        pred = non_max_suppression(pred, self.CONF_THRESHOLD, self.IOU_THRESHOLD)[0]

        return pred

    # @staticmethod
    # def _draw_bounding_box(frame, bbox, label, confidence):
    #     if label == "person":
    #         x, y, w, h = bbox
    #         x1, y1, x2, y2 = int(x - w / 2), int(y - h / 2), int(x + w / 2), int(y + h / 2)
    #         Logs.get_logger().debug(f"El frame es del tipo: {frame.dtype}", extra=__info__)
    #
    #         # Dibujar el bounding box en la imagen
    #         cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)
    #         cv2.putText(frame, f"{label}: {confidence:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    def __count_people(self, labels):
        person_count = sum(1 for label in labels if self.__classes[label].lower() == 'person')
        self.__update_people_count(person_count)

    def __update_people_count(self, person_count):
        Logs.get_logger().debug(f"Nueva detección de personas {self.get_current_people()} -> {person_count}",
                                extra=__info__)
        if self.get_current_people() == 0:  # Se le da mayor importancia a las nuevas personas detectadas
            self.__smoothed_person_count = (
                (1 - self.FILTER_FACTOR) * self.__smoothed_person_count + self.FILTER_FACTOR * person_count
            )
        else: # Se le da mayor importancia a las personas anteriormente detectadas
            self.__smoothed_person_count = (
                    self.FILTER_FACTOR * self.__smoothed_person_count + (1 - self.FILTER_FACTOR) * person_count
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
