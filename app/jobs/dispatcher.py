"""Job dispatcher for async job processing."""
import asyncio

from app.agent.pipeline import AgentRunner
from app.db.session import AsyncSessionLocal


async def dispatch_job(job_id: str) -> None:
    """
    Dispatch a job to the agent pipeline.
    
    This runs in the background and processes the job asynchronously.
    Creates its own database session.
    """
    # Run in background task
    asyncio.create_task(run_job(job_id))


async def run_job(job_id: str) -> None:
    """Run the agent pipeline for a job."""
    # Create a new database session for this background task
    async with AsyncSessionLocal() as db:
        runner = AgentRunner(db)
        try:
            await runner.run(job_id)
        except Exception as e:
            # Update job status to failed
            from app.db import crud
            try:
                await crud.update_job_status(db, job_id, "failed", str(e))
                await db.commit()
            except Exception as update_error:
                # Log but don't fail if we can't update status
                print(f"Failed to update job status: {update_error}")
                await db.rollback()
