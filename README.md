# 🧠 FeedbackIQ — Production-Grade Multi-Agent Feedback Intelligence Platform

> A continuously running, AI-powered internal platform that ingests user feedback from multiple external sources, processes it through a specialized multi-agent pipeline, enables human-in-the-loop review, generates structured tickets, and delivers real-time analytics, monitoring, and Telegram notifications.

---

## 🏗 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL SOURCES                                     │
│   GitHub Issues    Reddit Posts    Manual API Input    Google Play Reviews   │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Ingestion Agent   │  ← Thread-isolated BackgroundScheduler
                    │  (APScheduler)      │     Every 15 min
                    └──────────┬──────────┘
                               │  Writes to raw_feedback table
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LANGGRAPH MULTI-AGENT PIPELINE                           │
│                                                                             │
│   ┌─────────────────┐                                                       │
│   │  Translation    │ → language detection, English translation             │
│   │     Agent       │                                                       │
│   └────────┬────────┘                                                       │
│            │                                                                │
│   ┌────────▼────────┐                                                       │
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
    │  FastAPI     │   │  React Frontend  │   │  Telegram Bot    │
    │  REST API    │   │  Dashboard       │   │  Notifications   │
    │  /api/docs   │   │  localhost:3000  │   │  Success/Failure │
    └──────────────┘   └──────────────────┘   └──────────────────┘
              │                                        │
    ┌─────────▼─────────┐               ┌──────────────▼──────┐
    │  SlowAPI Rate     │               │  LangSmith          │
    │  Limiting         │               │  Observability      │
    │  100 req/min/IP   │               │  Agent Tracing      │
    └───────────────────┘               └─────────────────────┘
```

---

## 🤖 Agent Details

| Agent | Input | Output | LLM Used |
|---|---|---|---|
| **IngestionAgent** | GitHub/Reddit/Google Play/Manual APIs | `raw_feedback` DB records | No |
| **TranslationAgent** | Feedback text | language, is_english, translated_text | Gemini |
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
│   ├── main.py                  # FastAPI entry + rate limiting (SlowAPI)
│   ├── agents/                  # Multi-agent AI pipeline (8 agents)
│   ├── api/routes/              # REST endpoints (feedback, tickets, analytics, etc.)
│   ├── core/                    # Config, schemas, logging
│   ├── db/                      # Async SQLAlchemy models + engine
│   └── workers/
│       ├── scheduler.py         # Thread-isolated BackgroundScheduler
│       └── telegram.py          # Telegram Bot notification service
│
├── frontend/src/
│   ├── pages/                   # Overview, Feedback, Tickets, Analytics
│   ├── components/              # ui, charts, feedback, tickets, pipeline, monitoring
│   ├── layout/                  # Sidebar, TopBar (React Router)
│   ├── hooks/                   # useData (global polling hook)
│   └── utils/                   # Constants, date formatting, toast
│
└── docker-compose.yml           # PostgreSQL + Redis + Backend + Frontend
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
| `SECRET_KEY` | ✅ | Application secret key |
| `GEMINI_MODEL` | ❌ | Model name (default: `gemini-2.0-flash`) |
| `LANGCHAIN_API_KEY` | ❌ | LangSmith key for agent tracing |
| `LANGCHAIN_TRACING_V2` | ❌ | Enable LangSmith tracing (`true`/`false`) |
| `GITHUB_TOKEN` | ❌ | GitHub PAT for Issues ingestion & export |
| `GITHUB_REPO_OWNER` | ❌ | GitHub org/username |
| `GITHUB_REPO_NAME` | ❌ | GitHub repository name |
| `REDDIT_CLIENT_ID` | ❌ | Reddit app client ID |
| `REDDIT_CLIENT_SECRET` | ❌ | Reddit app client secret |
| `GOOGLE_PLAY_APP_ID` | ❌ | Google Play app to scrape reviews from |
| `GOOGLE_PLAY_REVIEW_COUNT` | ❌ | Number of reviews to fetch per cycle (default: `200`) |
| `INGESTION_ENABLED` | ❌ | Enable scheduled ingestion (default: `true`) |
| `INGESTION_INTERVAL_MINUTES` | ❌ | Polling interval (default: `15`) |
| `MAX_INGESTION_BATCH` | ❌ | Max feedbacks to AI-process per cycle (default: `200`) |
| `SCHEDULER_MAX_RUNTIME_MINUTES` | ❌ | Auto-stop scheduler after N minutes (default: `120`, `0` = forever) |
| `TELEGRAM_BOT_TOKEN` | ❌ | Telegram Bot API token for notifications |
| `TELEGRAM_CHAT_ID` | ❌ | Telegram chat ID to receive notifications |

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
| `POST` | `/api/ingestion/trigger` | Manually trigger full ingestion cycle |
| `POST` | `/api/ingestion/process-pending` | Manually trigger AI processing |
| `POST` | `/api/ingestion/trigger-google-play` | Manually trigger Google Play ingestion |
| `GET` | `/api/health` | Health check |

> **Rate Limiting**: All endpoints are rate-limited to **100 requests/minute per IP** via SlowAPI.

Full interactive docs: **http://localhost:8000/api/docs**

---

## 🖥 Frontend Dashboard

### Tech Stack
- **React 18** with React Router for multi-page navigation
- **Tailwind CSS v4** with custom design tokens (dark theme)
- **Vite** for fast development and HMR
- **IBM Plex Sans** + **JetBrains Mono** typography

### Pages

| Page | Features |
|---|---|
| **Overview** | KPI metrics, category/priority/sentiment distribution, pipeline diagram, source breakdown |
| **Feedback** | Full processed feedback table with filters, detail drawer, human review workflow |
| **Tickets** | Kanban-style ticket board grouped by priority, inline status editing, GitHub sync |
| **Analytics** | Category trend sparklines, top issues, duplicate groups |

### Component Architecture
```
components/
├── ui/          → Card, Btn, Badge, Spinner, MetricCard, Pagination, FilterSelect
├── charts/      → Sparkline data visualization
├── feedback/    → FeedbackRow, FeedbackDrawer, PendingFeedbackRow, SubmitModal
├── tickets/     → TicketCard with status management
├── pipeline/    → Agent pipeline visualization
├── monitoring/  → MonitoringPanel, RecentAgentRunsTable
└── ingestion/   → IngestionSourcesPanel with live polling
```

---

## ⏰ Automated Scheduling & Notifications

### Thread-Isolated Background Scheduler
The ingestion scheduler uses `APScheduler BackgroundScheduler` running in a **dedicated thread pool**, completely isolated from FastAPI's event loop. This ensures:

- ✅ **No missed jobs** — API traffic never delays scheduled ingestion
- ✅ **No overlapping runs** — `max_instances=1` prevents concurrent cycles
- ✅ **Coalesced misfires** — backed-up runs merge into a single execution
- ✅ **Automatic TTL** — scheduler auto-stops after 2 hours (configurable)
- ✅ **Immediate first run** — ingestion triggers on startup, then every 15 minutes

### Telegram Notifications
Real-time Telegram alerts for every scheduler event:

| Event | Notification |
|---|---|
| Scheduler starts | 🚀 Interval, TTL, timestamp |
| Cycle succeeds (new data) | ✅ Fetched, new, processed counts, duration |
| Cycle completes (no new data) | ℹ️ "No New Reviews available" with count checked |
| Cycle fails | ❌ Error message, source, retry info |
| Scheduler stops | 🛑 Total cycles completed, stop reason |

---

## 🔄 Data Flow (End-to-End)

```
 1. INGEST     External source → RawFeedback (PostgreSQL)
 2. TRANSLATE  Language detection → English translation if needed
 3. CLASSIFY   Gemini LLM → category, priority, confidence
 4. SENTIMENT  Gemini LLM → sentiment score + emotion tags
 5. DEDUP      TF-IDF cosine similarity → is_duplicate flag
 6. INSIGHTS   Gemini LLM → impact summary + resolution
 7. TICKET     Gemini LLM → structured ticket with labels
 8. PERSIST    ProcessedFeedback + Ticket + AgentRuns saved
 9. NOTIFY     Telegram Bot → cycle success/failure alert
