# SEO Content Generation Platform

An intelligent, agent-based SEO content generation service that ingests a topic, analyzes SERP data, and produces publish-ready articles with proper SEO metadata, heading hierarchy, and link strategies.

## Features

- **Multi-step Agent Pipeline**: SERP analysis → Theme extraction → Outline generation → Article drafting → Metadata & Links
- **Crash Durability**: Step-level persistence allows resuming from any point after a crash
- **Quality Scoring**: Automated SEO constraint validation with revision loops
- **Mock SERP Support**: Works without API keys for development and testing
- **RESTful API**: FastAPI-based endpoints for job submission and status tracking

## Architecture

The system follows a layered architecture:

- **API Layer**: FastAPI REST endpoints
- **Job Manager**: Async job dispatch and tracking
- **Agent Pipeline**: Multi-step content generation pipeline
- **SERP Adapter**: Fetches or mocks search engine results
- **LLM Client**: OpenAI integration
- **Quality Scorer**: SEO constraint validation
- **Persistence Layer**: SQLAlchemy with SQLite (dev) / PostgreSQL (prod)

## Prerequisites

- Python 3.11+
- OpenAI API key
- (Optional) SERP API key (SerpAPI or ValueSERP) - falls back to mock data if not provided

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd seo-content-agent
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

5. Run database migrations:
```bash
alembic upgrade head
```

## Running the Application

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## Usage

### Create a Job

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "best productivity tools for remote teams",
    "target_word_count": 1500,
    "language": "en"
  }'
```

Response:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending",
  "topic": "best productivity tools for remote teams",
  "created_at": "2025-02-20T10:00:00Z",
  "updated_at": "2025-02-20T10:00:00Z"
}
```

### Check Job Status

```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

While processing, returns job status. When completed, returns the full article output.

### Example Output

```json
{
  "job_id": "a1b2c3d4",
  "topic": "best productivity tools for remote teams",
  "sections": [
    {
      "heading_level": "H1",
      "heading_text": "Best Productivity Tools for Remote Teams",
      "content": "...",
      "word_count": 200
    }
  ],
  "seo_metadata": {
    "title_tag": "Best Productivity Tools for Remote Teams in 2025",
    "meta_description": "Discover the top productivity tools for remote teams...",
    "primary_keyword": "productivity tools for remote teams",
    "secondary_keywords": ["remote collaboration tools", ...]
  },
  "internal_links": [...],
  "external_references": [...],
  "quality_score": {
    "total": 88,
    "passed_checks": 8,
    "failed_checks": 1
  },
  "total_word_count": 1487
}
```

## Testing

Run the test suite:
```bash
pytest -v
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

## Project Structure

```
seo-content-agent/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings management
│   ├── api/
│   │   ├── routes.py        # API endpoints
│   │   └── schemas.py       # Pydantic schemas
│   ├── agent/
│   │   ├── pipeline.py      # Main pipeline orchestrator
│   │   ├── llm_client.py    # LLM client wrapper
│   │   ├── serp_adapter.py  # SERP data fetcher
│   │   ├── theme_extractor.py
│   │   ├── outline_generator.py
│   │   ├── article_drafter.py
│   │   ├── metadata_builder.py
│   │   ├── link_strategist.py
│   │   └── quality_scorer.py
│   ├── db/
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── session.py       # DB session management
│   │   └── crud.py          # CRUD operations
│   └── jobs/
│       └── dispatcher.py     # Job dispatch logic
├── alembic/                 # Database migrations
├── tests/                    # Test suite
├── examples/                 # Example inputs/outputs
├── requirements.txt
└── README.md
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | Database connection string | No (defaults to SQLite) |
| `OPENAI_API_KEY` | OpenAI API key | Yes |
| `TINYFISH_API_KEY` | TinyFish API key (preferred for SERP) | No |
| `SERP_API_KEY` | Legacy SERP API key (optional) | No |
| `SERP_API_PROVIDER` | `serpapi` or `valueserp` | No |
| `ENVIRONMENT` | `development` or `production` | No |
| `LOG_LEVEL` | Logging level | No |

## Error Handling

- **SERP API Failures**: Falls back to mock data after 3 retries with exponential backoff
- **LLM API Failures**: Retries up to 5 times with exponential backoff on rate limits
- **Job Durability**: Each pipeline step persists its result. On restart, the pipeline resumes from the last completed step
- **Quality Scoring**: If score < 70, the system attempts up to 2 revision passes

## Design Decisions

1. **Step-Level Durability**: Each pipeline step commits independently, allowing resume from any point
2. **Pydantic v2**: Single source of truth for data shapes across API, internal logic, and DB
3. **Section-by-Section Drafting**: Each H2 section is drafted independently for better quality and consistency
4. **Mock-First SERP**: Mock adapter allows full development and testing without API costs
5. **Quality Threshold**: Revision loop with max 2 attempts prevents infinite loops

## Development

### Running Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Code Style

The project uses:
- Black for code formatting (recommended)
- Pydantic v2 for validation
- Type hints throughout

## License

[Your License Here]

## Contributing

[Contributing Guidelines]
