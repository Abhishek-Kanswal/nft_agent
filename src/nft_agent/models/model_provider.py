import os
import asyncio
import logging
from typing import AsyncGenerator, Any

from dotenv import load_dotenv

log = logging.getLogger(__name__)
load_dotenv()

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None
    log.debug("google.generativeai not available")

class ModelProvider:
    def __init__(self):
        self.provider = "gemini"
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Missing GEMINI_API_KEY in environment variables.")
        if genai is None:
            raise RuntimeError("google.generativeai SDK not installed in the venv.")

        # Configure Gemini and create a model client
        genai.configure(api_key=self.api_key)
        # Use GenerativeModel as in your working example
        try:
            self.client = genai.GenerativeModel(self.model)
        except Exception:
            # some SDK versions expose models differently; keep client None to fail gracefully later
            self.client = None
            log.warning("Unable to construct GenerativeModel client for model=%s", self.model)
        log.info("ModelProvider init provider=%s model=%s", self.provider, self.model)

    async def generate(self, prompt: str) -> str:
        """Return full text response using Gemini async API."""
        if self.client is None:
            return "FALLBACK: Gemini client unavailable."

        try:
            # call SDK async method if available
            coro = getattr(self.client, "generate_content_async", None)
            if coro and asyncio.iscoroutinefunction(coro):
                resp = await coro(prompt)
                # Many SDK responses expose .text or .candidates; prefer .text
                text = getattr(resp, "text", None)
                if text is None:
                    # try common shapes
                    if hasattr(resp, "candidates") and resp.candidates:
                        first = resp.candidates[0]
                        text = getattr(first, "content", getattr(first, "text", str(first)))
                return (text or "").strip()
            # fallback: try sync method in executor
            sync_call = getattr(self.client, "generate_content", None) or getattr(self.client, "generate", None)
            if sync_call:
                loop = asyncio.get_running_loop()
                resp = await loop.run_in_executor(None, sync_call, prompt)
                text = getattr(resp, "text", None)
                if text is None and isinstance(resp, dict):
                    # dict response shapes
                    if "candidates" in resp and resp["candidates"]:
                        cand = resp["candidates"][0]
                        text = cand.get("content") or cand.get("text")
                return (text or "").strip()
        except Exception as e:
            log.exception("Gemini generate failed: %s", e)
        return "FALLBACK: Could not contact Gemini model."

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Yield chunks from the full Gemini response (emulated streaming)."""
        full = await self.generate(prompt)
        if not full:
            return
        # Yield in modest chunks so callers can consume progressively
        chunk_size = 256
        for i in range(0, len(full), chunk_size):
            await asyncio.sleep(0)  # yield control
            yield full[i : i + chunk_size]
