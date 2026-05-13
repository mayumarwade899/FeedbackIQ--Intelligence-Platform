# 🧠 FeedbackIQ — Production-Grade Multi-Agent Feedback Intelligence Platform

> A continuously running, AI-powered internal platform that ingests user feedback from multiple external sources, processes it through a specialized multi-agent pipeline, enables human-in-the-loop review, generates structured tickets, and delivers real-time analytics and monitoring.

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SOURCES                                     │
│   GitHub Issues    Reddit Posts    Manual API Input    App Reviews           │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Ingestion Agent   │  ← Scheduled every N minutes
                    │  (APScheduler)      │     Deduplication by external_id
                    └──────────┬──────────┘
                               │  Writes to raw_feedback table
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH MULTI-AGENT PIPELINE                           │
│                                                                             │
│   ┌─────────────────┐                                                       │
│   │  Classification │ → category, priority, confidence, rationale           │
│   │     Agent       │                                                       │
│   └────────┬────────┘                                                       │
│            │ conditional routing                                            │
│     Spam? → END     else continue                                           │
│            │                                                                │
│   ┌────────▼────────┐                                                       │
│   │   Sentiment     │ → sentiment, sentiment_score, emotion_tags            │
│   │     Agent       │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                │
│   ┌────────▼────────┐                                                       │
│   │   Duplicate     │ → is_duplicate, similarity_score, embedding           │
│   │ Detection Agent │   (TF-IDF vector cosine similarity)                  │
│   └────────┬────────┘                                                       │
│            │ duplicate? → END     else continue                             │
│            │                                                                │
│   ┌────────▼────────┐                                                       │
│   │    Insights     │ → impact_summary, suggested_resolution, key_phrases   │
│   │     Agent       │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                │
│   ┌────────▼────────┐                                                       │
│   │ Ticket Generation│ → ticket_title, ticket_description, labels           │
│   │     Agent       │                                                       │
│   └────────┬────────┘                                                       │
└────────────┼────────────────────────────────────────────────────────────────┘
             │  Writes to: processed_feedback, tickets, agent_runs tables
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         POSTGRESQL DATABASE                                  │
│  raw_feedback | processed_feedback | tickets | agent_runs | ingestion_runs  │
└────────────────────────────────┬────────────────────────────────────────────┘
                                 │
              ┌──────────────────┼──────────────────────┐
              ▼                  ▼                       ▼
    ┌──────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │  FastAPI     │   │  React Frontend  │   │  LangSmith       │
    │  REST API    │   │  Dashboard       │   │  Observability   │
    │  /api/docs   │   │  localhost:3000  │   │  Agent Tracing   │
    └──────────────┘   └──────────────────┘   └──────────────────┘
