"""GPU memory monitoring to prevent OOM during heavy PDF processing."""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger("omniparser.gpu")


class GPUMonitor:
    """Periodically check GPU memory and expose a safe-to-proceed flag.

    Uses ``pynvml`` when available; degrades gracefully to a no-op on
    CPU-only machines.
    """

    def __init__(self, limit_mb: int = 14000, interval_sec: int = 2) -> None:
        self._limit_mb = limit_mb
        self._interval = interval_sec
        self._available = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._used_mb: float = 0.0
        self._total_mb: float = 0.0
        self._init_nvml()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def gpu_available(self) -> bool:
        return self._available

    @property
    def used_mb(self) -> float:
        return self._used_mb

    @property
    def free_mb(self) -> float:
        return max(0.0, self._total_mb - self._used_mb)

    def is_safe(self) -> bool:
        """Return True if current GPU usage is below the configured limit."""
        if not self._available:
            return True  # no GPU → no OOM risk from GPU
        return self._used_mb < self._limit_mb

    def start(self) -> None:
        """Start background monitoring thread."""
        if not self._available:
            logger.info("No NVIDIA GPU detected — GPU monitor disabled")
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info(
            "GPU monitor started (limit=%dMB, interval=%ds)",
            self._limit_mb, self._interval,
        )

    def stop(self) -> None:
        """Stop background monitoring thread."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._shutdown_nvml()

    def wait_until_safe(self, timeout: float = 120) -> bool:
        """Block until GPU memory drops below the limit or *timeout* elapses."""
        if not self._available or self.is_safe():
            return True
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.is_safe():
                return True
            time.sleep(self._interval)
        logger.warning("GPU memory did not drop below %dMB within %.0fs", self._limit_mb, timeout)
        return False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _init_nvml(self) -> None:
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            self._total_mb = info.total / (1024 * 1024)
            self._available = True
            logger.info("NVML initialised — GPU total memory: %.0fMB", self._total_mb)
        except Exception:
            self._available = False

    def _shutdown_nvml(self) -> None:
        if self._available:
            try:
                import pynvml
                pynvml.nvmlShutdown()
            except Exception:
                pass

    def _loop(self) -> None:
        try:
            import pynvml
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            return

        while not self._stop.is_set():
            try:
                info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                self._used_mb = info.used / (1024 * 1024)
                if self._used_mb > self._limit_mb:
                    logger.warning(
                        "GPU memory high: %.0f / %.0f MB (limit %d MB)",
                        self._used_mb, self._total_mb, self._limit_mb,
                    )
            except Exception:
                pass
            self._stop.wait(self._interval)
