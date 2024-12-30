__author__ = "Jose David Escribano Orts"
__subsystem__ = "PeopleDetector"
__module__ = "peopleCounter"
__version__ = "0.1"
__info__ = {"subsystem": __subsystem__, "module_name": __module__, "version": __version__}

import os
import cv2
import torch
import time
import yaml

from picamera2 import Picamera2
from ultralytics import YOLO

from tfm_muaii_rpi4.Environment.env import EnvSingleton
from tfm_muaii_rpi4.DataPersistence.contextVarsMgr import ContextVarsMgrSingleton, ContextVarsConst
from tfm_muaii_rpi4.Logger.logger import LogsSingleton
from tfm_muaii_rpi4.Utils.utils import Service

Logs = LogsSingleton()


class ImageDetectionConfig:
    # Tamaño para capturar la imagen para que se utilice completamente el sensor óptico
    ORIGINAL_WIDTH = 1640
    ORIGINAL_HEIGHT = 1232
    ORIGINAL_SIZE = (ORIGINAL_WIDTH, ORIGINAL_HEIGHT)

    # Tamaño adaptado para mejorar rendimiento
    NEW_WIDTH = 480
    NEW_HEIGHT = 480
    NEW_SIZE = (NEW_WIDTH, NEW_HEIGHT)

    # Formato de imagen
    FORMAT = "RGB888"

    # Límite inferior de confianza en las detecciones
    CONF_THRESHOLD: float = 0.04

    # Límite inferior para eliminar detecciones redundantes
    IOU_THRESHOLD: float = 0.5

    # Factor de filtro
    FILTER_FACTOR: float = 0.8

    # Fuente de texto
    TEXT_FONT = cv2.FONT_HERSHEY_SIMPLEX


class _PeopleCounter(Service):

    def __init__(self, show_image=False):
        super().__init__(__info__, is_thread=True)
        self._env = EnvSingleton()
        self._context_vars_mgr = ContextVarsMgrSingleton()

        self.__smoothed_person_count: int = 0  # Inicializar el contador suavizado
        self.__show_image: bool = show_image
        self.__classes: dict = {}
        self.__load_yolo_model()
        self.__init_camara()
        self.__load_yaml()

        self.sleep_period = 0.5

    def __load_yolo_model(self):
        model_path = self._env.get_path(self._env.yolo_models_path)
        model_file = os.path.join(model_path, "yolo11n.pt")
        ncnn_model_file = os.path.join(model_path, "yolo11n_ncnn_model")
        if not os.path.exists(ncnn_model_file):
            if not os.path.exists(model_file):
                raise Exception("No se encontro la versión nano de YOLOv11: yolo11n.pt")
            Logs.get_logger().warning("Modelo NCNN de YOLOv11 no encontrado, exportando para optimizar rendimiento", extra=__info__)
            time1 = time.time()
            tmp_model = YOLO(model_file)
            tmp_model.export(format="ncnn", imgsz=ImageDetectionConfig.NEW_HEIGHT)
            Logs.get_logger().warning(f"Modelo NCNN exportado correctamente tras {time.time() - time1} segundos",
                                      extra=__info__)
        self.__model = YOLO(ncnn_model_file, task="detect")
        Logs.get_logger().info("Modelo NCNN de YOLOv11 cargado correctamente", extra=__info__)

    def __init_camara(self):
        try:
            Logs.get_logger().info("Cargando cámara Picamera V2", extra=__info__)
            self.__camera = Picamera2()
            camera_config = self.__camera.create_preview_configuration(
                main={
                    "size": ImageDetectionConfig.ORIGINAL_SIZE,
                    "format": ImageDetectionConfig.FORMAT
                }
            )
            self.__camera.configure(camera_config)
            Logs.get_logger().info("Picamera V2 cargada y configurada correctamente", extra=__info__)
        except Exception as e:
            super().critical_error(e, "init")

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
                    super().sleep_period()
                    continue
                frame = cv2.flip(frame, 0)
                annotated_frame = self.__process_frame(frame)
                if self.__show_image:
                    cv2.imshow("TFM David - Object Detection", annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        self.stop()
                super().sleep_period()
        except Exception as e:
            Logs.get_logger().error(f"Error en el run del detector de personas: {e}", extra=__info__)
            super().critical_error(e, "_run")

    def run_test_images(self):
        try:
            image_folder = self._env.get_path(self._env.images_test_path)
            image_files = [image for image in os.listdir(image_folder) if image.endswith(('.jpg', '.png', '.jpeg'))]

            for image_file in image_files:
                image_path = os.path.join(image_folder, image_file)
                results = self.__model.predict(image_path, verbose=False, imgsz=ImageDetectionConfig.NEW_HEIGHT,
                                               conf=ImageDetectionConfig.CONF_THRESHOLD,
                                               iou=ImageDetectionConfig.IOU_THRESHOLD,
                                               classes=list(self.__classes.keys()), show=True)
                print(f"Personas detectadas en {image_file}: {len(results[0])}")

        except Exception as e:
            Logs.get_logger().error(f"Error en la ejecución del TEST de detección de personas: {e}", extra=__info__)
            super().critical_error(e, "_run")

    def __process_frame(self, frame):
        results = self.__model.track(frame, verbose=False, persist=True, imgsz=ImageDetectionConfig.NEW_HEIGHT,
                                     conf=ImageDetectionConfig.CONF_THRESHOLD, iou=ImageDetectionConfig.IOU_THRESHOLD,
                                     classes=list(self.__classes.keys()))
        detection_results = results[0]
        if detection_results is None:
            Logs.get_logger().warning("No se ha obtenido ningún resultado en la detección de personas")
            return
        annotated_frame = detection_results.plot()
        person_count = len(detection_results)
        inference_time = detection_results.speed['inference']
        fps = 1000 / inference_time
        Logs.get_logger().debug(f"{fps:.1f} FPS - Detectadas {person_count} personas", extra=__info__)
        if self.__show_image:
            fps_text = f"FPS: {fps:.1f}"
            text_size = cv2.getTextSize(fps_text, ImageDetectionConfig.TEXT_FONT, 1, 2)[0]
            text_x = annotated_frame.shape[1] - text_size[0] - 10 # 10 pixeles de margen de la esquina superior derecha
            text_y = text_size[1] + 10
            cv2.putText(annotated_frame, fps_text, (text_x, text_y), ImageDetectionConfig.TEXT_FONT, 1, (255, 255, 255), 2, cv2.LINE_AA)
        self.__update_people_count(person_count)
        return annotated_frame

    def __update_people_count(self, person_count):
        current_smoothed_count = self.get_current_people()
        if current_smoothed_count == 0:  # Se le da mayor importancia a las nuevas personas detectadas
            self.__smoothed_person_count = (
                (1 - ImageDetectionConfig.FILTER_FACTOR) * self.__smoothed_person_count + ImageDetectionConfig.FILTER_FACTOR * person_count
            )
        else: # Se le da mayor importancia a las personas anteriormente detectadas
            self.__smoothed_person_count = (
                    ImageDetectionConfig.FILTER_FACTOR * self.__smoothed_person_count + (1 - ImageDetectionConfig.FILTER_FACTOR) * person_count
            )
        Logs.get_logger().info(f"Actualizando contador de personas suavizado: {current_smoothed_count} -> {self.get_current_people()}",
                               extra=__info__)
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


if __name__ == "__main__":
    people_counter = PeopleCounterSingleton()
    people_counter.start()
    people_counter.run_test_images()