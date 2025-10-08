import httpx
import pytest

from src.integrations.presgen_core.client import PresGenCoreClient
from src.integrations.presgen_core.schemas import PresGenPresentationRequest


@pytest.mark.asyncio
async def test_generate_presentation_normalises_download_url(monkeypatch):
    client = PresGenCoreClient(base_url="http://core.test", use_mock=False)
    captured = {}

    async def fake_post(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return httpx.Response(
            200,
            request=httpx.Request("POST", f"http://core.test{path}"),
            json={
                "job_id": "job123",
                "success": True,
                "mode": "presentation_only",
                "download_url": "/training/download/job123",
            },
        )

    monkeypatch.setattr(client, "_post_presentations", fake_post)

    request = PresGenPresentationRequest(
        skill="aws_ec2",
        target_duration_minutes=12,
        custom_prompt="Explain EC2 instance families",
        metadata={"workflow_id": "wf-123"},
    )

    response = await client.generate_presentation(request)

    assert captured["path"] == "/training/presentation-only"
    assert captured["payload"]["voice_profile_name"] == "OpenAI Demo Voice (Your Audio)"
    assert captured["payload"]["quality_level"] == "fast"
    assert captured["payload"]["mode"] == "presentation_only"
    assert captured["payload"]["content_text"] == "Explain EC2 instance families"
    assert response.download_url == "http://core.test/training/download/job123"
    assert response.success is True
    assert response.job_id == "job123"
    assert response.duration_ms is not None

    await client.close()
