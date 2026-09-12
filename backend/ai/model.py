"""
AI Model Management Module
Handles PyTorch model loading, inference, and caching for the detection system.
"""

import os
import sys
import torch
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Model paths
MODELS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'models')
DEFAULT_DETECTION_MODEL = 'yolov5s'  # You can change to yolov5m, yolov5l, etc.

# Cache for loaded models
_model_cache: Dict[str, Any] = {}


class ModelConfig:
    """Configuration for model inference."""

    def __init__(self, device: str = None, confidence_threshold: float = 0.45,
                 iou_threshold: float = 0.45, img_size: int = 640):
        """
        Initialize model configuration.

        Args:
            device: 'cuda' or 'cpu'. Auto-detects if None.
            confidence_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
            img_size: Input image size for model
        """
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.img_size = img_size

    def __repr__(self):
        return (f"ModelConfig(device={self.device}, conf={self.confidence_threshold}, "
                f"iou={self.iou_threshold}, img_size={self.img_size})")


class DetectionModel:
    """Wrapper for detection model inference."""

    def __init__(self, model_name: str = DEFAULT_DETECTION_MODEL, config: ModelConfig = None):
        """
        Initialize detection model.

        Args:
            model_name: Model name (e.g., 'yolov5s', 'yolov5m')
            config: ModelConfig instance or None for defaults
        """
        self.model_name = model_name
        self.config = config or ModelConfig()
        self.model = None
        self.classes = None

        self._load_model()

    def _load_model(self):
        """Load the detection model."""
        try:
            # Check cache first
            if self.model_name in _model_cache:
                logger.info(f"Loading {self.model_name} from cache")
                self.model = _model_cache[self.model_name]
                return

            logger.info(f"Loading {self.model_name} model from PyTorch Hub")

            # Load YOLOv5 from PyTorch Hub
            self.model = torch.hub.load('ultralytics/yolov5', self.model_name, pretrained=True)
            self.model.to(self.config.device)
            self.model.eval()

            # Cache the model
            _model_cache[self.model_name] = self.model

            # Get class names
            self.classes = self.model.names if hasattr(self.model, 'names') else None

            logger.info(f"Successfully loaded {self.model_name} on {self.config.device}")

        except Exception as e:
            logger.error(f"Error loading model {self.model_name}: {e}")
            raise

    def predict(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Run inference on an image file.

        Args:
            image_path: Path to image file

        Returns:
            List of detections with class, confidence, bbox
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")

        try:
            results = self.model(image_path, size=self.config.img_size)
            return self._parse_results(results)

        except Exception as e:
            logger.error(f"Error during inference: {e}")
            return []

    def predict_array(self, image_array: np.ndarray) -> List[Dict[str, Any]]:
        """
        Run inference on a numpy image array.

        Args:
            image_array: Image as numpy array (H, W, C or H, W)

        Returns:
            List of detections with class, confidence, bbox
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")

        try:
            results = self.model(image_array, size=self.config.img_size)
            return self._parse_results(results)

        except Exception as e:
            logger.error(f"Error during inference: {e}")
            return []

    def _parse_results(self, results) -> List[Dict[str, Any]]:
        """
        Parse YOLOv5 results into standardized format.

        Args:
            results: YOLOv5 results object

        Returns:
            List of detection dictionaries
        """
        detections = []

        try:
            # Extract predictions
            predictions = results.xyxy[0].cpu().numpy()  # x1, y1, x2, y2, conf, class

            for pred in predictions:
                x1, y1, x2, y2, conf, class_id = pred
                conf = float(conf)

                # Filter by confidence threshold
                if conf < self.config.confidence_threshold:
                    continue

                class_id = int(class_id)
                class_name = self.classes[class_id] if self.classes else f"class_{class_id}"

                # Convert to bbox format (x, y, width, height)
                width = float(x2 - x1)
                height = float(y2 - y1)

                detection = {
                    'class': class_name,
                    'class_id': class_id,
                    'confidence': conf,
                    'bbox': {
                        'x': float(x1),
                        'y': float(y1),
                        'width': width,
                        'height': height,
                        'x1': float(x1),
                        'y1': float(y1),
                        'x2': float(x2),
                        'y2': float(y2)
                    }
                }

                detections.append(detection)

        except Exception as e:
            logger.error(f"Error parsing results: {e}")

        return detections

    def update_config(self, **kwargs):
        """
        Update model configuration.

        Args:
            **kwargs: Configuration parameters to update
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated config: {key}={value}")

    def clear_cache():
        """Clear model cache."""
        global _model_cache
        _model_cache.clear()
        logger.info("Model cache cleared")


class TinyFaceDetector:
    """Specialized face detection model (TinyFaceDetector)."""

    def __init__(self, model_path: Optional[str] = None, config: ModelConfig = None):
        """
        Initialize face detection model.

        Args:
            model_path: Path to model weights or None for default location
            config: ModelConfig instance
        """
        self.config = config or ModelConfig()
        self.model_path = model_path or os.path.join(MODELS_DIR, 'tiny_face_detector_model-weights_manifest.json')
        self.model = None

        self._load_model()

    def _load_model(self):
        """Load the face detection model."""
        try:
            # For TinyFaceDetector, we would typically load it using TensorFlow.js or ONNX
            # For now, we'll create a placeholder that can be customized
            logger.info(f"Loading TinyFaceDetector from {self.model_path}")
            # TODO: Implement actual model loading based on your setup
            self.model = None  # Placeholder

        except Exception as e:
            logger.error(f"Error loading face model: {e}")

    def detect_faces(self, image_array: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces in image.

        Args:
            image_array: Image as numpy array

        Returns:
            List of face detections
        """
        if self.model is None:
            logger.warning("Face model not loaded, returning empty detections")
            return []

        # TODO: Implement face detection logic
        return []


class ModelPool:
    """Manages multiple detection models for different purposes."""

    def __init__(self):
        """Initialize model pool."""
        self.models: Dict[str, DetectionModel] = {}
        self.config = ModelConfig()

    def get_model(self, model_name: str = DEFAULT_DETECTION_MODEL) -> DetectionModel:
        """
        Get or create a model instance.

        Args:
            model_name: Name of model

        Returns:
            DetectionModel instance
        """
        if model_name not in self.models:
            self.models[model_name] = DetectionModel(model_name, self.config)

        return self.models[model_name]

    def predict(self, image_path: str, model_name: str = DEFAULT_DETECTION_MODEL) -> List[Dict[str, Any]]:
        """
        Get predictions using specified model.

        Args:
            image_path: Path to image
            model_name: Model name

        Returns:
            List of detections
        """
        model = self.get_model(model_name)
        return model.predict(image_path)

    def predict_array(self, image_array: np.ndarray, model_name: str = DEFAULT_DETECTION_MODEL) -> List[Dict[str, Any]]:
        """
        Get predictions on image array.

        Args:
            image_array: Image as numpy array
            model_name: Model name

        Returns:
            List of detections
        """
        model = self.get_model(model_name)
        return model.predict_array(image_array)

    def update_config(self, **kwargs):
        """
        Update configuration for all models.

        Args:
            **kwargs: Configuration parameters
        """
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        # Update all loaded models
        for model in self.models.values():
            model.update_config(**kwargs)


# Global model pool instance
_model_pool: Optional[ModelPool] = None


def get_model_pool() -> ModelPool:
    """Get or create global model pool."""
    global _model_pool
    if _model_pool is None:
        _model_pool = ModelPool()
    return _model_pool


def predict_image(image_path: str, model_name: str = DEFAULT_DETECTION_MODEL) -> List[Dict[str, Any]]:
    """
    Quick prediction on image file.

    Args:
        image_path: Path to image
        model_name: Model name

    Returns:
        List of detections
    """
    pool = get_model_pool()
    return pool.predict(image_path, model_name)


def predict_array(image_array: np.ndarray, model_name: str = DEFAULT_DETECTION_MODEL) -> List[Dict[str, Any]]:
    """
    Quick prediction on image array.

    Args:
        image_array: Image as numpy array
        model_name: Model name

    Returns:
        List of detections
    """
    pool = get_model_pool()
    return pool.predict_array(image_array, model_name)


def set_inference_device(device: str = 'cuda'):
    """
    Set inference device for all models.

    Args:
        device: 'cuda' or 'cpu'
    """
    pool = get_model_pool()
    pool.update_config(device=device)
    logger.info(f"Inference device set to {device}")


def get_available_models() -> List[str]:
    """Get list of available YOLOv5 model sizes."""
    return ['yolov5n', 'yolov5s', 'yolov5m', 'yolov5l', 'yolov5x']


def benchmark_model(model_name: str = DEFAULT_DETECTION_MODEL) -> Dict[str, float]:
    """
    Benchmark model performance.

    Args:
        model_name: Model name

    Returns:
        Benchmark results
    """
    try:
        model = DetectionModel(model_name)

        # Create dummy image
        dummy_image = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)

        # Warm up
        model.predict_array(dummy_image)

        # Benchmark
        import time
        start = time.time()
        for _ in range(10):
            model.predict_array(dummy_image)
        elapsed = time.time() - start

        fps = 10 / elapsed
        latency = elapsed / 10

        return {
            'model': model_name,
            'device': model.config.device,
            'fps': fps,
            'latency_ms': latency * 1000
        }

    except Exception as e:
        logger.error(f"Error benchmarking model: {e}")
        return {}
