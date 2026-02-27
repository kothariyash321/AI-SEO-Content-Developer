"""Link strategy generation (internal and external links)."""
import httpx

from app.agent.llm_client import LLMClient
from app.agent.theme_extractor import ThemeReport
from app.api.schemas import InternalLink, ExternalReference, ArticleSection


class LinkStrategist:
    """Generate internal and external link strategies."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def build_strategy(
        self,
        topic: str,
        theme_report: ThemeReport,
        article_sections: list[ArticleSection],
    ) -> tuple[list[InternalLink], list[ExternalReference]]:
        """Generate internal and external link strategies."""
        # Format sections for context
        sections_text = "\n".join(
            f"{s.heading_level}: {s.heading_text}\n{s.content[:200]}"
            for s in article_sections
        )
        
        system_prompt = """You are an SEO link strategist. Identify relevant internal and external linking opportunities.
Return valid JSON matching the specified schema."""
        
        user_prompt = f"""For an article about '{topic}', generate link strategy:

Article sections:
{sections_text[:1000]}...

Primary keyword: {theme_report.primary_keyword}
Secondary keywords: {', '.join(theme_report.secondary_keywords[:5])}

Return JSON:
{{
  "internal_links": [
    {{
      "anchor_text": "string (natural anchor text)",
      "suggested_target_topic": "string (related topic/page)",
      "placement_section": "string (section heading where link should go)"
    }}
  ],
  "external_references": [
    {{
      "publisher": "string (publisher name)",
      "suggested_search_query": "string (query to find a real source from this publisher)",
      "context_for_citation": "string (where/why to cite this)",
      "placement_section": "string (section heading)"
    }}
  ]
}}

Requirements:
- 3-5 internal links with natural anchor text
- 2-4 external references from authoritative publishers (research papers, industry reports, reputable sites)
- Do NOT invent specific article URLs. Provide publisher + search query only.
- Links should be contextually relevant and add value"""

        from pydantic import BaseModel

        class LinkStrategyResponse(BaseModel):
            internal_links: list[dict]
            external_references: list[dict]

        result = await self.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=LinkStrategyResponse,
        )

        # Convert to proper models
        internal_links = [
            InternalLink(**link) for link in result.internal_links
        ]

        # Get actual section headings for validation
        actual_headings = {s.heading_text for s in article_sections}

        # Validate external references - resolve real URLs and validate placements.
        validated_external_refs = []
        for ref_dict in result.external_references:
            url = self._resolve_reference_url(ref_dict)
            placement = ref_dict.get("placement_section", "")

            # Validate URL
            url_valid = url and await self._validate_url(url)

            # Validate placement section exists in article
            placement_valid = False
            if placement:
                # Check if placement matches any actual heading (case-insensitive, partial match)
                placement_lower = placement.lower()
                for heading in actual_headings:
                    if placement_lower in heading.lower() or heading.lower() in placement_lower:
                        placement_valid = True
                        # Update to use actual heading name
                        ref_dict["placement_section"] = heading
                        break

            if url_valid and placement_valid:
                validated_external_refs.append(
                    ExternalReference(
                        url=url,
                        publisher=ref_dict.get("publisher", "Unknown publisher"),
                        context_for_citation=ref_dict.get(
                            "context_for_citation",
                            "Use as supporting external source.",
                        ),
                        placement_section=ref_dict["placement_section"],
                    )
                )
            else:
                # Log what failed
                issues = []
                if not url_valid:
                    issues.append("invalid URL")
                if not placement_valid:
                    issues.append(f"placement section '{placement}' not found in article")
                print(f"Warning: External reference skipped ({', '.join(issues)}): {url}")

        # Ensure we have at least 2 valid external references
        if len(validated_external_refs) < 2 and result.external_references:
            for ref_dict in result.external_references:
                if len(validated_external_refs) >= 4:
                    break

                # Skip if already validated
                url = self._resolve_reference_url(ref_dict)
                if any(ref.url == url for ref in validated_external_refs):
                    continue

                if url and await self._validate_url(url):
                    # Try to find a matching section or use first H2
                    placement = ref_dict.get("placement_section", "")
                    if not placement or not any(placement.lower() in h.lower() or h.lower() in placement.lower() for h in actual_headings):
                        # Use first H2 section as fallback
                        h2_sections = [s for s in article_sections if s.heading_level == "H2"]
                        if h2_sections:
                            ref_dict["placement_section"] = h2_sections[0].heading_text
                        elif article_sections:
                            ref_dict["placement_section"] = article_sections[0].heading_text
                    validated_external_refs.append(
                        ExternalReference(
                            url=url,
                            publisher=ref_dict.get("publisher", "Unknown publisher"),
                            context_for_citation=ref_dict.get(
                                "context_for_citation",
                                "Use as supporting external source.",
                            ),
                            placement_section=ref_dict.get("placement_section", ""),
                        )
                    )

        return internal_links, validated_external_refs

    def _resolve_reference_url(self, ref_dict: dict) -> str:
        """Resolve a stable URL from publisher/query when LLM does not provide one."""
        direct_url = ref_dict.get("url", "")
        if direct_url:
            return direct_url

        publisher = (ref_dict.get("publisher") or "").lower().strip()
        publisher_domains = {
            "harvard business review": "https://hbr.org",
            "forbes": "https://www.forbes.com",
            "gartner": "https://www.gartner.com",
            "mckinsey": "https://www.mckinsey.com",
            "mit sloan": "https://mitsloan.mit.edu",
            "stanford": "https://www.stanford.edu",
            "hubspot": "https://blog.hubspot.com",
            "atlassian": "https://www.atlassian.com",
            "microsoft": "https://www.microsoft.com",
            "google": "https://blog.google",
        }
        for key, domain in publisher_domains.items():
            if key in publisher:
                return domain
        return ""

    async def _validate_url(self, url: str) -> bool:
        """Validate that a URL exists and is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                response = await client.head(url)
                # Accept 2xx and 3xx status codes
                if 200 <= response.status_code < 400:
                    return True
                # Some publishers reject HEAD; fallback to lightweight GET.
                response = await client.get(url)
                return 200 <= response.status_code < 400
        except Exception:
            # If validation fails, return False
            return False
