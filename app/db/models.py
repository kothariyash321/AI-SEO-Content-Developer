"""SQLAlchemy ORM models."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class GenerationJob(Base):
    """Job tracking table."""
    __tablename__ = "generation_jobs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    target_word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1500)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    pipeline_steps: Mapped[list["PipelineStep"]] = relationship("PipelineStep", back_populates="job", cascade="all, delete-orphan")
    article_output: Mapped["ArticleOutput | None"] = relationship("ArticleOutput", back_populates="job", uselist=False, cascade="all, delete-orphan")


class PipelineStep(Base):
    """Pipeline step tracking for crash durability."""
    __tablename__ = "pipeline_steps"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String, ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False)
    step_name: Mapped[str] = mapped_column(String(50), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    job: Mapped["GenerationJob"] = relationship("GenerationJob", back_populates="pipeline_steps")


class ArticleOutput(Base):
    """Final article output storage."""
    __tablename__ = "article_outputs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id: Mapped[str] = mapped_column(String, ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    output_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    job: Mapped["GenerationJob"] = relationship("GenerationJob", back_populates="article_output")
