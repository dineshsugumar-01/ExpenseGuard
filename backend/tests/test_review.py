import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.models import Flag, Score, TransactionCache, Employee
from app.db.session import AsyncSessionLocal
from datetime import datetime, date
import uuid


@pytest.mark.asyncio
async def test_review_submission_endpoint():
    async with AsyncSessionLocal() as db:
        # Create test employee if not exists
        emp = Employee(
            id=str(uuid.uuid4()),
            email=f"auditor_{uuid.uuid4().hex[:6]}@expenseguard.local",
            name="Test Auditor",
            role="auditor",
            password_hash="fakehash"
        )
        db.add(emp)

        tx = TransactionCache(
            firefly_group_id=f"grp_{uuid.uuid4().hex[:8]}",
            journal_id=99999,
            amount=5000.0,
            date=date.today(),
            vendor="Luxury Flights",
            category="Travel",
            employee_id=emp.id
        )
        db.add(tx)

        score = Score(
            id=str(uuid.uuid4()),
            firefly_group_id=tx.firefly_group_id,
            risk_score=95.0,
            tier="HIGH",
            reasons_json=["Excessive flight amount"],
            contributions_json=[{"feature": "amount", "impact": 95, "is_anomalous": True}]
        )
        db.add(score)

        flag = Flag(
            id=str(uuid.uuid4()),
            score_id=score.id,
            status="open"
        )
        db.add(flag)
        await db.commit()
        flag_id = flag.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Test review submission without explicit bearer token (falls back to default auditor)
        payload = {"decision": "confirmed", "note": "Auditor confirmed fraudulent claim"}
        response = await ac.post(f"/api/flags/{flag_id}/review", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed"
        assert data["flag_id"] == flag_id

        # Verify flag updated in DB
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            updated_flag = await db.get(Flag, flag_id)
            assert updated_flag.status == "confirmed"
            assert updated_flag.note == "Auditor confirmed fraudulent claim"