```

---

## 🤖 Agent Details

| Agent | Input | Output | LLM Used |
|---|---|---|---|
| **IngestionAgent** | GitHub/Reddit/Manual APIs | `raw_feedback` DB records | No |
| **ClassificationAgent** | Feedback text | category, priority, confidence | Gemini |
| **SentimentAgent** | Feedback text | sentiment, score, emotion_tags | Gemini |
| **DuplicateDetectionAgent** | Feedback embedding | is_duplicate, similarity_score | No (vector math) |
| **InsightsAgent** | Text + classification | impact_summary, resolution, key_phrases | Gemini |
| **TicketGenerationAgent** | All enriched data | ticket title, description, labels | Gemini |
| **Orchestrator** | Raw feedback record | Orchestrates full pipeline via LangGraph | — |

All agents inherit from `BaseAgent` which provides:
- ✅ Retry logic (configurable retries with exponential backoff)
- ✅ Latency tracking (per-agent, stored in `agent_runs`)
- ✅ Error capture (non-crashing — errors noted in state)
- ✅ LangSmith trace injection
- ✅ Heuristic fallback when LLM is unavailable

---

## 📂 Project Structure

```
feedback-platform/
├── backend/
│   ├── main.py                          # FastAPI app with lifespan
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── alembic/                         # DB migrations
│   │   └── env.py
│   ├── agents/
│   │   ├── base.py                      # BaseAgent with retry + monitoring
│   │   ├── llm_client.py               # Gemini wrapper with JSON parsing
│   │   ├── orchestrator.py             # LangGraph StateGraph pipeline
│   │   ├── classification_agent.py
│   │   ├── sentiment_agent.py
│   │   ├── duplicate_detection_agent.py
│   │   ├── insights_agent.py
│   │   ├── ticket_generation_agent.py
│   │   └── ingestion_agent.py          # GitHub, Reddit, Manual sources
│   ├── api/
│   │   └── routes/
│   │       ├── feedback.py             # /api/feedback/*
│   │       ├── tickets.py              # /api/tickets/*
│   │       ├── analytics.py            # /api/analytics/*
│   │       ├── monitoring.py           # /api/monitoring/*
│   │       ├── agents.py               # /api/agents/*
│   │       └── ingestion.py            # /api/ingestion/*
│   ├── core/
│   │   ├── config.py                   # Pydantic Settings
│   │   ├── schemas.py                  # API schemas + AgentState TypedDict
│   │   └── logging_config.py
│   ├── db/
│   │   ├── database.py                 # Async SQLAlchemy engine
│   │   └── models.py                   # ORM models
│   └── workers/
│       └── scheduler.py                # APScheduler background jobs
│
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│       ├── main.jsx
│       └── App.jsx                     # Complete single-file React dashboard
│
└── docker-compose.yml
```

---

## ⚙️ Setup & Running

### Prerequisites
- Python 3.11+
- Node.js 20+
- PostgreSQL 14+ (or Docker)
- Google Gemini API key

### Option A — Docker Compose (Recommended)

```bash
# 1. Clone and enter project
git clone <your-repo>
cd feedback-platform

# 2. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# 3. Start everything
docker-compose up -d

# 4. Open the dashboard
open http://localhost:3000
# API docs: http://localhost:8000/api/docs
```

### Option B — Local Development

```bash
# ── Backend ──────────────────────────────────────────────────
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY and DATABASE_URL

# Start PostgreSQL (if not using Docker)
# Update DATABASE_URL in .env accordingly

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn main:app --reload --port 8000

# ── Frontend ──────────────────────────────────────────────────
cd ../frontend
npm install
npm run dev                        # Opens on http://localhost:3000
```

---

## 🔑 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL async connection string |
| `GOOGLE_API_KEY` | ✅ | Gemini API key for agent LLM calls |
| `GEMINI_MODEL` | ❌ | Model name (default: `gemini-2.0-flash`) |
| `LANGCHAIN_API_KEY` | ❌ | LangSmith key for agent tracing |
| `LANGCHAIN_TRACING_V2` | ❌ | Enable LangSmith tracing (`true`/`false`) |
| `GITHUB_TOKEN` | ❌ | GitHub PAT for Issues ingestion & export |
| `GITHUB_REPO_OWNER` | ❌ | GitHub org/username |
| `GITHUB_REPO_NAME` | ❌ | GitHub repository name |
| `REDDIT_CLIENT_ID` | ❌ | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | ❌ | Reddit app client secret |
| `INGESTION_ENABLED` | ❌ | Enable scheduled ingestion (default: `true`) |
| `INGESTION_INTERVAL_MINUTES` | ❌ | Polling interval (default: `15`) |
| `SECRET_KEY` | ✅ | Application secret key |

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/feedback/submit` | Submit feedback (triggers pipeline) |
| `GET` | `/api/feedback/raw` | List raw ingested feedback |
| `GET` | `/api/feedback/processed` | List AI-processed feedback |
| `GET` | `/api/feedback/processed/{id}` | Get single processed feedback |
| `POST` | `/api/feedback/processed/{id}/review` | Human review decision |
| `GET` | `/api/tickets` | List generated tickets |
| `PATCH` | `/api/tickets/{id}` | Update ticket |
| `POST` | `/api/tickets/{id}/sync-github` | Push ticket to GitHub Issues |
| `GET` | `/api/analytics/overview` | Platform metrics summary |
| `GET` | `/api/analytics/trends` | Category/sentiment trend data |
| `GET` | `/api/analytics/duplicates` | Duplicate feedback groups |
| `GET` | `/api/monitoring/metrics` | Agent performance metrics |
| `GET` | `/api/monitoring/agent-runs` | Agent execution log |
| `GET` | `/api/agents` | List all agents |
| `POST` | `/api/ingestion/trigger` | Manually trigger ingestion |
| `GET` | `/api/health` | Health check |

