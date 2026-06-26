"""
Wake word detection package using openWakeWord.
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import openwakeword

logger = logging.getLogger(__name__)


class WakeWordDetector:
    def __init__(
        self,
        wake_word: str = "Hello Puppy",
        model_path: Optional[str] = None,
        threshold: float = 0.5,
    ) -> None:
        self.wake_word = wake_word
        self.threshold = threshold

        # Attempt to load custom model path if specified or hello_puppy.onnx
        resolved_model_path = model_path
        if resolved_model_path is None and wake_word == "Hello Puppy":
            potential_path = Path("models/hello_puppy.onnx")
            if potential_path.exists():
                resolved_model_path = str(potential_path)

        if resolved_model_path and Path(resolved_model_path).exists():
            logger.info("Loading custom wake word model from %s", resolved_model_path)
            self._model = openwakeword.model.Model(
                wakeword_models=[resolved_model_path],
                inference_framework="onnx",
            )
            # Custom model name is usually the file name without extension
            self.model_name = Path(resolved_model_path).stem
        else:
            if wake_word == "Hello Puppy":
                logger.warning(
                    "Custom wake word model not found at models/hello_puppy.onnx. "
                    "Falling back to built-in 'alexa' ONNX model."
                )
            # Fall back to alexa built-in model
            self._model = openwakeword.model.Model(
                wakeword_models=["alexa"],
                inference_framework="onnx",
            )
            self.model_name = "alexa"

        logger.info("WakeWordDetector initialized with model: %s", self.model_name)

    def predict(self, audio_chunk: bytes) -> float:
        """
        Predict if the wake word is present in the audio chunk.
        audio_chunk: raw 16-bit PCM mono 16kHz audio.
        Returns the prediction confidence score (0.0 to 1.0).
        """
        if not audio_chunk:
            return 0.0

        try:
            # Convert raw PCM bytes to int16 numpy array
            audio_np = np.frombuffer(audio_chunk, dtype=np.int16)

            # openwakeword model.predict expects int16 numpy array.
            # It handles buffering internally.
            predictions = self._model.predict(audio_np)

            # predictions is a dictionary containing model scores, e.g., {'alexa': 0.02}
            score = predictions.get(self.model_name, 0.0)
            return float(score)
        except Exception as e:
            logger.error("Error predicting wake word: %s", e, exc_info=True)
            return 0.0