10. REVIEW     Human analyst approves/rejects via dashboard
11. EXPORT     Approved tickets optionally pushed to GitHub Issues
12. ANALYZE    Analytics derived from PostgreSQL aggregations
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

## 🛡️ Security & Rate Limiting

| Feature | Implementation |
|---|---|
| **API Rate Limiting** | SlowAPI — 100 requests/minute per IP |
| **CORS Protection** | Whitelisted origins only |
| **GZip Compression** | Responses > 1KB auto-compressed |
| **Input Validation** | Pydantic schema validation on all endpoints |
| **Toxicity Moderation** | Configurable soft/extreme thresholds for content filtering |
| **Environment Secrets** | `.env` file with Pydantic Settings validation |

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

### Telegram Alerts
- Real-time push notifications for every ingestion cycle
- Zero-configuration — just add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

---

## 🚀 Production Deployment Checklist

- [x] Thread-isolated scheduler (ingestion doesn't block API)
- [x] API rate limiting (SlowAPI — 100 req/min/IP)
- [x] Telegram notifications for scheduler lifecycle
- [x] Auto-stop scheduler after configurable TTL
- [x] Heuristic fallback when LLM is unavailable
- [x] Content moderation with toxicity thresholds
- [x] GZip compression middleware
- [ ] Set a strong `SECRET_KEY`
- [ ] Use a managed PostgreSQL (e.g., RDS, Supabase, Neon)
- [ ] Set `DEBUG=false`
- [ ] Configure `CORS_ORIGINS` to your actual frontend domain
- [ ] Enable LangSmith tracing for agent observability
- [ ] Set up log aggregation (Datadog, CloudWatch, etc.)
- [ ] Add authentication (OAuth2/JWT) for the dashboard

---


