"""SEO metadata generation."""
from app.agent.llm_client import LLMClient
from app.agent.theme_extractor import ThemeReport
from app.api.schemas import SEOMetadata


class MetadataBuilder:
    """Generate SEO metadata."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def build(
        self,
        topic: str,
        theme_report: ThemeReport,
        article_sections: list,
    ) -> SEOMetadata:
        """Generate SEO metadata."""
        # Extract article content for context
        article_text = "\n".join(
            f"{s.heading_text}\n{s.content[:300]}"
            for s in article_sections[:3]  # First few sections
        )
        
        system_prompt = """You are an SEO expert. Generate compelling, keyword-optimized metadata.
Return valid JSON matching the specified schema. Be precise with character limits."""
        
        user_prompt = f"""Generate SEO metadata for an article about '{topic}'.

Primary keyword: {theme_report.primary_keyword}
Secondary keywords: {', '.join(theme_report.secondary_keywords[:5])}

Article preview:
{article_text[:500]}...

Return JSON:
{{
  "title_tag": "string (50-60 characters, includes primary keyword)",
  "meta_description": "string (150-160 characters, compelling and includes primary keyword)",
  "primary_keyword": "string",
  "secondary_keywords": ["string", ...]
}}

CRITICAL: title_tag must be 50-60 characters. meta_description must be 150-160 characters."""

        from pydantic import BaseModel

        class MetadataResponse(BaseModel):
            title_tag: str
            meta_description: str
            primary_keyword: str
            secondary_keywords: list[str]

        result = None
        prompt_for_attempt = user_prompt
        for attempt in range(3):
            result = await self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=prompt_for_attempt,
                response_format=MetadataResponse,
            )
            title_len = len(result.title_tag.strip())
            desc_len = len(result.meta_description.strip())
            if 50 <= title_len <= 60 and 150 <= desc_len <= 160:
                break

            if attempt < 2:
                prompt_for_attempt = (
                    user_prompt
                    + f"""

REVISION REQUIRED:
- Your title_tag was {title_len} characters: "{result.title_tag}"
  -> Must be 50-60 characters while keeping the primary keyword natural.
- Your meta_description was {desc_len} characters.
  -> Must be 150-160 characters and include the primary keyword.

Count characters carefully before responding."""
                )

        title_tag = self._normalize_title(result.title_tag)
        meta_description = self._normalize_meta_description(
            result.meta_description,
            theme_report.primary_keyword,
        )

        return SEOMetadata(
            title_tag=title_tag,
            meta_description=meta_description,
            primary_keyword=result.primary_keyword,
            secondary_keywords=result.secondary_keywords,
        )

    def _normalize_title(self, raw: str) -> str:
        """Clamp title to 50-60 chars with small near-miss fixes."""
        title = " ".join(raw.split()).strip()
        if len(title) > 60:
            title = title[:60].rstrip(" ,;:-")
        if len(title) < 50:
            suffixes = [" | 2026 Guide", " Guide", " Tips"]
            for suffix in suffixes:
                if len(title) + len(suffix) <= 60:
                    title = f"{title}{suffix}"
                    if len(title) >= 50:
                        break
        return title

    def _normalize_meta_description(self, raw: str, primary_keyword: str) -> str:
        """Clamp description to 150-160 chars and keep sentence complete."""
        desc = " ".join(raw.split()).strip()
        if primary_keyword.lower() not in desc.lower():
            desc = f"{primary_keyword}: {desc}"

        if len(desc) > 160:
            cut = desc[:160].rstrip()
            if " " in cut:
                cut = cut[:cut.rfind(" ")]
            desc = cut.rstrip(" ,;:-") + "."

        if 145 <= len(desc) < 150:
            for suffix in [" Learn more.", " Get started."]:
                if len(desc) + len(suffix) <= 160:
                    desc = f"{desc.rstrip('.!?')}{suffix}"
                    break

        if len(desc) < 150:
            padding = " Practical insights for better decisions."
            if len(desc) + len(padding) <= 160:
                desc = f"{desc.rstrip('.!?')}.{padding}"
            else:
                for filler in [" Learn more.", " Explore options.", " Read now."]:
                    if len(desc) + len(filler) <= 160:
                        desc = f"{desc.rstrip('.!?')}{filler}"
                    if len(desc) >= 150:
                        break

        # Final hard cap and punctuation cleanup
        if len(desc) > 160:
            desc = desc[:160].rstrip(" ,;:-")
        if desc and not desc.endswith((".", "!", "?")) and len(desc) < 160:
            desc = f"{desc}."
        return desc
