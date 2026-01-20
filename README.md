# 🎤 PHRONAI: Voice-Powered AI Diagramming

> Transform voice commands into professional diagrams in real-time with zero-hallucination AI.

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🎯 What It Does

Speak naturally, get professional diagrams instantly. PHRONAI is a voice-controlled AI agent that:

- **Listens** to your voice commands
- **Understands** complex architectural descriptions
- **Renders** beautiful system diagrams in real-time
- **Never hallucinates** thanks to Pydantic schema validation

### Example Voice Commands

| You Say                                                                      | PHRONAI Does                        |
| ---------------------------------------------------------------------------- | ----------------------------------- |
| _"Add a database connected to the API server"_                               | Creates database node + arrow       |
| _"Create a microservices architecture with user service, auth, and gateway"_ | Full 3-node system with connections |
| _"Change all nodes to green"_                                                | Updates all node colors             |
| _"Delete the cache and connect database directly to server"_                 | Removes node, rewires edges         |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           PHRONAI FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   🎤 Voice Input          🧠 AI Processing          📊 Diagram      │
│   ─────────────          ─────────────────         ──────────       │
│                                                                     │
│   ┌─────────┐    ┌───────────────┐    ┌──────────────────────┐     │
│   │ Browser │───▶│   Deepgram    │───▶│   Groq LLaMA 3.3     │     │
│   │ (Audio) │    │   Nova-2 STT  │    │   + Instructor       │     │
│   └─────────┘    └───────────────┘    │   + Pydantic         │     │
│        ▲                              └──────────┬───────────┘     │
│        │                                         │                  │
│        │         ┌─────────────────┐             │                  │
│        └─────────│   tldraw +      │◀────────────┘                  │
│                  │   ELK.js Layout │   Validated JSON Actions       │
│                  └─────────────────┘                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Zero-Hallucination Guarantee

Unlike standard LLM integrations, PHRONAI **never produces invalid output**:

1. **Pydantic Schemas** - Every LLM response is validated against strict schemas
2. **Instructor Library** - Automatic retry with error context if validation fails
3. **Self-Correction Loop** - LLM sees its mistakes and fixes them

---

## ⚡ Tech Stack

| Layer              | Technology            | Why                         |
| ------------------ | --------------------- | --------------------------- |
| **Backend**        | Django 5.2 + Channels | Async WebSocket handling    |
| **LLM**            | Groq (LLaMA 3.3 70B)  | Fast inference, free tier   |
| **Validation**     | Instructor + Pydantic | Zero hallucination          |
| **Speech-to-Text** | Deepgram Nova-2       | 95%+ accuracy on tech terms |
| **Frontend**       | React 18 + tldraw     | Infinite canvas rendering   |
| **Layout**         | ELK.js                | Automatic graph layout      |
| **Auth**           | Supabase              | Magic links, OAuth          |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- API Keys: [Deepgram](https://deepgram.com/) + [Groq](https://groq.com/)

### 1. Backend Setup

```bash
cd phronai/server

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run server
python manage.py runserver 8000
```

### 2. Frontend Setup

```bash
cd phronai/client

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Add Supabase keys

# Run development server
npm run dev
```

### 3. Open in Browser

Navigate to `http://localhost:5173`, sign in, and start speaking! 🎤

---

## 📁 Project Structure

```
phronai/
├── server/                     # Django Backend
│   ├── agent/
│   │   ├── consumers.py        # WebSocket handler
│   │   ├── schemas.py          # Pydantic validation (23 colors!)
│   │   ├── reasoning.py        # LLM integration with Instructor
│   │   └── state.py            # Thread-safe session management
│   ├── middleware/
│   │   └── rate_limit.py       # 10 req/min per user
│   ├── integrations/
│   │   └── deepgram.py         # STT client with retry
│   ├── prompts/
│   │   └── sketch_protocol.md  # System prompt
│   └── Dockerfile              # Production build
│
├── client/                     # React Frontend
│   ├── src/
│   │   ├── pages/AgentCanvas.tsx    # Main canvas with voice UI
│   │   ├── lib/graphLayout.ts       # ELK.js integration
│   │   ├── lib/tldrawShapes.ts      # Custom node rendering
│   │   └── lib/DiagramNodeShape.tsx # Semantic node types
│   └── Dockerfile
│
├── docker-compose.yml          # Full stack deployment
├── docker-compose.dev.yml      # Local dev (PostgreSQL + Redis)
└── railway.toml                # Railway deployment config
```

---

## 🔒 Security Features

- **Rate Limiting**: 10 requests/minute per user (sliding window)
- **JWT Auth**: Supabase tokens validated on WebSocket connect
- **Input Validation**: All LLM outputs schema-validated before execution
- **CORS Protection**: Configured for production domains

---

## 📊 Performance

| Metric                 | Value                          |
| ---------------------- | ------------------------------ |
| End-to-end latency     | ~4 seconds                     |
| Transcription accuracy | 95%+                           |
| LLM schema compliance  | 100%                           |
| Concurrent sessions    | Thread-safe with asyncio locks |

---


### Environment Variables

```env
# Required
DEEPGRAM_API_KEY=your_key
GROQ_API_KEY=your_key
DJANGO_SECRET_KEY=generate_a_secure_key
ALLOWED_HOSTS=your-domain.railway.app

# Optional (auto-provided by Railway)
DATABASE_URL=postgres://...
REDIS_URL=redis://...
```

---

## 📝 API Reference

### WebSocket: `ws://host/ws/agent/?token=<jwt>`

| Direction       | Type          | Payload                             |
| --------------- | ------------- | ----------------------------------- |
| Client → Server | Binary        | Audio (WebM/Opus)                   |
| Server → Client | `transcript`  | `{ text: "..." }`                   |
| Server → Client | `actions`     | `{ actions: [...] }`                |
| Client → Server | `canvas_sync` | `{ graph: {...}, snapshot: "..." }` |

### HTTP Endpoints

| Endpoint         | Method | Purpose              |
| ---------------- | ------ | -------------------- |
| `/health/`       | GET    | Health check         |
| `/health/ready/` | GET    | Kubernetes readiness |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## � Author

**Hemant** – Full Stack Developer

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/heman10x/)

📩 **Interested in this project or want to collaborate?** [Contact me on LinkedIn](https://www.linkedin.com/in/heman10x/)

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.
