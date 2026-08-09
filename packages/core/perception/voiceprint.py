"""
Voiceprint speaker embedding encoder for FamilyRobot.

Extracts normalized 192-dimensional speaker acoustic embeddings from 16kHz PCM audio bytes
for zero-touch identity resolution.
"""

from __future__ import annotations

import logging
import math
import os
import struct
from typing import Optional

logger = logging.getLogger(__name__)

# Expected embedding dimension (standard ECAPA-TDNN vector size)
EMBEDDING_DIM = 192


class VoiceprintEncoder:
    """Extracts speaker voiceprint embeddings from audio chunks.

    Uses an ONNX ECAPA-TDNN model if available on disk, or falls back to
    deterministic spectral feature extraction (for offline/CPU testing).
    """

    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = model_path or "models/ecapa_tdnn.onnx"
        self._session = None
        self._input_name = None

        if os.path.exists(self.model_path):
            try:
                import onnxruntime as ort

                self._session = ort.InferenceSession(self.model_path)
                self._input_name = self._session.get_inputs()[0].name
                logger.info("Loaded Voiceprint ONNX model from %s", self.model_path)
            except Exception as exc:
                logger.warning(
                    "Failed to initialize ONNX session for voiceprint (%s). "
                    "Falling back to spectral feature extraction.",
                    exc,
                )

    def encode(self, audio_bytes: bytes) -> list[float]:
        """Extract a normalized 192-dimensional speaker embedding from PCM audio.

        Args:
            audio_bytes: Raw 16kHz 16-bit mono PCM audio bytes.

        Returns:
            A unit-normalized list of 192 float features.
        """
        if not audio_bytes or len(audio_bytes) < 320:  # <10ms of audio
            return [0.0] * EMBEDDING_DIM

        # Parse 16-bit PCM samples
        sample_count = len(audio_bytes) // 2
        try:
            samples = struct.unpack(f"<{sample_count}h", audio_bytes[: sample_count * 2])
        except struct.error:
            return [0.0] * EMBEDDING_DIM

        # Convert to float [-1.0, 1.0]
        float_samples = [s / 32768.0 for s in samples]

        # Use ONNX session if active
        if self._session and self._input_name:
            try:
                import numpy as np

                inp = np.array([float_samples], dtype=np.float32)
                outputs = self._session.run(None, {self._input_name: inp})
                raw_emb = outputs[0].flatten().tolist()
                return self._normalize(raw_emb[:EMBEDDING_DIM])
            except Exception as exc:
                logger.debug("ONNX inference failed (%s), using spectral fallback", exc)

        # Spectral Fallback Feature Extractor:
        # Computes 192 energy & frequency bin features across frame segments
        embedding = [0.0] * EMBEDDING_DIM
        num_samples = len(float_samples)

        # 1. Basic energy & statistics
        mean_val = sum(float_samples) / num_samples
        variance = sum((x - mean_val) ** 2 for x in float_samples) / num_samples
        rms = math.sqrt(max(0.0, variance))

        # Zero crossing rate
        zcr = sum(
            1
            for i in range(1, num_samples)
            if (float_samples[i] >= 0) != (float_samples[i - 1] >= 0)
        ) / num_samples

        # 2. Divide audio into 192 sub-segment spectral energy bins
        chunk_size = max(1, num_samples // EMBEDDING_DIM)
        for i in range(EMBEDDING_DIM):
            start = i * chunk_size
            end = min(num_samples, start + chunk_size)
            segment = float_samples[start:end]
            if segment:
                seg_energy = sum(x * x for x in segment) / len(segment)
                seg_zcr = sum(
                    1
                    for k in range(1, len(segment))
                    if (segment[k] >= 0) != (segment[k - 1] >= 0)
                ) / len(segment)
                # Combine energy, zcr, and position weight
                val = seg_energy * 0.7 + seg_zcr * 0.2 + (rms * (i % 7)) * 0.1
                embedding[i] = val

        embedding[0] = rms
        embedding[1] = zcr

        return self._normalize(embedding)

    @staticmethod
    def _normalize(vec: list[float]) -> list[float]:
        """Unit-normalize vector to ensure Euclidean/Cosine distance consistency."""
        norm = math.sqrt(sum(x * x for x in vec))
        if norm == 0:
            return [0.0] * len(vec)
        return [x / norm for x in vec]
