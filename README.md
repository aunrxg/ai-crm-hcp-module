# AI-First CRM HCP Module

### LogInteractionScreen — LangGraph · Groq · FastAPI · React · PostgreSQL

> A pharma sales CRM module where field representatives log interactions with Healthcare Professionals (HCPs) through a conversational AI agent. The form panel updates automatically in real time — the rep never edits fields directly.

---

## 📸 Screen Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🏥 CRM HCP                     Log Interaction    Apr 21 2026  │
├─────────────────────────────────────────────────────────────────┤
│  🔍  Dr. Priya Sharma  ·  Cardiology  ·  Apollo Mumbai  [T1]   │
├───────────────────────────┬─────────────────────────────────────┤
│                           │                                     │
│   💬  AI ASSISTANT        │   📋  INTERACTION FORM (READ-ONLY) │
│   ─────────────────────   │   ──────────────────────────────── │
│                           │                                     │
│   > Just visited Dr.      │   Type        Visit                │
│     Sharma at Apollo...   │   Date        21 Apr 2026          │
│                           │   Duration    45 min               │
│   ← Logging interaction   │   Sentiment   🟢 Positive          │
│     with Dr. Sharma...    │                                     │
│     [🔧 log_interaction]  │   Products    Rosuvastatin         │
│                           │              Atorvastatin          │
│   > Change sentiment to   │                                     │
│     positive please       │   AI Summary                       │
│                           │   ┌──────────────────────────────┐ │
│   ← Updated! Sentiment    │   │ Rep visited Dr. Sharma at    │ │
│     is now positive.      │   │ Apollo. Strong interest in   │ │
│     [🔧 edit_interaction] │   │ new Rosuvastatin formulation.│ │
│                           │   └──────────────────────────────┘ │
│   [____________________]  │                                     │
│   [         Send ➤      ] │   ✓  Saved to database            │
│                           │                                     │
└───────────────────────────┴─────────────────────────────────────┘
```

**The form on the right is 100% read-only. All interactions happen through the chat panel.**

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                            │
│  ChatPanel (input)  ←→  Redux Store  →  FormPanel (display) │
└──────────────────────────┬──────────────────────────────────┘
                           │ POST /api/chat
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend                            │
│              routes/chat.py → agent/graph.py                │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              LangGraph StateGraph Agent                      │
│                                                             │
│   HumanMessage → [LLM Node] → tool_call?                   │
│                       ↓ yes                                 │
│               [Tool Node] → executes tool                   │
│                       ↓                                     │
│               [LLM Node] → final response                   │
│                       ↓                                     │
│              AgentState (with updated interaction_draft)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
      Groq API (LLM)            PostgreSQL DB
  gemma2-9b-it (primary)     hcps / interactions /
  llama-3.3-70b (complex)    follow_ups / agent_sessions
```

---

## 🧠 LangGraph Agent Design

The agent is built as a `StateGraph` with three nodes:

### AgentState

```python
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    session_id: str
    hcp_id: Optional[str]
    interaction_draft: InteractionDraft   # This is what populates the form
    last_tool_called: Optional[str]
    interaction_id: Optional[str]
    error: Optional[str]
    final_response: Optional[str]
```

### Graph Flow

```
Entry ──► [LLM Node] ──has tool call?──► YES ──► [Tool Node] ──► [LLM Node]
                        │                                              │
                        NO                                            │
                        ▼                                             ▼
                      [END]                                         [END]
```

The `interaction_draft` field in `AgentState` is the key to the split-screen UX — every tool updates this dict, and the FastAPI response returns it to the frontend, which dispatches it to Redux, which re-renders `FormPanel`.

---

## 🔧 The 5 LangGraph Tools

| # | Tool | Trigger phrase examples | LLM used |
|---|------|------------------------|----------|
| 1 | `log_interaction` | "Met Dr. X today", "Just finished a call with..." | gemma2-9b-it |
| 2 | `edit_interaction` | "Change sentiment to positive", "Add Metformin to products" | gemma2-9b-it |
| 3 | `get_hcp_profile` | "Tell me about Dr. X", "Profile before my visit" | gemma2-9b-it |
| 4 | `schedule_follow_up` | "Follow up in 10 days", "Schedule sample delivery" | llama-3.3-70b-versatile |
| 5 | `summarize_and_analyze_visit` | "Analyze my visits", "How is my engagement with Dr. X?" | llama-3.3-70b-versatile |

