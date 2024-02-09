__author__ = "Jose David Escribano Orts"
__subsystem__ = "PeopleDetector"
__module__ = "peopleCounter"
__version__ = "0.1"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import math
import time
import cv2
import torch
import yaml
from yolov5.models.experimental import attempt_load
from yolov5.utils.general import non_max_suppression, xyxy2xywh
import os

from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service

Logs = LogsSingleton()


class _PeopleCounter(Service):
    CONF_THRESHOLD: float = 0.1
    IOU_THRESHOLD: float = 0.5
    FILTER_FACTOR: float = 0.8

    def __init__(self, show_image=True):
        super().__init__(__info__, True)
        self._env = EnvSingleton()
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_path = self._env.get_path(self._env.yolo_models_path)
        self._model_file = os.path.join(model_path, "yolov5n.pt")
        self._model = attempt_load(self._model_file, device=self._device)
        self._model.to(self._device).eval()
        self._person_count: int = 0  # Inicializar el contador de personas
        self._smoothed_person_count: int = 0  # Inicializar el contador suavizado
        self.sleep_period = 0.5
        self._show_image: bool = show_image
        self._classes: list = []

        class_path = self._env.get_path(self._env.yolo_classes_path)
        self._class_file = os.path.join(class_path, "coco.yaml")
        self._load_yaml(self._class_file)

    def _load_yaml(self, yaml_file):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self._classes = data["names"]

    def start(self):
        try:
            super().start()
        except Exception as e:
            super().critical_error(e, "start")

    def stop(self):
        super().stop()

    def _run(self):
        try:
            cap = cv2.VideoCapture(0)

            if not cap.isOpened():
                Logs.get_logger().critical("No se pudo abrir la cámara para obtener imagenes.", extra=__info__)
                raise Exception("No se pudo abrir la cámara para obtener imagenes.")

            while not super().need_stop():
                ret, frame = cap.read()
                if not ret:
                    Logs.get_logger().error("Error al leer el fotograma de la camara", extra=__info__)
                else:
                    self._process_frame(frame)
                    Logs.get_logger().info(f"Recuento de personas: {round(self._smoothed_person_count)}",
                                           extra=__info__)
                super().sleep_period()

            cap.release()
            cv2.destroyAllWindows()
        except Exception as e:
            Logs.get_logger().error(f"Error en el run del detector de personas: {e}", extra=__info__)
            super().critical_error(e, "_run")

    def _run_test_images(self):
        try:
            image_folder = self._env.get_path(self._env.images_test_path)
            image_files = [f for f in os.listdir(image_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]

            for image_file in image_files:
                image_path = os.path.join(image_folder, image_file)
                frame = cv2.imread(image_path)

                if frame is not None:
                    self._process_frame(frame)
                    Logs.get_logger().info(f"Recuento de personas: {round(self._person_count)}", extra=__info__)
                else:
                    Logs.get_logger().error(f"Error al leer la imagen: {image_path}", extra=__info__)

                time.sleep(10)

        except Exception as e:
            Logs.get_logger().error(f"Error en la ejecución del detector de personas: {e}", extra=__info__)
            super().critical_error(e, "_run")

    def _process_frame(self, frame):
        self._person_count = 0  # Reiniciar el contador para el próximo frame
        pred = self._detect(frame)

        if pred is not None and len(pred) > 0:
            det = pred  # Todas las detecciones
            det[:, :4] = xyxy2xywh(det[:, :4])  # Convertir coordenadas a xywh

            # Ajustar manualmente las coordenadas a la escala de la imagen
            h, w, _ = frame.shape

            xywh = det[:, :4].tolist()
            labels = det[:, 5].int().tolist()
            confidences = det[:, 4].tolist()

            for label, confidence, bbox in zip(labels, confidences, xywh):
                object_name = self._classes[label]
                # print(f"Object detected: {object_name}, Confidence: {confidence:.2f}, Bounding Box: {bbox}")
                self._draw_bounding_box(frame, bbox, object_name, confidence)

            self._count_people(labels)
            self._smooth_people_count()

            # Mostrar el frame con las detecciones
            if self._show_image:
                cv2.imshow("YOLOv5 Object Detection", frame)

                # Salir al presionar 'q'
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop()

    def _detect(self, frame):
        # Convertir a RGB si es necesario
        if frame.shape[-1] != 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

        frame = self._resize_to_divisible(frame)

        img = torch.from_numpy(frame).to(self._device)
        img = img.float() / 255.0
        img = img.permute(2, 0, 1).unsqueeze(0)  # Cambiar el orden de los canales y agregar dimensión batch

        pred = self._model(img)[0]
        pred = non_max_suppression(pred, self.CONF_THRESHOLD, self.IOU_THRESHOLD)[0]

        return pred

    @staticmethod
    def _resize_to_divisible(frame, divisor: int = 32 ):
        new_height = math.ceil(frame.shape[0] / divisor) * divisor
        new_width = math.ceil(frame.shape[1] / divisor) * divisor
        frame_resized = cv2.resize(frame, (new_width, new_height))
        return frame_resized

    @staticmethod
    def _draw_bounding_box(frame, bbox, label, confidence):
        if label == "person":
            x, y, w, h = bbox
            x1, y1, x2, y2 = int(x - w / 2), int(y - h / 2), int(x + w / 2), int(y + h / 2)

            # Dibujar el bounding box en la imagen
            cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)
            cv2.putText(frame, f"{label}: {confidence:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

    def _count_people(self, labels):
        person_count = sum(1 for label in labels if self._classes[label].lower() == 'person')
        self._person_count += person_count

    def _smooth_people_count(self):
        self._smoothed_person_count = (
            self.FILTER_FACTOR * self._smoothed_person_count
            + (1 - self.FILTER_FACTOR) * self._person_count
        )

    def get_current_people(self):
        return round(self._smoothed_person_count)


class PeopleCounterSingleton:
    __instance = None

    def __new__(cls):
        if PeopleCounterSingleton.__instance is None:
            PeopleCounterSingleton.__instance = _PeopleCounter()
        return PeopleCounterSingleton.__instance
