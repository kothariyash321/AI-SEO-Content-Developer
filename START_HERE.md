# 🚀 Start Here - Quick Setup & Run

Your `.env` file has been created with your OpenAI API key! 

## Step 1: Install Dependencies

Open your terminal and run:

```bash
cd "/Users/yash/Downloads/Podium Assignment"

# Install all required packages
pip3 install -r requirements.txt
```

If you get permission errors, use:
```bash
pip3 install --user -r requirements.txt
```

Or create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2: Initialize Database

```bash
alembic upgrade head
```

## Step 3: Start the Server

```bash
uvicorn app.main:app --reload
```

Or if using virtual environment:
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

## Step 4: Test the API

Once the server is running, open your browser:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Root**: http://localhost:8000

## Step 5: Create Your First Article

### Option A: Using the API Docs (Easiest)
1. Go to http://localhost:8000/docs
2. Click on `POST /api/v1/jobs`
3. Click "Try it out"
4. Enter:
   ```json
   {
     "topic": "best productivity tools for remote teams",
     "target_word_count": 1500,
     "language": "en"
   }
   ```
5. Click "Execute"
6. Copy the `job_id` from the response
7. Use `GET /api/v1/jobs/{job_id}` to check status and get the article when complete

### Option B: Using curl
```bash
# Create a job
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "best productivity tools for remote teams",
    "target_word_count": 1500,
    "language": "en"
  }'

# Check status (replace {job_id} with the ID from above)
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

## Troubleshooting

### "Module not found" errors
- Make sure you've run `pip install -r requirements.txt`
- If using venv, make sure it's activated: `source venv/bin/activate`

### "OPENAI_API_KEY not found"
- The .env file should already be created with your key
- Make sure you're in the project directory

### Database errors
- Run `alembic upgrade head` to create tables

### Port already in use
- Change the port: `uvicorn app.main:app --reload --port 8001`

## Expected Processing Time

- **SERP Fetch**: ~1-2 seconds (uses mock data)
- **Theme Extraction**: ~5-10 seconds
- **Outline Generation**: ~5-10 seconds  
- **Article Drafting**: ~30-60 seconds (depends on sections)
- **Metadata Generation**: ~5-10 seconds
- **Link Strategy**: ~5-10 seconds
- **Quality Scoring**: <1 second

**Total**: Approximately 1-2 minutes for a 1500-word article

---

✅ Your `.env` file is ready with your OpenAI API key!
✅ Just install dependencies and run the server!
