import asyncio
import logging
from sqlalchemy import select
from app.db.models import TransactionCache, Score
from app.db.session import AsyncSessionLocal
from app.services.scoring import ScoringService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScoreAll")


async def score_existing_transactions():
    # 1. Fetch unscored IDs using a quick session
    async with AsyncSessionLocal() as session:
        stmt = (
            select(TransactionCache)
            .outerjoin(Score, TransactionCache.firefly_group_id == Score.firefly_group_id)
            .where(Score.id == None)
        )
        res = await session.execute(stmt)
        txs = res.scalars().all()
        tx_data = [
            (
                t.firefly_group_id,
                t.journal_id,
                t.amount,
                str(t.date),
                t.category,
                t.vendor,
                t.raw_json or {}
            )
            for t in txs
        ]

    logger.info(f"Found {len(tx_data)} unscored transactions. Scoring...")

    scored_count = 0
    for gid, jid, amt, dt, cat, ven, raw in tx_data:
        async with AsyncSessionLocal() as session:
            scoring_svc = ScoringService(session)
            split = {
                "transaction_journal_id": jid,
                "amount": amt,
                "date": dt,
                "category_name": cat,
                "destination_name": ven,
                "source_name": "Alex Chen",
                "source_id": 1,
            }
            try:
                await scoring_svc.process_firefly_transaction(gid, raw, [split])
                scored_count += 1
                if scored_count % 100 == 0:
                    logger.info(f"Scored {scored_count}/{len(tx_data)} transactions...")
            except Exception as exc:
                logger.warning(f"Error scoring {gid}: {exc}")

    logger.info(f"Successfully scored {scored_count} transactions!")


if __name__ == "__main__":
    asyncio.run(score_existing_transactions())
