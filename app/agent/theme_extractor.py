"""Theme extraction from SERP results."""
import json
from typing import Literal

from pydantic import BaseModel, Field

from app.agent.llm_client import LLMClient
from app.api.schemas import SerpResult


class ThemeReport(BaseModel):
    """Theme extraction report."""
    primary_keyword: str
    secondary_keywords: list[str]
    main_subtopics: list[str]
    search_intent: Literal["informational", "commercial", "transactional", "navigational"]
    content_gaps: list[str]
    unique_angles: list[str] = Field(default_factory=list)


class ThemeExtractor:
    """Extract themes and keywords from SERP results."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def extract(self, topic: str, serp_results: list[SerpResult]) -> ThemeReport:
        """Extract themes, keywords, and search intent from SERP results."""
        # Format SERP results for prompt
        serp_json = [
            {
                "rank": r.rank,
                "title": r.title,
                "snippet": r.snippet,
                "url": r.url,
            }
            for r in serp_results
        ]
        
        system_prompt = """You are an SEO strategist. Analyze search result data and extract content themes.
Return valid JSON matching the specified schema. Be precise and data-driven."""
        
        user_prompt = f"""Given these top-10 SERP results for '{topic}':

{json.dumps(serp_json, indent=2)}

Return JSON with:
  - primary_keyword: string (the main keyword/topic)
  - secondary_keywords: string[] (8-12 related terms that people actually type into search engines - focus on search queries, not descriptive labels. Examples: "remote team collaboration software", "async communication tools", "project tracking automation" - NOT "tools strategies" or "expert insights")
  - main_subtopics: string[] (5-8 recurring themes across results)
  - search_intent: one of "informational", "commercial", "transactional", or "navigational"
  - content_gaps: string[] (topics NOT covered that could differentiate our article)
  - unique_angles: string[] (3-5 specific angles competitors rarely cover; must be actionable and distinctive)

CRITICAL for secondary_keywords:
- Extract terms that are actual search queries people use
- Look for specific technical terms, product names, or problem-solving phrases
- Avoid generic descriptors like "strategies", "tools", "insights", "applications"
- Focus on terms with real search volume potential
- Examples of GOOD keywords (domain-neutral patterns):
  - "[specific product/tool name]"
  - "[action verb] + [noun]" (e.g., "automate project tracking")
  - "[problem] + [solution type]" (e.g., "reduce meeting fatigue software")
  - "[audience] + [specific need]" (e.g., "remote team async communication")
- Examples of BAD keywords: "generic strategies", "helpful tools", "expert insights", "real-world applications"

Focus on extracting actionable insights that will help create a comprehensive article."""
        
        result = await self.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=ThemeReport,
        )
        
        return result
