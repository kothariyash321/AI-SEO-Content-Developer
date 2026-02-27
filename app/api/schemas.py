"""Pydantic schemas for API request/response models."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GenerationRequest(BaseModel):
    """Request schema for article generation."""
    topic: str = Field(..., description="Primary keyword / topic")
    target_word_count: int = Field(default=1500, ge=500, le=5000, description="Article length target")
    language: str = Field(default="en", description="BCP-47 language tag")


class SerpResult(BaseModel):
    """Single search engine result."""
    rank: int = Field(..., ge=1, description="Search result rank (1-10)")
    url: str = Field(..., description="Result URL")
    title: str = Field(..., description="Result title")
    snippet: str = Field(..., description="Result snippet/description")


class ArticleSection(BaseModel):
    """A single section of the article with heading and content."""
    heading_level: Literal["H1", "H2", "H3"] = Field(..., description="Heading level")
    heading_text: str = Field(..., description="Heading text")
    content: str = Field(..., description="Section content")
    word_count: int = Field(..., ge=0, description="Word count for this section")


class SEOMetadata(BaseModel):
    """SEO metadata for the article."""
    title_tag: str = Field(..., description="SEO title tag (50-60 chars)")
    meta_description: str = Field(..., description="Meta description (150-160 chars)")
    primary_keyword: str = Field(..., description="Primary keyword")
    secondary_keywords: list[str] = Field(default_factory=list, description="Secondary keywords")


class InternalLink(BaseModel):
    """Internal link suggestion."""
    anchor_text: str = Field(..., description="Anchor text for the link")
    suggested_target_topic: str = Field(..., description="Suggested target topic/page")
    placement_section: str = Field(..., description="Section where link should be placed")


class ExternalReference(BaseModel):
    """External reference/citation."""
    url: str = Field(..., description="External URL")
    publisher: str = Field(..., description="Publisher name")
    context_for_citation: str = Field(..., description="Context for where to cite this")
    placement_section: str = Field(..., description="Section where citation should be placed")


class FAQItem(BaseModel):
    """FAQ question and answer pair."""
    question: str = Field(..., description="FAQ question")
    answer: str = Field(..., description="FAQ answer")


class QualityCheck(BaseModel):
    """Individual quality check result."""
    check_name: str = Field(..., description="Name of the check")
    passed: bool = Field(..., description="Whether check passed")
    points: int = Field(..., ge=0, description="Points awarded")
    max_points: int = Field(..., ge=0, description="Maximum points for this check")
    details: str | None = Field(None, description="Additional details")


class QualityReport(BaseModel):
    """Quality scoring report."""
    total: int = Field(..., ge=0, le=100, description="Total quality score (0-100)")
    passed_checks: int = Field(..., ge=0, description="Number of checks that passed")
    failed_checks: int = Field(..., ge=0, description="Number of checks that failed")
    details: list[QualityCheck] = Field(default_factory=list, description="Individual check results")


class ArticleOutput(BaseModel):
    """Complete article output."""
    job_id: str = Field(..., description="Job ID")
    topic: str = Field(..., description="Article topic")
    sections: list[ArticleSection] = Field(default_factory=list, description="Article sections")
    seo_metadata: SEOMetadata = Field(..., description="SEO metadata")
    internal_links: list[InternalLink] = Field(default_factory=list, description="Internal link suggestions")
    external_references: list[ExternalReference] = Field(default_factory=list, description="External references")
    faq: list[FAQItem] | None = Field(None, description="FAQ section (optional)")
    quality_score: QualityReport | None = Field(None, description="Quality score report (optional)")
    total_word_count: int = Field(..., ge=0, description="Total word count")
    created_at: datetime = Field(..., description="Creation timestamp")


class JobStatus(BaseModel):
    """Job status response."""
    job_id: str = Field(..., description="Job ID")
    status: Literal["pending", "running", "completed", "failed"] = Field(..., description="Job status")
    topic: str = Field(..., description="Article topic")
    created_at: datetime = Field(..., description="Job creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    error: str | None = Field(None, description="Error message if failed")