### Tool 1 — `log_interaction` (detailed)

Takes raw chat input and:
1. Calls `gemma2-9b-it` to extract structured entities:
   ```json
   {
     "drugs_mentioned": ["Rosuvastatin", "Atorvastatin"],
     "objections": ["pricing concern"],
     "competitors": [],
     "action_items": ["send samples"]
   }
   ```
2. Generates an `ai_summary` (2–3 sentences)
3. Writes to `interactions` table
4. Returns the full `interaction_draft` to update the form

### Tool 2 — `edit_interaction` (detailed)

Accepts a natural language edit instruction:
1. Fetches the current interaction record from DB
2. Sends instruction + current record to LLM: *"Return only the JSON fields that need to change"*
3. Applies the JSON delta via SQL UPDATE
4. Returns the updated `interaction_draft`

---

## 🗃️ Database Schema

```sql
-- Healthcare Professionals
CREATE TABLE hcps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    specialty VARCHAR(100),
    hospital VARCHAR(200),
    city VARCHAR(100),
    tier VARCHAR(10) DEFAULT 'tier2',    -- tier1 | tier2 | tier3
    email VARCHAR(200),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Interaction records
CREATE TABLE interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hcp_id UUID REFERENCES hcps(id) NOT NULL,
    interaction_type VARCHAR(20) DEFAULT 'visit',  -- visit|call|email|conference
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    duration_minutes INTEGER,
    products_discussed JSONB,           -- ["Rosuvastatin", "Atorvastatin"]
    sentiment VARCHAR(10) DEFAULT 'neutral',  -- positive|neutral|negative
    raw_input TEXT,                     -- original rep message
    ai_summary TEXT,                    -- LLM-generated
    entities_json JSONB,               -- {drugs, objections, competitors, actions}
    next_action TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Follow-up tasks
CREATE TABLE follow_ups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interaction_id UUID REFERENCES interactions(id),
    hcp_id UUID REFERENCES hcps(id),
    due_date DATE,
    task TEXT,
    status VARCHAR(20) DEFAULT 'pending',  -- pending|done|cancelled
    created_at TIMESTAMP DEFAULT NOW()
);

-- Agent session memory
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(100) UNIQUE,
    hcp_id UUID,
    messages_json JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Groq API key (free at [console.groq.com](https://console.groq.com))
- Node.js 20+ (if running frontend locally)
- Python 3.11+ (if running backend locally)

### Option A — Docker Compose (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/aunrxg/ai-crm-hcp.git
cd ai-crm-hcp

# 2. Set up environment
cp backend/.env.example backend/.env
# Edit backend/.env and add your GROQ_API_KEY

# 3. Start all services
docker-compose up --build

# 4. Seed the database (in a new terminal)
docker-compose exec backend python seed.py

# 5. Open the app
# Frontend:  http://localhost:5173
# API docs:  http://localhost:8000/docs
```

### Option B — Local Development

```bash
# ── Backend ──────────────────────────────────────
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Add your GROQ_API_KEY to .env

# Start PostgreSQL (or use a cloud DB, update DATABASE_URL in .env)
# Then run migrations:
alembic upgrade head
python seed.py                  # seed HCP data

uvicorn app.main:app --reload --port 8000

# ── Frontend ─────────────────────────────────────
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

---

## 🔑 Environment Variables

```env
# backend/.env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
DATABASE_URL=postgresql://postgres:password@localhost:5432/crm_hcp
GROQ_PRIMARY_MODEL=gemma2-9b-it
GROQ_LARGE_MODEL=llama-3.3-70b-versatile
CORS_ORIGINS=["http://localhost:5173"]
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check |
| `GET` | `/api/hcp` | List all HCPs |
| `GET` | `/api/hcp/search?q=` | Search HCPs by name |
| `GET` | `/api/hcp/{id}` | HCP profile + recent interactions |
| `POST` | `/api/hcp` | Create HCP |
| `POST` | `/api/chat` | **Main agent endpoint** |
| `GET` | `/api/chat/session/{id}` | Fetch session history |
| `GET` | `/api/interactions?hcp_id=` | List interactions |
| `POST` | `/api/interactions` | Create interaction (direct) |
| `PUT` | `/api/interactions/{id}` | Update interaction |

