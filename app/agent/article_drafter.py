"""Article drafting section by section."""
import re

from app.agent.llm_client import LLMClient
from app.agent.outline_generator import ArticleOutline
from app.agent.theme_extractor import ThemeReport
from app.api.schemas import ArticleSection


class ArticleDrafter:
    """Draft article sections."""

    _INTRO_BUDGET: int = 200
    _GENERIC_ATTRIBUTION_PHRASES = [
        "industry leaders",
        "experts often",
        "experts say",
        "thought leaders",
        "studies show",
    ]

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def draft_section(
        self,
        topic: str,
        heading: str,
        heading_level: str,
        word_budget: int,
        primary_keyword: str,
        secondary_keywords: list[str],
        previous_sections: list[ArticleSection] = None,
        parent_heading: str = None,
        max_retries: int = 3,
    ) -> ArticleSection:
        """Draft a single section of the article with strict word budget enforcement."""
        system_prompt = """You are an expert content writer. Write naturally — never robotic or formulaic.
CRITICAL RULES:
- Incorporate keywords contextually, NOT repeatedly. Each secondary keyword should appear at most 1-2 times per section.
- Vary sentence structure. Avoid formulaic patterns like "[Topic] is [verb]-ing [thing]."
- Write engaging, informative content that reads like a human expert wrote it, not a content mill.
- Do NOT repeat the same phrases multiple times in one section.
- Use synonyms and natural language variations.
- NEVER use first-person voice ("I", "my", "from my experience", "in my opinion"). Write in third-person or neutral voice appropriate for business content."""
        
        context = ""
        if previous_sections:
            # Show what was already covered to avoid repetition
            context = "\n\nPrevious sections (avoid repeating these topics):\n" + "\n".join(
                f"{s.heading_text}\n{s.content[:150]}..." 
                for s in previous_sections[-2:]  # Last 2 sections for context
            )
        
        # Build section-specific context based on heading
        section_context = ""
        if heading_level == "H3" and parent_heading:
            # Add H3-specific instructions based on heading content
            heading_lower = heading.lower()
            if "perspective" in heading_lower or "professional" in heading_lower or "expert" in heading_lower:
                section_context = "\n\nSECTION-SPECIFIC CONTEXT: This is a 'Perspectives' or 'Expert' section. Write from the viewpoint of practicing professionals describing real-world experiences in third-person or neutral voice. Focus on practical, day-to-day applications rather than theoretical concepts."
            elif "future" in heading_lower or "prediction" in heading_lower or "trend" in heading_lower:
                section_context = "\n\nSECTION-SPECIFIC CONTEXT: This is a 'Future' or 'Predictions' section. Focus on 5-year horizon developments, emerging technologies, and forward-looking trends. Use future tense appropriately. Discuss what's coming next, not what exists today."
            elif "comparison" in heading_lower or "compare" in heading_lower or "versus" in heading_lower:
                section_context = "\n\nSECTION-SPECIFIC CONTEXT: This is a 'Comparison' section. Provide specific, detailed comparisons between different options, tools, or approaches. Include concrete differences, pros/cons, and use cases. Be specific with names, features, and capabilities."
            elif "application" in heading_lower or "use case" in heading_lower or "implementation" in heading_lower:
                section_context = "\n\nSECTION-SPECIFIC CONTEXT: This is an 'Applications' or 'Use Cases' section. Focus on current, real-world implementations. Provide specific examples, case studies, or scenarios. Use present tense. Be concrete and specific."
            elif "technology" in heading_lower or "tool" in heading_lower or "system" in heading_lower:
                section_context = "\n\nSECTION-SPECIFIC CONTEXT: This is a 'Technology' or 'Tools' section. Describe specific technologies, tools, or systems. Include technical details, capabilities, and how they work. Name specific products or platforms when relevant."
            elif "guide" in heading_lower or "tutorial" in heading_lower or "how to" in heading_lower:
                section_context = "\n\nSECTION-SPECIFIC CONTEXT: This is a 'Guide' or 'Tutorial' section. Provide step-by-step instructions, actionable advice, or how-to information. Be practical and instructional."
            elif "challenge" in heading_lower or "pitfall" in heading_lower or "problem" in heading_lower:
                section_context = "\n\nSECTION-SPECIFIC CONTEXT: This is a 'Challenges' or 'Problems' section. Discuss obstacles, limitations, or difficulties. Be honest about drawbacks and provide balanced perspective."
            else:
                # Generic H3 context
                section_context = f"\n\nSECTION-SPECIFIC CONTEXT: This H3 section '{heading}' is part of the H2 section '{parent_heading}'. Write content that is distinct from other H3 sections in this article. Focus on unique aspects specific to this heading, not generic information that could apply to any section."
        
        # Build keyword list with instruction to use sparingly
        keyword_instruction = f"Primary keyword: {primary_keyword} (use naturally, 1-2 times)."
        if secondary_keywords:
            keyword_instruction += f" Secondary keywords (use each at most ONCE in this section, vary with synonyms): {', '.join(secondary_keywords[:5])}"
        
        user_prompt = f"""Write the '{heading}' section of an article about '{topic}'.
  
  CRITICAL: Target {word_budget} words, with a strict ±5% tolerance.
  
  {keyword_instruction}
  
  Tone: informative, engaging, expert — like a knowledgeable colleague explaining clearly.
  
  AVOID:
  - Filler phrases ('In today's world...', 'It goes without saying...', 'In conclusion...')
  - Repeating the same phrases multiple times
  - Formulaic sentence structures
  - Keyword stuffing
  - Vague attributions like "experts say", "industry leaders", or "studies show" without names
  - Repeating the same structure as other H3 sections{section_context}

  EVIDENCE REQUIREMENTS:
  - Every major claim should include a concrete example, named tool, or specific metric.
  - If a statistic is used, keep it plausible and specific (percentage, cost, timeline, or user count).
  - If you mention experts, name them; otherwise remove the attribution.
  - For H2 sections, include at least one concrete data point (pricing, percentage, count, or timeframe).
  
  Write naturally and conversationally. Vary your language. Use synonyms.
  Return only the section text (no heading).{context}"""
        
        # Retry logic to enforce word budget
        for attempt in range(max_retries):
            content = await self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            
            # Clean up content
            content = content.strip()
            
            # Count words
            word_count = len(re.findall(r'\b\w+\b', content))
            content_lower = content.lower()
            has_generic_attribution = any(
                phrase in content_lower for phrase in self._GENERIC_ATTRIBUTION_PHRASES
            )
            has_data_point = bool(re.search(r"\b\d+([.,]\d+)?(%|x|\+)?\b", content))
            
            # Check if within tolerance (±5% or ±8 words, whichever is larger)
            tolerance = max(8, int(word_budget * 0.05))
            if abs(word_count - word_budget) <= tolerance and not has_generic_attribution and (
                heading_level != "H2" or has_data_point
            ):
                # Word count is acceptable
                break
            elif attempt < max_retries - 1:
                # Adjust prompt for retry
                if word_count > word_budget:
                    user_prompt += (
                        f"\n\nIMPORTANT: Your previous attempt was {word_count} words, "
                        f"which exceeds the {word_budget} target. Revise to {word_budget} words "
                        f"within ±{tolerance} words."
                    )
                else:
                    user_prompt += (
                        f"\n\nIMPORTANT: Your previous attempt was {word_count} words, "
                        f"which is below the {word_budget} target. Revise to {word_budget} words "
                        f"within ±{tolerance} words."
                    )
                if has_generic_attribution:
                    user_prompt += (
                        "\n\nIMPORTANT: Remove vague attributions such as 'experts say', "
                        "'industry leaders', or 'studies show' unless you name the source."
                    )
                if heading_level == "H2" and not has_data_point:
                    user_prompt += (
                        "\n\nIMPORTANT: Add at least one concrete data point in this H2 "
                        "(price, percentage, count, or timeline)."
                    )
        
        return ArticleSection(
            heading_level=heading_level,
            heading_text=heading,
            content=content,
            word_count=word_count,
        )
    
    async def draft_article(
        self,
        topic: str,
        outline: ArticleOutline,
        theme_report: ThemeReport,
    ) -> list[ArticleSection]:
        """Draft the complete article section by section."""
        sections = []

        # Build a concrete drafting plan so H2 blocks (H2 + optional H3s)
        # stay within the outline's per-section budget.
        plan: list[dict] = [
            {
                "heading": outline.h1,
                "level": "H1",
                "budget": self._INTRO_BUDGET,
                "parent": None,
            }
        ]

        for outline_section in outline.sections:
            h3s = outline_section.h3s[:2]  # Max 2 H3s per H2
            block_budget = max(180, outline_section.word_budget)

            if not h3s:
                plan.append(
                    {
                        "heading": outline_section.h2,
                        "level": "H2",
                        "budget": block_budget,
                        "parent": None,
                    }
                )
                continue

            h3_count = len(h3s)
            # Reserve 30-45% for H3s while keeping the parent H2 substantial.
            tentative_h3_total = int(block_budget * 0.4)
            tentative_h3_total = max(100 * h3_count, min(tentative_h3_total, 140 * h3_count))
            h2_budget = max(110, block_budget - tentative_h3_total)
            h3_total = max(100 * h3_count, block_budget - h2_budget)
            per_h3_budget = max(100, h3_total // h3_count)

            # Final balancing to preserve exact block total.
            used = h2_budget + (per_h3_budget * h3_count)
            drift = block_budget - used
            h2_budget += drift

            plan.append(
                {
                    "heading": outline_section.h2,
                    "level": "H2",
                    "budget": h2_budget,
                    "parent": None,
                }
            )
            for h3_heading in h3s:
                plan.append(
                    {
                        "heading": h3_heading,
                        "level": "H3",
                        "budget": per_h3_budget,
                        "parent": outline_section.h2,
                    }
                )

        # Protect against cumulative drift by tracking remaining global budget.
        total_planned_budget = sum(item["budget"] for item in plan)
        remaining_budget = total_planned_budget
        used_keywords = set()

        for idx, item in enumerate(plan):
            remaining_items = len(plan) - idx
            min_floor = 120 if item["level"] == "H1" else 80
            max_allowed = remaining_budget - ((remaining_items - 1) * 80)
            adjusted_budget = max(min_floor, min(item["budget"], max_allowed))

            available_keywords = [
                kw for kw in theme_report.secondary_keywords
                if kw.lower() not in used_keywords
            ]
            if not available_keywords:
                available_keywords = theme_report.secondary_keywords
                used_keywords.clear()

            kw_slice = 2 if item["level"] == "H1" else 3
            drafted = await self.draft_section(
                topic=topic,
                heading=item["heading"],
                heading_level=item["level"],
                word_budget=adjusted_budget,
                primary_keyword=theme_report.primary_keyword,
                secondary_keywords=available_keywords[:kw_slice],
                previous_sections=sections,
                parent_heading=item["parent"],
            )
            sections.append(drafted)
            remaining_budget -= drafted.word_count

            for kw in available_keywords[:kw_slice]:
                used_keywords.add(kw.lower())

        return sections
