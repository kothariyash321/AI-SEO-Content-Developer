# TinyFish API Integration

The SEO Content Generation Platform now supports **TinyFish API** as the preferred method for fetching SERP (Search Engine Results Page) data.

## Why TinyFish?

- **Free/affordable** alternative to paid SERP APIs
- **Real search results** from Google (via DuckDuckGo)
- **No rate limits** (within your plan)
- **Same output format** as traditional SERP APIs

## Setup

### 1. Get Your TinyFish API Key

1. Sign up at [TinyFish](https://agent.tinyfish.ai) (or your TinyFish provider)
2. Get your API key from the dashboard
3. Add it to your `.env` file:

```bash
TINYFISH_API_KEY=your_tinyfish_api_key_here
```

### 2. Priority Order

The system tries APIs in this order:
1. **TinyFish API** (if `TINYFISH_API_KEY` is set) - **Preferred**
2. Legacy SERP API (SerpAPI/ValueSERP) - Fallback
3. Mock data - Development/testing only

### 3. How It Works

When you create a job, the system:
1. Calls TinyFish API with a goal prompt
2. TinyFish searches Google and returns real results
3. Results are parsed and used for competitive analysis
4. Theme extraction analyzes the real SERP data

## API Details

**Endpoint**: `https://agent.tinyfish.ai/v1/automation/run-sse`

**Method**: POST with Server-Sent Events (SSE) streaming

**Headers**:
- `X-API-Key`: Your TinyFish API key
- `Content-Type`: application/json

**Request Body**:
```json
{
  "url": "https://example.com/task",
  "goal": "Go to google.com and search for \"[TOPIC]\" and return the below output for only non-sponsored results on page 1 and 2\nRanking positions (1–10)\nPage titles\nSnippets/descriptions\nSource URLs"
}
```

**Response Format**:
```json
{
  "source": "DuckDuckGo",
  "results": [
    {
      "url": "https://example.com/article",
      "title": "Article Title",
      "snippet": "Article description...",
      "position": 1
    }
  ],
  "search_query": "your search topic"
}
```

## Testing

To test TinyFish integration:

1. Make sure `TINYFISH_API_KEY` is set in `.env`
2. Create a job via API:
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "AI in healthcare",
    "target_word_count": 1500,
    "language": "en"
  }'
```

3. Check the job status - it should use real Google search results!

## Troubleshooting

### "TinyFish API error"
- Check your API key is correct
- Verify you have credits/quota available
- Check network connectivity

### Falls back to mock data
- Ensure `TINYFISH_API_KEY` is in `.env`
- Restart the server after adding the key
- Check server logs for specific error messages

### Timeout errors
- TinyFish can take 30-60 seconds to return results
- The timeout is set to 60 seconds
- For very slow responses, you may need to increase timeout in `serp_adapter.py`

## Benefits Over Mock Data

✅ **Real competitive analysis** - See what's actually ranking  
✅ **Accurate keyword extraction** - Based on real search results  
✅ **Better content gaps** - Identify what competitors are missing  
✅ **Up-to-date information** - Always current search results  

## Migration from Legacy SERP APIs

If you were using SerpAPI or ValueSERP:
1. Add `TINYFISH_API_KEY` to `.env`
2. Remove or keep `SERP_API_KEY` (TinyFish takes priority)
3. Restart the server
4. That's it! The system automatically uses TinyFish