### POST /api/chat

**Request:**
```json
{
  "message": "Just met Dr. Sharma at Apollo for 45 mins. Discussed Rosuvastatin. She was positive.",
  "session_id": "uuid-session-string",
  "hcp_id": "uuid-of-selected-hcp",
  "interaction_draft": { "hcp_id": "...", "hcp_name": "Dr. Priya Sharma" },
  "history": []
}
```

**Response:**
```json
{
  "response": "Logged! Dr. Sharma's interaction is saved. Rosuvastatin noted with positive sentiment.",
  "interaction_draft": {
    "hcp_id": "abc-123",
    "hcp_name": "Dr. Priya Sharma",
    "interaction_type": "visit",
    "date": "2026-04-21",
    "duration_minutes": 45,
    "products_discussed": ["Rosuvastatin"],
    "sentiment": "positive",
    "ai_summary": "Field rep visited Dr. Sharma at Apollo Hospital...",
    "entities_json": {
      "drugs_mentioned": ["Rosuvastatin"],
      "objections": [],
      "competitors": [],
      "action_items": []
    },
    "next_action": null,
    "follow_up_date": null,
    "follow_up_task": null
  },
  "session_id": "uuid-session-string",
  "tool_called": "log_interaction"
}
```

The `interaction_draft` from this response is dispatched directly to Redux, which re-renders the form panel.

---

## 📁 Project Structure

```
ai-crm-hcp/
│
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, startup
│   │   ├── config.py            # Pydantic settings
│   │   ├── database.py          # SQLAlchemy engine, session
│   │   ├── models.py            # ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── routes/
│   │   │   ├── chat.py          # POST /api/chat → agent
│   │   │   ├── hcp.py           # HCP CRUD
│   │   │   └── interactions.py  # Interaction CRUD
│   │   └── agent/
│   │       ├── state.py         # AgentState, InteractionDraft TypedDicts
│   │       ├── tools.py         # All 5 @tool definitions
│   │       └── graph.py         # StateGraph, run_agent()
│   ├── alembic/                 # DB migrations
│   ├── seed.py                  # Seed script (8 pharma HCPs)
│   ├── test_agent.py            # End-to-end tool tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                         # Root, Redux Provider
│   │   ├── main.jsx
│   │   ├── index.css                       # Tailwind + Inter font
│   │   ├── components/
│   │   │   ├── LogInteractionScreen.jsx    # Main split-screen layout
│   │   │   ├── HCPSelector.jsx             # Searchable HCP picker
│   │   │   ├── ChatPanel.jsx               # Left panel — agent chat
│   │   │   ├── MessageBubble.jsx           # Chat message renderer
│   │   │   └── FormPanel.jsx               # Right panel — read-only form
│   │   ├── store/
│   │   │   ├── index.js                    # Redux store
│   │   │   ├── hcpSlice.js
│   │   │   ├── interactionSlice.js         # interaction_draft state
│   │   │   └── chatSlice.js                # messages, sessionId
│   │   └── api/
│   │       └── client.js                   # axios instance
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml
├── DEMO_SCRIPT.md
└── README.md
```

---

## 🧪 Testing the Agent

Run the end-to-end test suite against a running backend:

```bash
cd backend
python test_agent.py
```

Expected output:
```
✅ PASS  Create HCP         → Dr. Priya Sharma (tier1, Mumbai)
✅ PASS  Tool 1: log        → interaction_id set, ai_summary generated
✅ PASS  Tool 2: edit       → sentiment=positive, Clopidogrel added
✅ PASS  Tool 3: profile    → llm_narrative returned
✅ PASS  Tool 4: follow-up  → follow_up_date = 2026-05-01
✅ PASS  Tool 5: analysis   → sentiment_trend, risk_flag returned

All 6 tests passed ✓
```

