"""API routes for the SEO content generation service."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import GenerationRequest, ArticleOutput, JobStatus
from app.db.session import get_db
from app.db import crud
from app.jobs.dispatcher import dispatch_job

router = APIRouter()


@router.post("/jobs", response_model=JobStatus, status_code=status.HTTP_201_CREATED)
async def create_job(
    request: GenerationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new article generation job."""
    job = await crud.create_job(db, request)
    
    # Dispatch job asynchronously (creates its own DB session)
    await dispatch_job(job.id)
    
    return JobStatus(
        job_id=job.id,
        status=job.status,
        topic=job.topic,
        created_at=job.created_at,
        updated_at=job.updated_at,
        error=job.error,
    )


@router.get("/jobs/{job_id}", response_model=ArticleOutput | JobStatus)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get job status or completed article output."""
    try:
        job = await crud.get_job(db, job_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found",
            )
        
        # If job is completed, return the article output
        if job.status == "completed" and job.article_output:
            try:
                output_data = job.article_output.output_json
                return ArticleOutput(**output_data)
            except Exception as e:
                # If there's an error parsing the output, return job status with error
                return JobStatus(
                    job_id=job.id,
                    status=job.status,
                    topic=job.topic,
                    created_at=job.created_at,
                    updated_at=job.updated_at,
                    error=f"Error loading article output: {str(e)}",
                )
        
        # Otherwise return job status
        return JobStatus(
            job_id=job.id,
            status=job.status,
            topic=job.topic,
            created_at=job.created_at,
            updated_at=job.updated_at,
            error=job.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )
