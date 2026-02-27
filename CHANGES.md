# Changes Made: Anthropic → OpenAI Migration

## Summary
The project has been migrated from Anthropic Claude to OpenAI GPT models.

## Changes

### 1. Dependencies (`requirements.txt`)
- ❌ Removed: `anthropic>=0.26.0`
- ✅ Added: `openai>=1.0.0`

### 2. Configuration (`app/config.py`)
- Changed `anthropic_api_key` → `openai_api_key`
- Changed default model from `claude-3-5-sonnet-20241022` → `gpt-4o`
- Model can be changed to `gpt-4-turbo` or `gpt-3.5-turbo` if needed

### 3. LLM Client (`app/agent/llm_client.py`)
- Replaced `AsyncAnthropic` with `AsyncOpenAI`
- Updated API call from `messages.create()` to `chat.completions.create()`
- Maintained same interface, so no changes needed in other agent modules

### 4. Documentation
- Updated `README.md` to reference OpenAI instead of Anthropic
- Updated `QUICKSTART.md` with OpenAI setup instructions
- Updated `docker-compose.yml` environment variable

### 5. Environment Variables
- Changed `ANTHROPIC_API_KEY` → `OPENAI_API_KEY`
- Default model: `gpt-4o` (can use `gpt-4-turbo` or `gpt-3.5-turbo` for cost savings)

## Setup Instructions

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Create `.env` file:**
```bash
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./seo_content.db
LLM_MODEL=gpt-4o
```

3. **Run migrations:**
```bash
alembic upgrade head
```

4. **Start server:**
```bash
uvicorn app.main:app --reload
```

Or use the provided scripts:
```bash
./setup.sh    # First time setup
./run.sh      # Run the server
```

## Model Options

You can change the model in `.env`:
- `gpt-4o` - Latest and most capable (recommended)
- `gpt-4-turbo` - Good balance of capability and cost
- `gpt-3.5-turbo` - Fastest and cheapest option

## API Compatibility

The OpenAI API interface is compatible with the existing agent pipeline. All prompts and response parsing remain the same.