---

## 🎨 Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend framework | React | 18.3 |
| State management | Redux Toolkit | 2.2 |
| HTTP client | Axios | 1.7 |
| Styling | Tailwind CSS | 3.4 |
| Font | Google Inter | — |
| Build tool | Vite | 5.2 |
| Backend framework | FastAPI | 0.111 |
| ORM | SQLAlchemy | 2.0 |
| Migrations | Alembic | 1.13 |
| AI agent framework | LangGraph | 0.1 |
| LLM integration | LangChain-Groq | 0.1 |
| Primary LLM | Groq gemma2-9b-it | — |
| Secondary LLM | Groq llama-3.3-70b-versatile | — |
| Database | PostgreSQL | 15 |
| Containerization | Docker Compose | — |

---

## 🧩 Key Design Decisions

### Why chat-only form updates?

The assignment specifies the form and chat are side-by-side, and the form must be updated exclusively through the chat agent. This mirrors real field rep workflows — reps dictate or type naturally, and the AI structures the data. It also demonstrates the LangGraph agent's ability to extract structured data from unstructured text and maintain state across turns.

### Why LangGraph over plain LangChain?

LangGraph provides a `StateGraph` that persists the `interaction_draft` across multiple tool calls in a single session. If a rep says *"log my visit"* and then *"now schedule a follow-up"*, LangGraph carries the `interaction_id` from the first tool into the second — no re-prompting needed. Plain LangChain agent would lose this context.

### Why two Groq models?

`gemma2-9b-it` is fast and accurate for structured extraction tasks (entity extraction, JSON generation). `llama-3.3-70b-versatile` is used for tasks requiring richer reasoning — multi-visit trend analysis and intelligent follow-up date suggestion — where the larger context window and reasoning capability matter.

### Why PostgreSQL over MySQL?

PostgreSQL's native `JSONB` type is used for `products_discussed`, `entities_json`, and `messages_json`. JSONB enables efficient querying of nested fields (e.g., `WHERE entities_json->>'sentiment' = 'positive'`) without a schema change when the entity extraction output evolves.

---

## 🗺️ Data Flow (complete)

```
1. Rep selects HCP from dropdown
   → Redux: hcpSlice.selectedHCP = {id, name, specialty, ...}
   → Redux: interactionSlice.draft.hcp_id = id

2. Rep types message in ChatPanel and clicks Send
   → Redux: chatSlice.messages.push({role:'user', content})
   → API: POST /api/chat {message, session_id, hcp_id, interaction_draft, history}

3. FastAPI routes to agent/graph.py → run_agent()

4. LangGraph: LLM Node classifies intent → selects tool

5. LangGraph: Tool Node executes tool
   → e.g. log_interaction → calls Groq for entity extraction
   → writes to PostgreSQL interactions table
   → returns updated interaction_draft dict

6. LangGraph: LLM Node generates human-readable response

7. FastAPI returns ChatResponse {response, interaction_draft, tool_called}

8. Frontend:
   → chatSlice: addMessage({role:'assistant', content, toolCalled})
   → interactionSlice: updateDraft(interaction_draft)  ← KEY STEP

9. FormPanel re-renders all fields from updated Redux draft
   → Rep sees form populate in real time, no interaction required
```

---

## 🔮 Possible Enhancements

- **Streaming responses** — use FastAPI `StreamingResponse` + SSE for token-by-token chat output
- **Voice input** — Web Speech API in ChatPanel so reps can speak their visit notes hands-free
- **Offline support** — Service Worker to queue interactions when rep has no signal in the field
- **Multi-HCP sessions** — let a rep log interactions for multiple HCPs in a single session
- **Analytics dashboard** — a separate screen using Tool 5 to show territory-level sentiment trends
- **LangGraph persistence** — use `SqliteSaver` or `PostgresSaver` checkpoint for true cross-session memory

---

## 👤 Author

Built as part of the AI-First CRM Round 1 Assignment.  
Models used: `gemma2-9b-it` · `llama-3.3-70b-versatile` via Groq.  
AI agent framework: LangGraph.