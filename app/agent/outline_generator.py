"""Article outline generation."""
from pydantic import BaseModel

from app.agent.llm_client import LLMClient
from app.agent.theme_extractor import ThemeReport


class OutlineSection(BaseModel):
    """A section in the outline."""
    h2: str
    word_budget: int
    h3s: list[str] = []


class ArticleOutline(BaseModel):
    """Complete article outline."""
    h1: str
    sections: list[OutlineSection]


class OutlineGenerator:
    """Generate article outline from themes."""

    # H1 intro is drafted separately in ArticleDrafter; this constant mirrors
    # the budget reserved there so our math stays consistent.
    _INTRO_BUDGET: int = 200

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        topic: str,
        theme_report: ThemeReport,
        target_word_count: int,
    ) -> ArticleOutline:
        """Generate a word-budget-accurate article outline.

        Strategy
        --------
        1. Ask the LLM to produce an outline whose section budgets sum to
           (target_word_count - intro_budget).
        2. After the LLM responds, verify the math.
        3. If needed, scale each section budget proportionally.
        4. Correct rounding/guard drift so the section sum is exact.
        """
        # Words available for all H2/H3 sections (intro is drafted separately)
        section_budget = target_word_count - self._INTRO_BUDGET

        result = await self._call_llm(topic, theme_report, target_word_count, section_budget)
        result = self._enforce_budget(result, section_budget)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _call_llm(
        self,
        topic: str,
        theme_report: ThemeReport,
        target_word_count: int,
        section_budget: int,
    ) -> ArticleOutline:
        """Ask the LLM to build the outline."""
        system_prompt = (
            "You are a senior content strategist specialising in SEO-optimised "
            "article structure.\n"
            "Return valid JSON matching the specified schema. Create outlines that "
            "are logical, comprehensive, and SEO-friendly."
        )

        user_prompt = f"""Create a detailed article outline for '{topic}' that:
  - Targets these subtopics: {', '.join(theme_report.main_subtopics[:5])} (focus on top 5)
  - Uses primary keyword '{theme_report.primary_keyword}' in H1 naturally
  - Includes 4-6 H2 sections (not more!) with 1-2 H3s per H2 if needed
  - Targets {target_word_count} total words
  - Matches search intent: {theme_report.search_intent}
  - Addresses content gaps: {', '.join(theme_report.content_gaps[:2])}
  - Integrates unique angles: {', '.join(theme_report.unique_angles[:3]) if theme_report.unique_angles else 'none provided; infer 2 concrete differentiators from SERP gaps'}

CRITICAL CONSTRAINTS:
- Maximum 6 H2 sections total
- H3s are optional — only include if truly needed for clarity
- H1 intro is written separately and uses {self._INTRO_BUDGET} words.
  Your section budgets must therefore sum to exactly {section_budget} words.

STRICT MATH RULE
  sum(all word_budgets in the JSON) MUST equal {section_budget}.

  Budget guidance per heading level:
    • H2 block with no H3s  → 220–320 words
    • H2 block with H3s     → 240–360 words total
      (the H2 paragraph and its H3s must share this one block budget)

  Example for {target_word_count}-word article with 4 H2 blocks (2 with H3s):
  (intro = {self._INTRO_BUDGET} words, leaving {section_budget} for sections):
    Block 1 (H2 + H3s) = 325 words
    Block 2 (H2 + H3s) = 325 words
    Block 3 (H2 only)  = 325 words
    Block 4 (H2 only)  = 325 words
    Total section budgets = 1300 ✓  (equals {section_budget})

  Before returning JSON, verify:
    sum(section.word_budget for section in sections) == {section_budget}

Return structured JSON:
{{
  "h1": "string (the main heading)",
  "sections": [
    {{
      "h2": "string (section heading)",
      "word_budget": number (target words for this entire H2 block, INCLUDING any H3s),
      "h3s": ["string", ...]  (optional, max 2 per H2)
    }}
  ]
}}

IMPORTANT: Keep sections focused and avoid redundancy. Each section must cover
distinct, valuable information.

DIFFERENTIATION RULE:
- At least 2 H2 sections must explicitly represent unique angles not commonly covered
  in generic listicles for this topic."""

        return await self.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=ArticleOutline,
        )

    def _total_section_budget(self, outline: ArticleOutline) -> int:
        """Sum all word_budgets across sections."""
        return sum(s.word_budget for s in outline.sections)

    def _enforce_budget(self, outline: ArticleOutline, target: int) -> ArticleOutline:
        """Ensure section budgets sum to *target*.

        Steps
        -----
        1. Scale each budget proportionally when needed.
        2. Fix any rounding drift by adjusting the largest section.
        3. Guard against degenerate budgets (< 80 words) by redistributing.
        4. Always return with an exact sum of *target*.
        """
        current_total = self._total_section_budget(outline)
        if current_total == target:
            return outline

        # ── Step 1: proportional scale ────────────────────────────────
        if current_total == 0:
            # Pathological LLM output: distribute evenly
            per_section = target // max(len(outline.sections), 1)
            for s in outline.sections:
                s.word_budget = per_section
        else:
            scale = target / current_total
            for s in outline.sections:
                s.word_budget = max(80, round(s.word_budget * scale))

        # ── Step 2: fix rounding drift ────────────────────────────────
        scaled_total = self._total_section_budget(outline)
        drift = target - scaled_total
        if drift != 0 and outline.sections:
            # Add/subtract the rounding error from the largest section
            largest = max(outline.sections, key=lambda s: s.word_budget)
            largest.word_budget = max(80, largest.word_budget + drift)

        # ── Step 3: guard degenerate budgets ─────────────────────────
        for s in outline.sections:
            if s.word_budget < 80:
                s.word_budget = 80

        # Final drift correction after guard (budgets may have grown)
        final_total = self._total_section_budget(outline)
        final_drift = target - final_total
        if final_drift != 0 and outline.sections:
            if final_drift > 0:
                largest = max(outline.sections, key=lambda s: s.word_budget)
                largest.word_budget += final_drift
            else:
                # Reduce from largest sections first while preserving minimum floor.
                remaining = -final_drift
                for section in sorted(outline.sections, key=lambda s: s.word_budget, reverse=True):
                    reducible = max(0, section.word_budget - 80)
                    delta = min(reducible, remaining)
                    section.word_budget -= delta
                    remaining -= delta
                    if remaining == 0:
                        break

        print(
            f"[OutlineGenerator] Budget enforced: "
            f"LLM={current_total} → adjusted={self._total_section_budget(outline)} "
            f"(target={target})"
        )

        return outline