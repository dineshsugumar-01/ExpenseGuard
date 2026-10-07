import pytest
from unittest.mock import AsyncMock, patch
from app.integrations.firefly import FireflyClient


@pytest.mark.asyncio
async def test_firefly_client_tagging():
    client = FireflyClient(base_url="http://mock-firefly:8080", token="mock-token")

    # Mock _request method
    with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = {"data": {"id": "123"}}

        success = await client.tag_and_annotate_transaction(
            group_id="123",
            journal_id=456,
            tier="HIGH",
            risk_score=85.0,
            reasons=["Amount 4x typical", "Weekend filing"],
            bridge_score_id="score-uuid-1",
            existing_tags=["team-dinner"]
        )

        assert success is True
        assert mock_req.called
        call_args = mock_req.call_args
        assert call_args[0][0] == "PUT"
        assert "123" in call_args[0][1]

        sent_json = call_args[1]["json"]
        assert sent_json["fire_webhooks"] is False
        txn_split = sent_json["transactions"][0]
        assert "tier:HIGH" in txn_split["tags"]
        assert "expenseguard:scored" in txn_split["tags"]
        assert "team-dinner" in txn_split["tags"]
        assert "Risk Score: 85/100" in txn_split["notes"]
