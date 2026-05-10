"""HTTP sender modülü için testler.

``monkeypatch`` ile ``httpx.post`` mock'lanarak gerçek ağ çağrısı
yapılmadan başarılı/başarısız senaryolar doğrulanır.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from tenacity import RetryError

from config import AgentConfig
from models import (
    CpuMetrics,
    MemoryMetrics,
    MetricPayload,
)
from sender.http_sender import ClientError, send_metrics


@pytest.fixture()
def agent_config() -> AgentConfig:
    """Test için minimal config."""
    return AgentConfig(
        server_id="test-server",
        backend_url="http://test-backend:8000",
        api_key="test-key",
    )


@pytest.fixture()
def sample_payload() -> MetricPayload:
    """Test için minimal payload."""
    return MetricPayload(
        server_id="test-server",
        collected_at=datetime.now(tz=UTC),
        cpu=CpuMetrics(
            percent=25.0,
            per_core=[20.0, 30.0],
            load_avg_1=0.5,
            load_avg_5=0.4,
            load_avg_15=0.3,
        ),
        memory=MemoryMetrics(
            total_bytes=8_000_000_000,
            used_bytes=4_000_000_000,
            available_bytes=4_000_000_000,
            cached_bytes=1_000_000_000,
            percent=50.0,
            swap_total_bytes=2_000_000_000,
            swap_used_bytes=0,
        ),
        disks=[],
        networks=[],
        top_processes=[],
        services=[],
        log_entries=[],
    )


def _make_response(status_code: int, **kwargs: object) -> httpx.Response:
    """Mock-safe ``httpx.Response`` — ``request`` attribute dahil."""
    request = httpx.Request("POST", "http://test-backend:8000/api/v1/metrics")
    return httpx.Response(status_code, request=request, **kwargs)


class TestSendMetricsSuccess:
    """2xx yanıtlarda başarılı gönderim."""

    def test_returns_true_on_200(
        self,
        monkeypatch: pytest.MonkeyPatch,
        agent_config: AgentConfig,
        sample_payload: MetricPayload,
    ) -> None:
        def mock_post(*args: object, **kwargs: object) -> httpx.Response:
            return _make_response(200, json={"status": "ok"})

        monkeypatch.setattr(httpx, "post", mock_post)
        assert send_metrics(sample_payload, agent_config) is True

    def test_sends_correct_url(
        self,
        monkeypatch: pytest.MonkeyPatch,
        agent_config: AgentConfig,
        sample_payload: MetricPayload,
    ) -> None:
        captured_url: str = ""

        def mock_post(url: str, **kwargs: object) -> httpx.Response:
            nonlocal captured_url
            captured_url = url
            return _make_response(200, json={"status": "ok"})

        monkeypatch.setattr(httpx, "post", mock_post)
        send_metrics(sample_payload, agent_config)
        assert captured_url == "http://test-backend:8000/api/v1/metrics"

    def test_sends_auth_header(
        self,
        monkeypatch: pytest.MonkeyPatch,
        agent_config: AgentConfig,
        sample_payload: MetricPayload,
    ) -> None:
        captured_headers: dict = {}

        def mock_post(*args: object, **kwargs: object) -> httpx.Response:
            captured_headers.update(kwargs.get("headers", {}))
            return _make_response(200, json={"status": "ok"})

        monkeypatch.setattr(httpx, "post", mock_post)
        send_metrics(sample_payload, agent_config)
        assert captured_headers["Authorization"] == "Bearer test-key"
        assert captured_headers["Content-Type"] == "application/json"


class TestSendMetricsClientError:
    """4xx yanıtlarda ClientError fırlatılır, retry yapılmaz."""

    def test_400_raises_client_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        agent_config: AgentConfig,
        sample_payload: MetricPayload,
    ) -> None:
        def mock_post(*args: object, **kwargs: object) -> httpx.Response:
            return _make_response(400, text="Bad Request")

        monkeypatch.setattr(httpx, "post", mock_post)
        with pytest.raises(ClientError, match="HTTP 400"):
            send_metrics(sample_payload, agent_config)

    def test_422_raises_client_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        agent_config: AgentConfig,
        sample_payload: MetricPayload,
    ) -> None:
        def mock_post(*args: object, **kwargs: object) -> httpx.Response:
            return _make_response(422, text="Validation Error")

        monkeypatch.setattr(httpx, "post", mock_post)
        with pytest.raises(ClientError, match="HTTP 422"):
            send_metrics(sample_payload, agent_config)


class TestSendMetricsServerError:
    """5xx yanıtlarda 3 retry sonrası RetryError fırlatılır."""

    def test_500_retries_three_times(
        self,
        monkeypatch: pytest.MonkeyPatch,
        agent_config: AgentConfig,
        sample_payload: MetricPayload,
    ) -> None:
        call_count = 0

        def mock_post(*args: object, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            resp = _make_response(500, text="Internal Server Error")
            raise httpx.HTTPStatusError(
                "Server Error", request=resp.request, response=resp
            )

        monkeypatch.setattr(httpx, "post", mock_post)

        send_metrics.retry.wait = lambda *a, **kw: 0  # type: ignore[attr-defined]
        with pytest.raises(RetryError):
            send_metrics(sample_payload, agent_config)

        assert call_count == 3


class TestSendMetricsNetworkError:
    """Ağ hatalarında 3 retry sonrası RetryError fırlatılır."""

    def test_connection_error_retries_three_times(
        self,
        monkeypatch: pytest.MonkeyPatch,
        agent_config: AgentConfig,
        sample_payload: MetricPayload,
    ) -> None:
        call_count = 0

        def mock_post(*args: object, **kwargs: object) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection refused")

        monkeypatch.setattr(httpx, "post", mock_post)

        send_metrics.retry.wait = lambda *a, **kw: 0  # type: ignore[attr-defined]
        with pytest.raises(RetryError):
            send_metrics(sample_payload, agent_config)

        assert call_count == 3
