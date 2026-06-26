"""
LLM client using llama-cpp-python for local inference.

Implements the LLMPort protocol with Llama 3.2 3B (Q4_K_M GGUF).
All blocking C++ calls are wrapped in asyncio.to_thread to keep
the event loop responsive.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LlamaLLMClient:
    """Local LLM client backed by llama-cpp-python."""

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 2048,
        n_threads: int = 4,
    ) -> None:
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self._llama: Optional[object] = None

    async def _ensure_loaded(self) -> None:
        """Lazy-load the model on first use."""
        if self._llama is not None:
            return
        try:
            from llama_cpp import Llama  # type: ignore[import-untyped]

            logger.info("Loading LLM from %s (n_ctx=%d)", self.model_path, self.n_ctx)
            self._llama = await asyncio.to_thread(
                Llama,
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False,
            )
            logger.info("LLM loaded successfully.")
        except Exception as exc:
            logger.error("Failed to load LLM: %s", exc, exc_info=True)
            raise

    def _build_prompt(self, prompt: str, system: str) -> str:
        """Build a ChatML-style prompt string."""
        parts: list[str] = []
        if system:
            parts.append(f"<|im_start|>system\n{system}<|im_end|>")
        parts.append(f"<|im_start|>user\n{prompt}<|im_end|>")
        parts.append("<|im_start|>assistant\n")
        return "\n".join(parts)

    async def generate(
        self,
        prompt: str,
        *,
        system: str = "",
        max_tokens: int = 512,
        temperature: float = 0.7,
        stop: list[str] | None = None,
    ) -> str:
        """Generate a completion for the given prompt.

        Satisfies the ``LLMPort`` protocol.
        """
        await self._ensure_loaded()
        full_prompt = self._build_prompt(prompt, system)
        stop_sequences = stop or ["<|im_end|>"]

        try:
            result = await asyncio.to_thread(
                self._llama.create_completion,  # type: ignore[union-attr]
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop_sequences,
            )
            text: str = result["choices"][0]["text"].strip()  # type: ignore[index]
            return text
        except Exception as exc:
            logger.error("LLM generation failed: %s", exc, exc_info=True)
            return "I'm sorry, I couldn't process that right now."
