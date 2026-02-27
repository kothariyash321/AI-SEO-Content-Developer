"""SERP (Search Engine Results Page) adapter for fetching search results."""
import json
import asyncio
from typing import Any

import httpx

from app.api.schemas import SerpResult
from app.config import settings


class SerpAdapter:
    """Adapter for fetching SERP data from APIs or mock data."""
    
    def __init__(self):
        self.api_key = settings.serp_api_key
        self.provider = settings.serp_api_provider
        self.tinyfish_api_key = settings.tinyfish_api_key
    
    async def fetch(self, topic: str, max_results: int = 10) -> list[SerpResult]:
        """
        Fetch SERP results for a topic.
        
        Priority:
        1. TinyFish API (if configured)
        2. Legacy SERP API (SerpAPI/ValueSERP)
        3. Mock data (fallback)
        """
        # Try TinyFish first (preferred)
        if self.tinyfish_api_key:
            try:
                # Fail fast if TinyFish is slow/unreachable, then fallback.
                return await asyncio.wait_for(
                    self._fetch_tinyfish(topic, max_results),
                    timeout=20.0,
                )
            except Exception as e:
                print(f"TinyFish API error: {e}, trying fallback...")
                # Fall through to next option
        
        # Try legacy SERP API
        if self.api_key:
            try:
                return await self._fetch_from_api(topic, max_results)
            except Exception as e:
                print(f"SERP API error: {e}, falling back to mock data")
                return self._get_mock_results(topic, max_results)
        
        # Fallback to mock
        return self._get_mock_results(topic, max_results)
    
    async def _fetch_tinyfish(self, topic: str, max_results: int) -> list[SerpResult]:
        """Fetch results from TinyFish API using the exact prompt format from user's working example."""
        # Use the EXACT prompt format that works - matching user's provided code
        goal = f'Go to google.com and search for "{topic}" and return the below output for only non-sponsored results on page 1 and 2\nRanking positions (1–10)\nPage titles\nSnippets/descriptions\nSource URLs'
        
        async with httpx.AsyncClient(timeout=20.0, trust_env=False) as client:
            async with client.stream(
                'POST',
                'https://agent.tinyfish.ai/v1/automation/run-sse',
                headers={
                    'X-API-Key': self.tinyfish_api_key,
                    'Content-Type': 'application/json',
                },
                json={
                    'url': "https://example.com/task",
                    'goal': goal,
                },
            ) as response:
                response.raise_for_status()
                
                # Parse SSE stream (httpx.aiter_lines() yields str, not bytes).
                raw_lines: list[str] = []
                final_data = None

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    raw_lines.append(line)

                    # Server-Sent Events commonly emit payloads as: "data: {...}"
                    payload = line
                    if line.startswith("data:"):
                        payload = line[5:].strip()
                    if payload == "[DONE]":
                        break

                    candidate = self._extract_results_payload(payload)
                    if candidate:
                        final_data = candidate
                        break

                # Fallback: attempt parsing from all collected lines if no direct hit
                if not final_data and raw_lines:
                    combined = "\n".join(raw_lines)
                    final_data = self._extract_results_payload(combined)
                
                if not final_data or 'results' not in final_data:
                    preview = "\n".join(raw_lines)[:500]
                    raise ValueError(f"Could not parse TinyFish response. Buffer preview: {preview}")
                
                return self._parse_tinyfish_response(final_data, max_results)

    def _extract_results_payload(self, text: str) -> dict[str, Any] | None:
        """Try multiple parse strategies and return the first dict containing `results`."""
        if not text:
            return None

        def find_results(obj: Any) -> dict[str, Any] | None:
            if isinstance(obj, dict):
                results = obj.get("results")
                if isinstance(results, list):
                    return obj
                for value in obj.values():
                    found = find_results(value)
                    if found:
                        return found
            elif isinstance(obj, list):
                for item in obj:
                    found = find_results(item)
                    if found:
                        return found
            return None

        # 1) Direct JSON parse
        try:
            parsed = json.loads(text)
            found = find_results(parsed)
            if found:
                return found
        except json.JSONDecodeError:
            pass

        # 2) Scan line-by-line for embedded JSON snippets
        for line in text.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            if candidate.startswith("data:"):
                candidate = candidate[5:].strip()
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
                found = find_results(parsed)
                if found:
                    return found
            except json.JSONDecodeError:
                continue

        return None
    
    def _parse_tinyfish_response(self, data: dict, max_results: int) -> list[SerpResult]:
        """Parse TinyFish API response into SerpResult objects."""
        results = []
        
        # Extract results from response
        search_results = data.get('results', [])
        
        for item in search_results[:max_results]:
            # TinyFish uses 'position', we need to map to 'rank'
            position = item.get('position', len(results) + 1)
            
            results.append(SerpResult(
                rank=position,
                url=item.get('url', ''),
                title=item.get('title', ''),
                snippet=item.get('snippet', ''),
            ))
        
        # Sort by rank to ensure proper ordering
        results.sort(key=lambda x: x.rank)
        
        return results
    
    async def _fetch_from_api(self, topic: str, max_results: int) -> list[SerpResult]:
        """Fetch results from actual SERP API (legacy)."""
        if self.provider == "serpapi":
            return await self._fetch_serpapi(topic, max_results)
        elif self.provider == "valueserp":
            return await self._fetch_valueserp(topic, max_results)
        else:
            raise ValueError(f"Unknown SERP provider: {self.provider}")
    
    async def _fetch_serpapi(self, topic: str, max_results: int) -> list[SerpResult]:
        """Fetch from SerpAPI (legacy)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": topic,
                    "api_key": self.api_key,
                    "engine": "google",
                    "num": max_results,
                }
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for idx, item in enumerate(data.get("organic_results", [])[:max_results], 1):
                results.append(SerpResult(
                    rank=idx,
                    url=item.get("link", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                ))
            
            return results
    
    async def _fetch_valueserp(self, topic: str, max_results: int) -> list[SerpResult]:
        """Fetch from ValueSERP (legacy)."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://api.valueserp.com/search",
                params={
                    "q": topic,
                    "api_key": self.api_key,
                    "num": max_results,
                }
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for idx, item in enumerate(data.get("organic_results", [])[:max_results], 1):
                results.append(SerpResult(
                    rank=idx,
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("snippet", ""),
                ))
            
            return results
    
    def _get_mock_results(self, topic: str, max_results: int) -> list[SerpResult]:
        """
        Generate realistic mock SERP results.
        
        This provides deterministic test data when API is unavailable.
        """
        # Generate mock results based on topic
        mock_results = []
        
        # Common mock data patterns
        base_urls = [
            "https://example.com",
            "https://techcrunch.com",
            "https://medium.com",
            "https://wikipedia.org",
            "https://forbes.com",
            "https://hbr.org",
            "https://techradar.com",
            "https://zdnet.com",
            "https://theverge.com",
            "https://arstechnica.com",
        ]
        
        base_titles = [
            f"Complete Guide to {topic.title()}",
            f"Best {topic.title()} in 2025",
            f"Everything You Need to Know About {topic.title()}",
            f"{topic.title()}: A Comprehensive Overview",
            f"Top 10 {topic.title()} Solutions",
            f"How to Choose the Right {topic.title()}",
            f"{topic.title()} Explained: Expert Insights",
            f"The Ultimate {topic.title()} Handbook",
            f"{topic.title()}: Tips, Tricks, and Best Practices",
            f"Understanding {topic.title()}: A Deep Dive",
        ]
        
        base_snippets = [
            f"Discover the most effective {topic} strategies and tools. Our comprehensive guide covers everything from basics to advanced techniques.",
            f"Looking for the best {topic}? We've reviewed dozens of options to help you make an informed decision.",
            f"Learn everything about {topic} with our detailed guide. Includes expert tips, common pitfalls, and actionable advice.",
            f"This comprehensive resource covers all aspects of {topic}, from fundamental concepts to real-world applications.",
            f"Explore the top-rated {topic} solutions available today. Compare features, pricing, and user reviews.",
            f"Master {topic} with our step-by-step guide. Perfect for beginners and experienced users alike.",
            f"Get expert insights on {topic}. Learn from industry leaders and discover proven strategies.",
            f"Your complete resource for {topic}. Includes tutorials, comparisons, and recommendations.",
            f"Everything you need to know about {topic} in one place. Updated regularly with the latest information.",
            f"Navigate the world of {topic} with confidence. Our guide provides clear explanations and practical examples.",
        ]
        
        for i in range(min(max_results, 10)):
            mock_results.append(SerpResult(
                rank=i + 1,
                url=f"{base_urls[i % len(base_urls)]}/{topic.replace(' ', '-').lower()}",
                title=base_titles[i % len(base_titles)],
                snippet=base_snippets[i % len(base_snippets)],
            ))
        
        return mock_results
