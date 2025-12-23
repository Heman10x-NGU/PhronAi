# PHRONAI Server

Django-based AI Agent Backend for Voice-to-Action workflows.

## Tech Stack

- Python 3.12
- Django 5.1
- Django Channels (WebSockets)
- Redis (Channel Layer)
- Instructor + Pydantic (Zero-hallucination LLM)
- PostgreSQL

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## WebSocket Endpoint

- `ws://localhost:8000/ws/agent/` - Main agent connection
