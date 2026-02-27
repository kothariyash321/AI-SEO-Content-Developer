"""Quality scorer tests."""
from datetime import datetime

from app.agent.quality_scorer import QualityScorer
from app.api.schemas import (
    ArticleOutput,
    ArticleSection,
    SEOMetadata,
    InternalLink,
    ExternalReference,
)


def test_keyword_in_h1():
    """Test primary keyword in H1 check."""
    scorer = QualityScorer()
    
    article = ArticleOutput(
        job_id="test",
        topic="productivity tools",
        sections=[
            ArticleSection(
                heading_level="H1",
                heading_text="Best Productivity Tools for Teams",
                content="Content here",
                word_count=100,
            )
        ],
        seo_metadata=SEOMetadata(
            title_tag="Best Productivity Tools",
            meta_description="Discover the best productivity tools",
            primary_keyword="productivity tools",
            secondary_keywords=[],
        ),
        internal_links=[],
        external_references=[],
        total_word_count=100,
        created_at=datetime.utcnow(),
    )
    
    report = scorer.score(article, target_word_count=100)
    
    # Check that keyword in H1 check exists
    h1_check = next((c for c in report.details if "H1" in c.check_name), None)
    assert h1_check is not None
    assert h1_check.passed is True


def test_meta_title_length():
    """Test meta title length validation."""
    scorer = QualityScorer()
    
    # Valid title (50-60 chars)
    valid_title = "Best Productivity Tools for Remote Teams in 2025"
    assert 50 <= len(valid_title) <= 60
    
    article = ArticleOutput(
        job_id="test",
        topic="test",
        sections=[
            ArticleSection(
                heading_level="H1",
                heading_text="Test",
                content="Content",
                word_count=100,
            )
        ],
        seo_metadata=SEOMetadata(
            title_tag=valid_title,
            meta_description="A" * 155,  # Valid description
            primary_keyword="test",
            secondary_keywords=[],
        ),
        internal_links=[],
        external_references=[],
        total_word_count=100,
        created_at=datetime.utcnow(),
    )
    
    report = scorer.score(article, target_word_count=100)
    title_check = next((c for c in report.details if "title length" in c.check_name.lower()), None)
    assert title_check is not None
    assert title_check.passed is True


def test_internal_link_count():
    """Test internal link count validation."""
    scorer = QualityScorer()
    
    article = ArticleOutput(
        job_id="test",
        topic="test",
        sections=[
            ArticleSection(
                heading_level="H1",
                heading_text="Test",
                content="Content",
                word_count=100,
            )
        ],
        seo_metadata=SEOMetadata(
            title_tag="Test Title",
            meta_description="Test description",
            primary_keyword="test",
            secondary_keywords=[],
        ),
        internal_links=[
            InternalLink(
                anchor_text="link 1",
                suggested_target_topic="topic1",
                placement_section="section1",
            ),
            InternalLink(
                anchor_text="link 2",
                suggested_target_topic="topic2",
                placement_section="section2",
            ),
            InternalLink(
                anchor_text="link 3",
                suggested_target_topic="topic3",
                placement_section="section3",
            ),
            InternalLink(
                anchor_text="link 4",
                suggested_target_topic="topic4",
                placement_section="section4",
            ),
        ],
        external_references=[],
        total_word_count=100,
        created_at=datetime.utcnow(),
    )
    
    report = scorer.score(article, target_word_count=100)
    link_check = next((c for c in report.details if "internal links" in c.check_name.lower()), None)
    assert link_check is not None
    assert link_check.passed is True  # 4 links is within 3-5 range
