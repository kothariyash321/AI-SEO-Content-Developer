# Quick Start Guide

Get the SEO Content Generation Platform up and running in minutes.

## Prerequisites

- Python 3.11 or higher
- OpenAI API key (get one at https://platform.openai.com/api-keys)

## Setup (5 minutes)

1. **Clone and navigate to the project:**
```bash
cd "Podium Assignment"
```

2. **Create virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

Edit `.env`:
```
OPENAI_API_KEY=your_key_here
DATABASE_URL=sqlite+aiosqlite:///./seo_content.db
```

5. **Initialize database:**
```bash
alembic upgrade head
```

## Run the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## Create Your First Article

### Using curl:

```bash
# Create a job
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "best productivity tools for remote teams",
    "target_word_count": 1500,
    "language": "en"
  }'

# Save the job_id from the response, then check status:
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

### Using the API docs:

1. Go to `http://localhost:8000/docs`
2. Click on `POST /api/v1/jobs`
3. Click "Try it out"
4. Enter your topic and word count
5. Click "Execute"
6. Copy the `job_id` from the response
7. Use `GET /api/v1/jobs/{job_id}` to check status and get the article when complete

## Expected Processing Time

- **SERP Fetch**: ~1-2 seconds (or instant with mock)
- **Theme Extraction**: ~5-10 seconds
- **Outline Generation**: ~5-10 seconds
- **Article Drafting**: ~30-60 seconds (depends on number of sections)
- **Metadata Generation**: ~5-10 seconds
- **Link Strategy**: ~5-10 seconds
- **Quality Scoring**: <1 second

**Total**: Approximately 1-2 minutes for a 1500-word article

## Troubleshooting

### "Module not found" errors
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again

### "OPENAI_API_KEY not found"
- Check your `.env` file exists and has the key
- Make sure you're running from the project root directory

### Database errors
- Run `alembic upgrade head` to create tables
- Check `DATABASE_URL` in `.env` is correct

### Job stuck in "pending" or "running"
- Check server logs for errors
- Verify your OpenAI API key is valid and has credits
- Check database connection

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [design_decisions.md](design_decisions.md) for architecture details
- See [examples/productivity_tools/](examples/productivity_tools/) for example usage
