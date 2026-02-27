"""FAQ generation from SERP data."""
from app.agent.llm_client import LLMClient
from app.api.schemas import SerpResult, FAQItem


class FAQGenerator:
    """Generate FAQ section from SERP results."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def generate(
        self,
        topic: str,
        serp_results: list[SerpResult],
        article_sections: list,
    ) -> list[FAQItem]:
        """Generate FAQ items from SERP data and article content."""
        # Extract potential questions from SERP titles and snippets
        # SERP titles often contain questions or question-like phrases
        potential_questions = []
        for result in serp_results[:10]:
            title = result.title
            snippet = result.snippet
            
            # Look for question patterns in titles
            if any(q_word in title.lower() for q_word in ['what', 'how', 'why', 'when', 'where', 'which', 'who', '?']):
                potential_questions.append(title)
            # Also extract from snippets
            if '?' in snippet:
                # Extract question-like phrases
                sentences = snippet.split('.')
                for sentence in sentences:
                    if '?' in sentence:
                        potential_questions.append(sentence.strip())
        
        # Format for LLM
        serp_context = "\n".join([
            f"Rank {r.rank}: {r.title} - {r.snippet[:100]}"
            for r in serp_results[:10]
        ])
        
        system_prompt = """You are an SEO content strategist. Generate FAQ questions and answers based on search results and article content.
Return valid JSON matching the specified schema. Create questions that people actually search for."""
        
        user_prompt = f"""Based on these SERP results for '{topic}':

{serp_context}

And the article sections covering: {', '.join([s.heading_text for s in article_sections[:5]])}

Generate 5-7 FAQ questions and concise answers (2-3 sentences each) that:
- Address common questions people have about '{topic}'
- Are based on what's actually ranking in search results
- Provide valuable, concise answers
- Use natural question phrasing (not keyword-stuffed)
- REJECT overly generic questions with weak search intent (e.g., "Why is this important?")
- Prefer specific questions with tool names, team size, pricing, or clear use-case constraints
- Good example: "Is Notion or Asana better for remote teams under 10 people?"
- Bad example: "Why are productivity tools important?"

Return JSON object with this structure:
{{
  "faq_items": [
    {{
      "question": "string (natural question people would ask)",
      "answer": "string (2-3 sentence answer)"
    }}
  ]
}}

Focus on questions that appear in search results or are naturally related to the topic."""
        
        from pydantic import BaseModel
        
        class FAQResponse(BaseModel):
            faq_items: list[dict]
        
        try:
            result = await self.llm_client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=FAQResponse,
            )
            
            # Convert to FAQItem objects
            faq_items = [
                FAQItem(question=item["question"], answer=item["answer"])
                for item in result.faq_items
            ]

            filtered = [item for item in faq_items if not self._is_generic_question(item.question)]
            return filtered[:7]
        except Exception as e:
            # Fallback: try parsing as direct list if model parsing fails
            try:
                import json
                raw_response = await self.llm_client.generate(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_format=None,  # Get raw response
                )
                # Try to parse as JSON array directly
                data = json.loads(raw_response.strip().strip("```json").strip("```").strip())
                if isinstance(data, list):
                    faq_items = [
                        FAQItem(question=item["question"], answer=item["answer"])
                        for item in data
                    ]
                    return faq_items
            except Exception:
                pass
            
            # If all else fails, raise original error
            raise e

    def _is_generic_question(self, question: str) -> bool:
        """Filter out low-intent FAQ questions that are too broad to rank."""
        q = question.lower().strip()
        generic_starts = [
            "why are",
            "what are",
            "how do i choose",
        ]
        weak_phrases = [
            "important",
            "benefits",
            "what is",
        ]

        if any(q.startswith(prefix) for prefix in generic_starts) and len(q.split()) <= 10:
            return True
        if any(phrase in q for phrase in weak_phrases) and not any(ch.isdigit() for ch in q):
            # Allow if specificity hints exist.
            if not any(token in q for token in ["for ", "vs", "under", "cost", "price", "best "]):
                return True
        return False
