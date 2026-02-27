"""CRUD operations for database models."""
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import GenerationJob, PipelineStep, ArticleOutput
from app.api.schemas import GenerationRequest


async def create_job(db: AsyncSession, request: GenerationRequest) -> GenerationJob:
    """Create a new generation job."""
    job = GenerationJob(
        topic=request.topic,
        target_word_count=request.target_word_count,
        language=request.language,
        config_json=request.model_dump(),
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: str) -> GenerationJob | None:
    """Get a job by ID with relationships loaded."""
    result = await db.execute(
        select(GenerationJob)
        .options(selectinload(GenerationJob.article_output))
        .where(GenerationJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def update_job_status(
    db: AsyncSession,
    job_id: str,
    status: str,
    error: str | None = None,
) -> GenerationJob | None:
    """Update job status."""
    job = await get_job(db, job_id)
    if not job:
        return None
    
    job.status = status
    job.error = error
    job.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    return job


async def create_pipeline_step(
    db: AsyncSession,
    job_id: str,
    step_name: str,
    step_order: int,
) -> PipelineStep:
    """Create a new pipeline step."""
    step = PipelineStep(
        job_id=job_id,
        step_name=step_name,
        step_order=step_order,
        status="pending",
    )
    db.add(step)
    await db.commit()
    await db.refresh(step)
    return step


async def get_pipeline_steps(
    db: AsyncSession,
    job_id: str,
) -> list[PipelineStep]:
    """Get all pipeline steps for a job, ordered by step_order."""
    result = await db.execute(
        select(PipelineStep)
        .where(PipelineStep.job_id == job_id)
        .order_by(PipelineStep.step_order)
    )
    return list(result.scalars().all())


async def update_step_status(
    db: AsyncSession,
    step_id: str,
    status: str,
    result_json: dict[str, Any] | None = None,
    error: str | None = None,
) -> PipelineStep | None:
    """Update pipeline step status and result."""
    result = await db.execute(select(PipelineStep).where(PipelineStep.id == step_id))
    step = result.scalar_one_or_none()
    if not step:
        return None
    
    step.status = status
    step.result_json = result_json
    step.error = error
    
    if status == "running" and not step.started_at:
        step.started_at = datetime.utcnow()
    elif status == "completed" and not step.completed_at:
        step.completed_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(step)
    return step


async def get_last_completed_step(
    db: AsyncSession,
    job_id: str,
) -> PipelineStep | None:
    """Get the last completed step for a job."""
    result = await db.execute(
        select(PipelineStep)
        .where(
            PipelineStep.job_id == job_id,
            PipelineStep.status == "completed"
        )
        .order_by(PipelineStep.step_order.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def save_article_output(
    db: AsyncSession,
    job_id: str,
    output_json: dict[str, Any],
    quality_score: int | None,
    word_count: int,
) -> ArticleOutput:
    """Save the final article output."""
    # Check if output already exists
    result = await db.execute(
        select(ArticleOutput).where(ArticleOutput.job_id == job_id)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.output_json = output_json
        existing.quality_score = quality_score
        existing.word_count = word_count
        await db.commit()
        await db.refresh(existing)
        return existing
    
    output = ArticleOutput(
        job_id=job_id,
        output_json=output_json,
        quality_score=quality_score,
        word_count=word_count,
    )
    db.add(output)
    await db.commit()
    await db.refresh(output)
    return output
