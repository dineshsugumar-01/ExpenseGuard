import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_webhook_idempotency_and_processing(client: AsyncClient):
    payload = {
        "event": "STORE_TRANSACTION",
        "content": {
            "id": "group_test_9999",
            "attributes": {
                "transactions": [
                    {
                        "transaction_journal_id": "8888",
                        "type": "withdrawal",
                        "date": "2026-10-07T10:00:00Z",
                        "amount": "1450.00",
                        "description": "Lunch with client",
                        "source_name": "Marcus Vance",
                        "destination_name": "Saravana Bhavan",
                        "category_name": "Meals & Entertainment",
                        "tags": []
                    }
                ]
            }
        }
    }

    # 1. First webhook delivery
    res1 = await client.post("/webhooks/firefly", json=payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["status"] == "processed"
    assert data1["group_id"] == "group_test_9999"
    assert "tier" in data1
    assert "score" in data1

    # 2. Resend same payload (Idempotency test)
    res2 = await client.post("/webhooks/firefly", json=payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["status"] == "duplicate_ignored"
