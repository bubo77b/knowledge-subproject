"""Tests for omniparser.gpu_monitor."""

from omniparser.gpu_monitor import GPUMonitor


class TestGPUMonitor:
    def test_no_gpu_is_safe(self):
        """On a machine without NVIDIA GPU, is_safe() should return True."""
        mon = GPUMonitor(limit_mb=14000)
        assert mon.is_safe() is True

    def test_no_gpu_free_mb(self):
        mon = GPUMonitor()
        assert mon.free_mb == 0.0

    def test_start_stop_without_gpu(self):
        mon = GPUMonitor()
        mon.start()
        mon.stop()

    def test_wait_until_safe_without_gpu(self):
        mon = GPUMonitor()
        assert mon.wait_until_safe(timeout=1) is True
