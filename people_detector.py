import math
import time
import cv2
import torch
import yaml
from yolov5.models.experimental import attempt_load
from yolov5.utils.general import non_max_suppression, xyxy2xywh
import threading
import os
from logger import Logs


class PeopleCounter:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PeopleCounter, cls).__new__(cls)
                cls._instance._initialized = False
            else:
                Logs.get_logger().warning("Ya existe una instancia de PeopleCounter.")
        return cls._instance

    def __init__(self, model_path="yolo/models/yolov5/yolov5n.pt", class_file="yolo/classes/coco.yaml",
                 conf_threshold=0.1, iou_threshold=0.5, filter_factor=0.8, show_image=True):
        if not self._initialized:
            self._initialized: bool = True
            self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._model = attempt_load(model_path, device=self._device)
            self._model.to(self._device).eval()
            self._conf_threshold: float = conf_threshold
            self._iou_threshold: float = iou_threshold
            self._filter_factor: float = filter_factor
            self._person_count: int = 0  # Inicializar el contador de personas
            self._smoothed_person_count: int = 0  # Inicializar el contador suavizado
            self._show_image: bool = show_image
            self._classes: list = []
            self.need_stop: bool = False  # Bandera para detener el hilo

            self._load_yaml(class_file)

    def _load_yaml(self, yaml_file):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            self._classes = data["names"]

    def run(self):
        try:
            cap = cv2.VideoCapture(1)

            if not cap.isOpened():
                Logs.get_logger().error(f"No se puede abrir la cámara.")
                self.stop()

            while not self.need_stop:
                ret, frame = cap.read()
                if not ret:
                    Logs.get_logger().error("Error al leer el fotograma de la camara")
                    self.stop()
                else:
                    self._process_frame(frame)
                    #Logs.get_logger().info(f"Recuento de personas: {round(self._smoothed_person_count)}")
                time.sleep(0.5)

            cap.release()
            cv2.destroyAllWindows()
        except Exception as e:
            Logs.get_logger().error(f"Error en el run del detector de personas: {e}")

    def run_with_images(self, image_folder):
        try:
            image_files = [f for f in os.listdir(image_folder) if f.endswith(('.jpg', '.png', '.jpeg'))]

            for image_file in image_files:
                image_path = os.path.join(image_folder, image_file)
                frame = cv2.imread(image_path)

                if frame is not None:
                    self._process_frame(frame)
                    Logs.get_logger().info(f"Recuento de personas: {round(self._person_count)}")
                else:
                    Logs.get_logger().error(f"Error al leer la imagen: {image_path}")

                time.sleep(10)
            self.stop()

        except Exception as e:
            Logs.get_logger().error(f"Error en la ejecución del detector de personas: {e}")

    def stop(self):
        self.need_stop = True

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
        pred = non_max_suppression(pred, self._conf_threshold, self._iou_threshold)[0]

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
            self._filter_factor * self._smoothed_person_count
            + (1 - self._filter_factor) * self._person_count
        )

    def get_current_people(self):
        return round(self._smoothed_person_count)


if __name__ == "__main__":
    try:
        Logs.get_logger().info("--------Iniciando detector de personas--------")
        # Instanciar el detector
        detector = PeopleCounter(show_image=True)
        # Crear un hilo para ejecutar el main
        main_thread = threading.Thread(target=detector.run)
        #main_thread = threading.Thread(target=detector.run_with_images, args=('image_test',))
        # Iniciar el hilo
        main_thread.start()
        aux_current_people: int = -1
        while not detector.need_stop:
            current_people: int = detector.get_current_people()
            if current_people > 0 and current_people != aux_current_people:
                aux_current_people = current_people
                Logs.get_logger().info(f"Personas presentes en el vehiculo: {current_people}")
            time.sleep(1)

        # Esperar a que el hilo termine
        main_thread.join(timeout=60)
        Logs.get_logger().info("Hilo de detección de personas terminado")
    except Exception as e:
        Logs.get_logger().critical(f"Error al iniciar el hilo de detección de personas: {e}")

    finally:
        # Liberar recursos al finalizar
        cv2.destroyAllWindows()
