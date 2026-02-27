# Design Decisions

This document outlines key architectural and implementation decisions made during the development of the SEO Content Generation Platform.

## 1. Step-Level Durability Over Job-Level

**Decision**: Each pipeline step commits its result independently to the database, rather than treating the entire pipeline as atomic.

**Rationale**: 
- A job that fails at step 6 can resume from step 6, not step 1
- Critical when SERP API calls have per-request costs
- Reduces wasted compute and API usage
- Provides better observability (can inspect partial results)

**Implementation**: The `pipeline_steps` table stores each step's status and result JSON. On restart, `AgentRunner` queries for the last completed step and resumes from the next one.

## 2. Pydantic v2 Throughout

**Decision**: Use Pydantic v2 for all schemas (API, internal agent data, DB serialization).

**Rationale**:
- Single source of truth for data shapes
- LLM JSON outputs are parsed directly into Pydantic models
- Parse failures are caught immediately and trigger re-prompts, not runtime errors downstream
- Type safety and validation at every layer
- Consistent serialization/deserialization

**Implementation**: All API schemas, agent intermediate data structures, and database JSON columns use Pydantic models.

## 3. Section-by-Section Article Drafting

**Decision**: Draft each H2 section independently with a word budget, rather than generating the entire article in one LLM call.

**Rationale**:
- More consistent quality across sections
- Avoids context window issues for long articles
- Allows section-level revision without regenerating the entire article
- Better control over word count distribution
- Can provide context from previous sections for coherence

**Implementation**: `ArticleDrafter.draft_article()` iterates through outline sections, calling `draft_section()` for each with appropriate word budgets.

## 4. Mock-First SERP Adapter

**Decision**: Design `SerpAdapter` as an interface with mock implementation that returns realistic fixture data.

**Rationale**:
- Allows full development and testing without consuming SERP API credits
- Makes the test suite deterministic and fast
- Enables offline development
- Graceful degradation: falls back to mock on API failure

**Implementation**: `SerpAdapter.fetch()` tries API first, falls back to `_get_mock_results()` on failure or if no API key is configured.

## 5. Quality Score Threshold with Revision Loop

**Decision**: If quality score < 70/100, pass failing constraints back to LLM drafter for revision. Maximum 2 revision attempts.

**Rationale**:
- Ensures minimum quality bar before accepting output
- Prevents infinite loops with max revision limit
- Provides specific, actionable feedback to LLM
- Balances quality with cost/compute time

**Implementation**: `AgentRunner.run()` scores after assembly, and if score < 70, calls `_revise_article()` up to 2 times before accepting the best result.

## 6. Async Job Dispatch

**Decision**: Use asyncio background tasks for job processing rather than Celery or a separate worker process.

**Rationale**:
- Simpler deployment (single process)
- Sufficient for MVP and moderate load
- Easier to debug and develop
- Can be upgraded to Celery/Redis later if needed

**Implementation**: `dispatch_job()` creates an asyncio task that runs `AgentRunner.run()` in the background.

## 7. SQLite for Development, PostgreSQL for Production

**Decision**: Support both SQLite (dev) and PostgreSQL (prod) via SQLAlchemy's async drivers.

**Rationale**:
- SQLite requires no setup for local development
- PostgreSQL provides production-grade features (concurrency, performance)
- SQLAlchemy abstracts the differences
- Easy to switch via `DATABASE_URL` environment variable

**Implementation**: `DATABASE_URL` defaults to SQLite, but can be set to PostgreSQL connection string. Both use async drivers (`aiosqlite`, `asyncpg`).

## 8. Structured Error Handling

**Decision**: Wrap external API calls (SERP, LLM) with retry logic and exponential backoff. Persist errors to database.

**Rationale**:
- External APIs are unreliable (network issues, rate limits)
- Retries handle transient failures
- Errors stored in `pipeline_steps.error` enable debugging
- Graceful degradation (fallback to mock SERP)

**Implementation**:
- SERP: 3 retries with 1s, 2s, 4s backoff, then fallback to mock
- LLM: 5 retries for rate limits (429), 2 retries for timeouts/5xx
- All errors logged to step record

## 9. Character Limit Enforcement in Metadata

**Decision**: Enforce 50-60 char title tag and 150-160 char meta description limits strictly.

**Rationale**:
- SEO best practices require these limits
- Search engines truncate longer metadata
- Quality scorer validates these constraints
- LLM prompts explicitly request these limits

**Implementation**: `MetadataBuilder` validates and truncates if needed. `QualityScorer` checks these limits and awards points accordingly.

## 10. Test Structure

**Decision**: Separate unit tests (agent components) from integration tests (full pipeline, API).

**Rationale**:
- Unit tests are fast and can mock LLM/SERP
- Integration tests validate end-to-end behavior
- Clear separation of concerns
- Can run unit tests frequently during development

**Implementation**: 
- `test_quality_scorer.py`: Unit tests for quality checks
- `test_api.py`: API endpoint tests
- `test_pipeline.py`: (To be added) Full pipeline integration tests with mocked LLM

## Future Considerations

1. **Celery/Redis**: If job volume increases, migrate to Celery with Redis for better scalability
2. **Caching**: Cache SERP results by topic to reduce API calls
3. **Streaming**: Stream article sections as they're generated for better UX
4. **FAQ Generator**: Implement bonus FAQ generation from "People Also Ask" SERP data
5. **Webhook Support**: Add webhook callbacks on job completion
6. **Job Dashboard**: Add `GET /jobs` endpoint with pagination and filtering
