"""Collector modülleri için testler.

CPU, Memory, Disk, Network ve Process testleri gerçek sistem
çağrıları yapar (live unit test).  Services testlerinde
``subprocess.run`` mock'lanır.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from collectors import cpu, disk, memory, network, process, services
from models import (
    CpuMetrics,
    DiskMetrics,
    MemoryMetrics,
    NetworkMetrics,
    ProcessInfo,
    ServiceStatus,
)

# ── CPU ──────────────────────────────────────────────────────────────


class TestCpuCollector:
    """CPU collector testleri (live)."""

    def test_returns_cpu_metrics_model(self) -> None:
        result = cpu.collect()
        assert isinstance(result, CpuMetrics)

    def test_percent_in_valid_range(self) -> None:
        result = cpu.collect()
        assert 0.0 <= result.percent <= 100.0

    def test_per_core_is_nonempty_list(self) -> None:
        result = cpu.collect()
        assert len(result.per_core) > 0
        assert all(0.0 <= v <= 100.0 for v in result.per_core)

    def test_load_averages_are_non_negative(self) -> None:
        result = cpu.collect()
        assert result.load_avg_1 >= 0.0
        assert result.load_avg_5 >= 0.0
        assert result.load_avg_15 >= 0.0


# ── Memory ───────────────────────────────────────────────────────────


class TestMemoryCollector:
    """Memory collector testleri (live)."""

    def test_returns_memory_metrics_model(self) -> None:
        result = memory.collect()
        assert isinstance(result, MemoryMetrics)

    def test_total_bytes_positive(self) -> None:
        result = memory.collect()
        assert result.total_bytes > 0

    def test_percent_in_valid_range(self) -> None:
        result = memory.collect()
        assert 0.0 <= result.percent <= 100.0

    def test_used_does_not_exceed_total(self) -> None:
        result = memory.collect()
        assert result.used_bytes <= result.total_bytes

    def test_swap_fields_non_negative(self) -> None:
        result = memory.collect()
        assert result.swap_total_bytes >= 0
        assert result.swap_used_bytes >= 0


# ── Disk ─────────────────────────────────────────────────────────────


class TestDiskCollector:
    """Disk collector testleri (live)."""

    def test_returns_list_of_disk_metrics(self) -> None:
        result = disk.collect()
        assert isinstance(result, list)
        assert all(isinstance(d, DiskMetrics) for d in result)

    def test_at_least_one_partition(self) -> None:
        result = disk.collect()
        assert len(result) >= 1

    def test_root_partition_present(self) -> None:
        result = disk.collect()
        paths = [d.path for d in result]
        assert "/" in paths

    def test_usage_fields_consistent(self) -> None:
        result = disk.collect()
        for d in result:
            assert d.total_bytes > 0
            assert d.used_bytes + d.free_bytes <= d.total_bytes
            assert 0.0 <= d.percent <= 100.0

    def test_io_rates_non_negative(self) -> None:
        result = disk.collect()
        for d in result:
            assert d.read_bytes_per_sec >= 0.0
            assert d.write_bytes_per_sec >= 0.0


# ── Network ──────────────────────────────────────────────────────────


class TestNetworkCollector:
    """Network collector testleri (live)."""

    def test_returns_list_of_network_metrics(self) -> None:
        result = network.collect()
        assert isinstance(result, list)
        assert all(isinstance(n, NetworkMetrics) for n in result)

    def test_loopback_filtered(self) -> None:
        result = network.collect()
        interfaces = [n.interface for n in result]
        assert "lo" not in interfaces

    def test_rate_fields_non_negative(self) -> None:
        result = network.collect()
        for n in result:
            assert n.bytes_sent_per_sec >= 0.0
            assert n.bytes_recv_per_sec >= 0.0
            assert n.packets_sent_per_sec >= 0.0
            assert n.packets_recv_per_sec >= 0.0

    def test_error_fields_non_negative(self) -> None:
        result = network.collect()
        for n in result:
            assert n.errors_in >= 0
            assert n.errors_out >= 0


# ── Process ──────────────────────────────────────────────────────────


class TestProcessCollector:
    """Process collector testleri (live)."""

    def test_returns_list_of_process_info(self) -> None:
        result = process.collect()
        assert isinstance(result, list)
        assert all(isinstance(p, ProcessInfo) for p in result)

    def test_respects_top_n_limit(self) -> None:
        result = process.collect()
        assert len(result) <= 10

    def test_sorted_by_cpu_descending(self) -> None:
        result = process.collect()
        cpu_vals = [p.cpu_percent for p in result]
        assert cpu_vals == sorted(cpu_vals, reverse=True)

    def test_required_fields_populated(self) -> None:
        result = process.collect()
        for p in result:
            assert p.pid > 0
            assert isinstance(p.name, str)
            assert isinstance(p.status, str)


# ── Services ─────────────────────────────────────────────────────────


class TestServicesCollector:
    """Services collector testleri (subprocess mock'lu)."""

    def _mock_systemctl_output(self, active: str, sub: str, ts: str) -> str:
        return f"ActiveState={active}\nSubState={sub}\nActiveEnterTimestamp={ts}\n"

    def test_returns_list_of_service_status(self, mocker: pytest.fixture) -> None:
        mock_run = mocker.patch("collectors.services.subprocess.run")
        mock_run.return_value = MagicMock(
            stdout=self._mock_systemctl_output("active", "running", ""),
            returncode=0,
        )

        result = services.collect(["nginx"])
        assert len(result) == 1
        assert isinstance(result[0], ServiceStatus)

    def test_active_service_fields(self, mocker: pytest.fixture) -> None:
        mock_run = mocker.patch("collectors.services.subprocess.run")
        mock_run.return_value = MagicMock(
            stdout=self._mock_systemctl_output("active", "running", ""),
            returncode=0,
        )

        result = services.collect(["nginx"])
        svc = result[0]
        assert svc.name == "nginx"
        assert svc.status == "active"
        assert svc.sub_state == "running"

    def test_failed_service(self, mocker: pytest.fixture) -> None:
        mock_run = mocker.patch("collectors.services.subprocess.run")
        mock_run.return_value = MagicMock(
            stdout=self._mock_systemctl_output("failed", "failed", ""),
            returncode=0,
        )

        result = services.collect(["broken"])
        assert result[0].status == "failed"

    def test_timeout_returns_unknown(self, mocker: pytest.fixture) -> None:
        import subprocess as sp

        mock_run = mocker.patch("collectors.services.subprocess.run")
        mock_run.side_effect = sp.TimeoutExpired(cmd="systemctl", timeout=5)

        result = services.collect(["slow-svc"])
        assert result[0].status == "unknown"
        assert result[0].sub_state == "unknown"

    def test_multiple_services(self, mocker: pytest.fixture) -> None:
        mock_run = mocker.patch("collectors.services.subprocess.run")
        mock_run.return_value = MagicMock(
            stdout=self._mock_systemctl_output("active", "running", ""),
            returncode=0,
        )

        result = services.collect(["nginx", "docker", "postgresql"])
        assert len(result) == 3
        assert mock_run.call_count == 3
