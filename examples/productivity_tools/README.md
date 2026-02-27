# Productivity Tools Example

This directory contains an example input and expected output for the SEO content generation platform.

## Input

See `input.json` for the request payload.

## Expected Output Structure

The output will be a complete `ArticleOutput` JSON with:
- Article sections (H1, H2, H3) with content
- SEO metadata (title tag, meta description, keywords)
- Internal link suggestions (3-5 links)
- External references (2-4 citations)
- Quality score report
- Total word count

## Running the Example

1. Start the API server:
```bash
uvicorn app.main:app --reload
```

2. Submit the job:
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d @input.json
```

3. Poll for completion:
```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

Replace `{job_id}` with the ID returned from step 2.