Full interactive docs: **http://localhost:8000/api/docs**

---

## 🖥 Frontend Dashboard Pages

| Page | Features |
|---|---|
| **Overview** | KPI metrics, category/priority/sentiment distribution, pipeline diagram, source breakdown |
| **Feedback** | Full processed feedback table with filters, detail drawer, human review workflow |
| **Tickets** | Kanban-style ticket board grouped by priority, inline status editing, GitHub sync |
| **Analytics** | Category trend sparklines, top issues, duplicate groups |
| **Monitoring** | Agent success rates, latency heatmap, recent agent run logs |

---

## 🔄 Data Flow (End-to-End)

```
1. INGEST     External source → RawFeedback (PostgreSQL)
2. CLASSIFY   Gemini LLM → category, priority, confidence
3. SENTIMENT  Gemini LLM → sentiment score + emotion tags  
4. DEDUP      TF-IDF cosine similarity → is_duplicate flag
5. INSIGHTS   Gemini LLM → impact summary + resolution
6. TICKET     Gemini LLM → structured ticket with labels
7. PERSIST    ProcessedFeedback + Ticket + AgentRuns saved
8. REVIEW     Human analyst approves/rejects via dashboard
9. EXPORT     Approved tickets optionally pushed to GitHub Issues
10. ANALYZE   Analytics derived from PostgreSQL aggregations
```

---

## 📊 Database Schema

```sql
raw_feedback          -- Source data, dedup by external_id
processed_feedback    -- AI enrichments, review state, embeddings
tickets               -- Generated tickets, GitHub sync state
agent_runs            -- Per-agent execution traces (latency, errors)
ingestion_runs        -- Scheduled job execution history
```

---

## 🔭 Observability

### LangSmith Integration
- Set `LANGCHAIN_API_KEY` and `LANGCHAIN_TRACING_V2=true`
- Every agent invocation is traced with input/output, latency, tokens
- View traces at https://smith.langchain.com

### Built-in Metrics (no external tools required)
- Per-agent success rate, avg latency → stored in `agent_runs`
- Processing throughput, duplicate rate → derived from DB queries
- All metrics exposed via `/api/monitoring/metrics`

---

## 🚀 Production Deployment Checklist

- [ ] Set a strong `SECRET_KEY`
- [ ] Use a managed PostgreSQL (e.g., RDS, Supabase, Neon)
- [ ] Set `DEBUG=false`
- [ ] Configure `CORS_ORIGINS` to your actual frontend domain
- [ ] Enable LangSmith tracing for agent observability
- [ ] Set up log aggregation (Datadog, CloudWatch, etc.)
- [ ] Add rate limiting to `/api/feedback/submit`
- [ ] Configure `INGESTION_INTERVAL_MINUTES` based on load
- [ ] Add authentication (OAuth2/JWT) for the dashboard

---

## 🗺 Roadmap

- [ ] **Memory Agent**: Summarize recurring feedback themes into long-term context
- [ ] **Webhook support**: Push ticket events to Slack / PagerDuty
- [ ] **Auth**: JWT-based login for reviewers
- [ ] **Batch ML retraining**: Fine-tune classification based on human corrections
- [ ] **More sources**: Zendesk, Intercom, App Store reviews API
- [ ] **Export**: CSV / PDF report generation

---

## 👤 Author

Built as a production-grade reference architecture for multi-agent AI systems.
