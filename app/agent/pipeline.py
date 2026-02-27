"""Main agent pipeline orchestrator."""
import json
import re
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.api.schemas import (
    SerpResult,
    ArticleOutput,
    ArticleSection,
    SEOMetadata,
    InternalLink,
    ExternalReference,
)
from app.agent.serp_adapter import SerpAdapter
from app.agent.llm_client import LLMClient
from app.agent.theme_extractor import ThemeExtractor, ThemeReport
from app.agent.outline_generator import OutlineGenerator, ArticleOutline
from app.agent.article_drafter import ArticleDrafter
from app.agent.metadata_builder import MetadataBuilder
from app.agent.link_strategist import LinkStrategist
from app.agent.quality_scorer import QualityScorer
from app.agent.faq_generator import FAQGenerator
from app.api.schemas import FAQItem


class AgentRunner:
    """Orchestrates the multi-step agent pipeline."""
    
    # Define pipeline steps in order
    STEP_NAMES = [
        "serp_fetch",
        "theme_extraction",
        "outline_generation",
        "article_drafting",
        "metadata_generation",
        "link_strategy",
        "faq_generation",  # Bonus feature
    ]
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm_client = LLMClient()
        self.serp_adapter = SerpAdapter()
        self.theme_extractor = ThemeExtractor(self.llm_client)
        self.outline_generator = OutlineGenerator(self.llm_client)
        self.article_drafter = ArticleDrafter(self.llm_client)
        self.metadata_builder = MetadataBuilder(self.llm_client)
        self.link_strategist = LinkStrategist(self.llm_client)
        self.quality_scorer = QualityScorer()
        self.faq_generator = FAQGenerator(self.llm_client)
    
    async def run(self, job_id: str) -> None:
        """Run the complete pipeline for a job."""
        # Get job
        job = await crud.get_job(self.db, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        
        # Update job status to running
        await crud.update_job_status(self.db, job_id, "running")
        
        try:
            # Check for existing steps and resume from last completed
            existing_steps = await crud.get_pipeline_steps(self.db, job_id)
            step_results = {}
            
            # Load existing step results
            for step in existing_steps:
                if step.status == "completed" and step.result_json:
                    step_results[step.step_name] = step.result_json
            
            # Determine starting step
            last_completed = await crud.get_last_completed_step(self.db, job_id)
            start_index = 0
            if last_completed:
                try:
                    start_index = self.STEP_NAMES.index(last_completed.step_name) + 1
                except ValueError:
                    start_index = 0
            
            # Execute each step
            for step_index, step_name in enumerate(self.STEP_NAMES[start_index:], start=start_index):
                await self._execute_step(job_id, step_name, step_index, step_results, job)
            
            # Assemble final output
            article_output = await self._assemble_output(job_id, step_results, job)
            
            # Score quality
            quality_report = self.quality_scorer.score(article_output, job.target_word_count)
            
            # Check for critical failures that require revision
            word_count_check = next(
                (c for c in quality_report.details if "Word count" in c.check_name and not c.passed),
                None
            )
            phrase_repetition_check = next(
                (c for c in quality_report.details if "Phrase repetition" in c.check_name and not c.passed),
                None
            )
            keyword_coverage_check = next(
                (c for c in quality_report.details if "Secondary keyword coverage" in c.check_name and not c.passed),
                None
            )
            
            # If quality score is low OR critical failures exist, attempt revision (max 2 attempts)
            revision_attempts = 0
            max_revisions = 2
            needs_revision = (
                quality_report.total < 70 
                or word_count_check is not None 
                or phrase_repetition_check is not None
                or keyword_coverage_check is not None
            )
            
            print(f"Quality check: score={quality_report.total}, word_count_failed={word_count_check is not None}, phrase_repetition_failed={phrase_repetition_check is not None}, needs_revision={needs_revision}")
            
            while needs_revision and revision_attempts < max_revisions:
                revision_attempts += 1
                print(f"Starting revision attempt {revision_attempts}/{max_revisions}")
                
                # Re-draft sections that failed quality checks
                article_output = await self._revise_article(
                    job_id, article_output, quality_report, step_results, job
                )
                
                # Re-score after revision
                quality_report = self.quality_scorer.score(article_output, job.target_word_count)
                
                # Re-check if revision is still needed
                word_count_check = next(
                    (c for c in quality_report.details if "Word count" in c.check_name and not c.passed),
                    None
                )
                phrase_repetition_check = next(
                    (c for c in quality_report.details if "Phrase repetition" in c.check_name and not c.passed),
                    None
                )
                keyword_coverage_check = next(
                    (c for c in quality_report.details if "Secondary keyword coverage" in c.check_name and not c.passed),
                    None
                )
                
                needs_revision = (
                    quality_report.total < 70 
                    or word_count_check is not None 
                    or phrase_repetition_check is not None
                    or keyword_coverage_check is not None
                )
                
                print(f"After revision {revision_attempts}: score={quality_report.total}, word_count_failed={word_count_check is not None}, phrase_repetition_failed={phrase_repetition_check is not None}, needs_revision={needs_revision}")
            
            # Set quality score on the article output
            article_output.quality_score = quality_report
            
            # Save final output
            await crud.save_article_output(
                self.db,
                job_id,
                article_output.model_dump(mode="json"),
                quality_report.total,
                article_output.total_word_count,
            )
            
            # Update job status to completed
            await crud.update_job_status(self.db, job_id, "completed")
            
        except Exception as e:
            await crud.update_job_status(self.db, job_id, "failed", str(e))
            raise
    
    async def _execute_step(
        self,
        job_id: str,
        step_name: str,
        step_order: int,
        step_results: dict,
        job,
    ) -> None:
        """Execute a single pipeline step."""
        # Create or get step record
        existing_steps = await crud.get_pipeline_steps(self.db, job_id)
        step_record = next(
            (s for s in existing_steps if s.step_name == step_name),
            None
        )
        
        if not step_record:
            step_record = await crud.create_pipeline_step(
                self.db, job_id, step_name, step_order
            )
        
        # Skip if already completed
        if step_record.status == "completed":
            return
        
        # Mark as running
        await crud.update_step_status(self.db, step_record.id, "running")
        
        try:
            # Execute step
            if step_name == "serp_fetch":
                result = await self._step_serp_fetch(job.topic)
            elif step_name == "theme_extraction":
                result = await self._step_theme_extraction(
                    job.topic, step_results["serp_fetch"]
                )
            elif step_name == "outline_generation":
                result = await self._step_outline_generation(
                    job.topic, step_results["theme_extraction"], job.target_word_count
                )
            elif step_name == "article_drafting":
                result = await self._step_article_drafting(
                    job.topic, step_results["theme_extraction"], step_results["outline_generation"]
                )
            elif step_name == "metadata_generation":
                result = await self._step_metadata_generation(
                    job.topic, step_results["theme_extraction"], step_results["article_drafting"]
                )
            elif step_name == "link_strategy":
                result = await self._step_link_strategy(
                    job.topic, step_results["theme_extraction"], step_results["article_drafting"]
                )
            elif step_name == "faq_generation":
                result = await self._step_faq_generation(
                    job.topic, step_results["serp_fetch"], step_results["article_drafting"]
                )
            else:
                raise ValueError(f"Unknown step: {step_name}")
            
            # Save result
            # Handle different result types: dict, list, or Pydantic model
            if isinstance(result, dict):
                result_json = result
            elif isinstance(result, list):
                result_json = result  # Lists are already serialized
            else:
                result_json = result.model_dump(mode="json")
            
            await crud.update_step_status(
                self.db, step_record.id, "completed", result_json
            )
            step_results[step_name] = result_json
            
        except Exception as e:
            await crud.update_step_status(
                self.db, step_record.id, "failed", error=str(e)
            )
            raise
    
    async def _step_serp_fetch(self, topic: str) -> list[dict]:
        """Step 1: Fetch SERP results."""
        results = await self.serp_adapter.fetch(topic, max_results=10)
        return [r.model_dump(mode="json") for r in results]
    
    async def _step_theme_extraction(
        self, topic: str, serp_results: list[dict]
    ) -> dict:
        """Step 2: Extract themes."""
        serp_objs = [SerpResult(**r) for r in serp_results]
        theme_report = await self.theme_extractor.extract(topic, serp_objs)
        return theme_report.model_dump(mode="json")
    
    async def _step_outline_generation(
        self, topic: str, theme_report: dict, target_word_count: int
    ) -> dict:
        """Step 3: Generate outline."""
        theme_obj = ThemeReport(**theme_report)
        outline = await self.outline_generator.generate(topic, theme_obj, target_word_count)
        return outline.model_dump(mode="json")
    
    async def _step_article_drafting(
        self, topic: str, theme_report: dict, outline: dict
    ) -> list[dict]:
        """Step 4: Draft article."""
        theme_obj = ThemeReport(**theme_report)
        outline_obj = ArticleOutline(**outline)
        sections = await self.article_drafter.draft_article(topic, outline_obj, theme_obj)
        return [s.model_dump(mode="json") for s in sections]
    
    async def _step_metadata_generation(
        self, topic: str, theme_report: dict, sections: list[dict]
    ) -> dict:
        """Step 5: Generate metadata."""
        theme_obj = ThemeReport(**theme_report)
        section_objs = [ArticleSection(**s) for s in sections]
        metadata = await self.metadata_builder.build(topic, theme_obj, section_objs)
        return metadata.model_dump(mode="json")
    
    async def _step_link_strategy(
        self, topic: str, theme_report: dict, sections: list[dict]
    ) -> dict:
        """Step 6: Build link strategy."""
        theme_obj = ThemeReport(**theme_report)
        section_objs = [ArticleSection(**s) for s in sections]
        internal_links, external_refs = await self.link_strategist.build_strategy(
            topic, theme_obj, section_objs
        )
        return {
            "internal_links": [l.model_dump(mode="json") for l in internal_links],
            "external_references": [r.model_dump(mode="json") for r in external_refs],
        }
    
    async def _step_faq_generation(
        self, topic: str, serp_results: list[dict], sections: list[dict]
    ) -> list[dict]:
        """Step 7: Generate FAQ section."""
        serp_objs = [SerpResult(**r) for r in serp_results]
        section_objs = [ArticleSection(**s) for s in sections]
        faq_items = await self.faq_generator.generate(topic, serp_objs, section_objs)
        return [item.model_dump(mode="json") for item in faq_items]
    
    async def _assemble_output(
        self, job_id: str, step_results: dict, job
    ) -> ArticleOutput:
        """Assemble final article output from step results."""
        sections = [ArticleSection(**s) for s in step_results["article_drafting"]]
        external_references = [
            ExternalReference(**r) for r in step_results["link_strategy"]["external_references"]
        ]
        sections = self._inject_external_citations(sections, external_references)
        total_word_count = sum(s.word_count for s in sections)
        
        return ArticleOutput(
            job_id=job_id,
            topic=job.topic,
            sections=sections,
            seo_metadata=SEOMetadata(**step_results["metadata_generation"]),
            internal_links=[
                InternalLink(**l) for l in step_results["link_strategy"]["internal_links"]
            ],
            external_references=external_references,
            faq=[
                FAQItem(**f) for f in step_results.get("faq_generation", [])
            ] if step_results.get("faq_generation") else None,
            quality_score=None,  # Will be set after scoring
            total_word_count=total_word_count,
            created_at=datetime.utcnow(),
        )

    def _inject_external_citations(
        self,
        sections: list[ArticleSection],
        external_references: list[ExternalReference],
    ) -> list[ArticleSection]:
        """Inject lightweight in-text citations into the matched section content."""
        if not sections or not external_references:
            return sections

        for ref in external_references:
            target_section = None
            placement_lower = ref.placement_section.lower()
            for section in sections:
                heading_lower = section.heading_text.lower()
                if placement_lower in heading_lower or heading_lower in placement_lower:
                    target_section = section
                    break

            if not target_section:
                continue

            # Avoid duplicate citation insertion for same URL.
            if ref.url in target_section.content:
                continue

            citation_line = (
                f"\n\nSource: {ref.publisher} — {ref.context_for_citation} ({ref.url})"
            )
            target_section.content = f"{target_section.content.rstrip()}{citation_line}"
            target_section.word_count = len(re.findall(r"\b\w+\b", target_section.content))

        return sections
    
    async def _revise_article(
        self,
        job_id: str,
        article_output: ArticleOutput,
        quality_report,
        step_results: dict,
        job,
    ) -> ArticleOutput:
        """Revise article based on quality report feedback."""
        # Identify failed checks
        failed_checks = [c for c in quality_report.details if not c.passed]
        
        # Check for word count failure - need to reduce content
        word_count_check = next(
            (c for c in failed_checks if "Word count" in c.check_name),
            None
        )
        
        if word_count_check:
            # Word count is too high - need to reduce
            target_reduction = article_output.total_word_count - job.target_word_count
            reduction_percentage = (target_reduction / article_output.total_word_count) * 100
            
            # Re-draft sections to be more concise
            revised_sections = []
            for section in article_output.sections:
                if section.heading_level == "H1":
                    # Keep intro but make it shorter
                    new_budget = max(150, section.word_count - int(section.word_count * 0.15))
                elif section.heading_level == "H2":
                    # Reduce H2 sections by ~15-20%
                    new_budget = max(180, section.word_count - int(section.word_count * 0.20))
                elif section.heading_level == "H3":
                    # Reduce H3 sections by ~20% or remove if too short
                    if section.word_count < 100:
                        continue  # Skip very short H3s
                    new_budget = max(100, section.word_count - int(section.word_count * 0.20))
                else:
                    new_budget = section.word_count
                
                # Find parent heading for H3s
                parent_heading = None
                if section.heading_level == "H3":
                    # Find the H2 that precedes this H3
                    for prev_section in article_output.sections:
                        if prev_section.heading_level == "H2":
                            parent_heading = prev_section.heading_text
                        elif prev_section == section:
                            break
                
                # Re-draft the section with new budget and explicit word count target
                revised_section = await self.article_drafter.draft_section(
                    topic=job.topic,
                    heading=section.heading_text,
                    heading_level=section.heading_level,
                    word_budget=new_budget,
                    primary_keyword=article_output.seo_metadata.primary_keyword,
                    secondary_keywords=article_output.seo_metadata.secondary_keywords[:2],  # Use fewer keywords
                    previous_sections=revised_sections,
                    parent_heading=parent_heading,
                )
                revised_sections.append(revised_section)
            
            # Rebuild article output with revised sections
            total_word_count = sum(s.word_count for s in revised_sections)
            article_output.sections = revised_sections
            article_output.total_word_count = total_word_count
        
        # Check for phrase repetition failure - need to reduce keyword density
        phrase_repetition_check = next(
            (c for c in failed_checks if "Phrase repetition" in c.check_name),
            None
        )
        
        if phrase_repetition_check:
            # Reduce keyword usage - re-draft sections with fewer keywords
            revised_sections = []
            for section in article_output.sections:
                # Use fewer secondary keywords per section
                limited_keywords = article_output.seo_metadata.secondary_keywords[:2]  # Only 2 per section
                
                revised_section = await self.article_drafter.draft_section(
                    topic=job.topic,
                    heading=section.heading_text,
                    heading_level=section.heading_level,
                    word_budget=section.word_count,  # Keep same length
                    primary_keyword=article_output.seo_metadata.primary_keyword,
                    secondary_keywords=limited_keywords,
                    previous_sections=revised_sections,
                )
                revised_sections.append(revised_section)
            
            article_output.sections = revised_sections
            article_output.total_word_count = sum(s.word_count for s in revised_sections)
        
        return article_output
