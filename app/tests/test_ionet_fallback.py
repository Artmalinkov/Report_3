# app/tests/test_ionet_fallback.py
"""
Тестирование fallback-логики IONETClient при 429 "Insufficient credits"
от IO_NET (см. FALLBACK_MODELS в ionet_client.py) — без обращения к
реальному API, _send_request замокан.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.ionet_client import IONETClient, IONetCreditsError, FALLBACK_MODELS


async def test_fallback_not_used_when_primary_succeeds():
    """Если основная модель отвечает успешно, резервные не вызываются"""
    client = IONETClient()
    mock_response = {"choices": [{"message": {"content": "ok"}}]}
    with patch.object(client, "_send_request", new=AsyncMock(return_value=mock_response)) as mocked:
        result = await client._send_request_with_fallback("промпт")

    assert result == mock_response
    mocked.assert_awaited_once_with("промпт")


async def test_fallback_tries_next_model_on_credits_error():
    """При 429 у основной модели пробуется первая резервная, и на этом успех"""
    client = IONETClient()
    mock_response = {"choices": [{"message": {"content": "от резервной"}}]}

    async def side_effect(prompt, model=None):
        if model is None:
            raise IONetCreditsError("основная модель исчерпана")
        assert model == FALLBACK_MODELS[0]
        return mock_response

    with patch.object(client, "_send_request", new=AsyncMock(side_effect=side_effect)):
        result = await client._send_request_with_fallback("промпт")

    assert result == mock_response


async def test_fallback_raises_when_all_models_exhausted():
    """Если основная и все резервные модели вернули 429 — итоговая ошибка IONetCreditsError"""
    client = IONETClient()
    with patch.object(client, "_send_request", new=AsyncMock(side_effect=IONetCreditsError("исчерпано"))) as mocked:
        raised = False
        try:
            await client._send_request_with_fallback("промпт")
        except IONetCreditsError:
            raised = True

    assert raised, "ожидалось IONetCreditsError"
    # основная модель + все резервные
    assert mocked.await_count == 1 + len(FALLBACK_MODELS)


async def test_fallback_not_used_on_non_credits_error():
    """Ошибка, отличная от 429, сразу пробрасывается — без перебора резервных моделей"""
    client = IONETClient()
    with patch.object(client, "_send_request", new=AsyncMock(side_effect=Exception("500 Internal Server Error"))) as mocked:
        raised = False
        try:
            await client._send_request_with_fallback("промпт")
        except Exception as e:
            raised = True
            assert "500" in str(e)

    assert raised, "ожидалось Exception"
    mocked.assert_awaited_once()
