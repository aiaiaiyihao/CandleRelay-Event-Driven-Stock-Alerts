import asyncio
import logging
from datetime import datetime
from app.core.config import SessionLocal
from app.models.PollTask import PollTask
from app.services.provider import fetch_price_by_provider
from fastapi import HTTPException
from sqlalchemy import select, and_

async def _poll_loop(job_data: dict) -> None:
    """
    Background loop that, every <interval> seconds, calls
    fetch_price_by_provider() for each symbol in the job.
    """
    logging.info(
        f"Polling job {job_data['id']}: {job_data['symbols']} every {job_data['interval']}s "
        f"via {job_data['provider']}"
    )

    while True:
        # 1️⃣ Refresh job status from DB — stop if no longer 'running'
        with SessionLocal() as session:
            job = session.get(PollTask, job_data['id'])
            if not job or job.status != "running":
                logging.info(f"⏹️ Job {job_data['id']} stopped (status={job.status if job else 'N/A'})")
                break

        # 2️⃣ Fetch each symbol
        for symbol in job_data['symbols']:
            try:
                await fetch_price_by_provider(job_data['provider'], symbol,True)
            except Exception as exc:
                logging.error(f"{symbol}: {exc}")

        # 3️⃣ Update last_run_at
        with SessionLocal() as session:
            job = session.get(PollTask, job_data['id'])
            if job:
                job.last_run_at = datetime.utcnow()
                session.commit()

        # 4️⃣ Sleep until next interval
        await asyncio.sleep(job_data['interval'])


async def start_job(req, session) -> PollTask:
    # Step 1: Query active polling tasks for this provider
    stmt = select(PollTask).where(
        and_(
            PollTask.provider == req.provider,
            PollTask.status == "running"
        )
    )
    existing_jobs = session.execute(stmt).scalars().all()

    # Step 2: Flatten all symbols currently in polling
    existing_symbols = set()
    for job in existing_jobs:
        existing_symbols.update(job.symbols)

    # Step 3: Check for intersection
    dupes = set(req.symbols) & existing_symbols
    if dupes:
        raise HTTPException(
            status_code=400,
            detail=f"Symbols already polling: {sorted(dupes)}"
        )


    """
    Create a PollTask row and launch its polling loop.
    """
    job = PollTask(
        symbols=req.symbols,
        provider=req.provider,
        interval=req.interval,
        status="running",
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    job_data = {
        "id": job.id,
        "symbols": job.symbols,
        "provider": job.provider,
        "interval": job.interval,
    }

    asyncio.create_task(_poll_loop(job_data))
    return job