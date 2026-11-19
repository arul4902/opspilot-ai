# OpsPilot AI – Production Deployment Guide

This guide details the complete deployment architecture for **OpsPilot AI** across **Vercel** (Frontend) and **Render** (Backend & Managed PostgreSQL), including Server-Sent Events (SSE) proxy configuration and environment setups.

---

## 1. Architecture Overview

```
                      ┌───────────────────────────────────────────┐
                      │            Vercel Edge Network            │
                      │  OpsPilot Angular 22 SPA                  │
                      │  https://opspilot-ai.vercel.app           │
                      └─────────────────────┬─────────────────────┘
                                            │
                                            │ REST APIs & SSE (/events/stream, /agent/stream)
                                            ▼
                      ┌───────────────────────────────────────────┐
                      │            Render Cloud Service           │
                      │  FastAPI 0.115 ASGI + Uvicorn             │
                      │  https://opspilot-ai-backend.onrender.com │
                      └───────┬───────────────────────────┬───────┘
                              │                           │
                              ▼                           ▼
            ┌───────────────────────────┐   ┌───────────────────────────┐
            │   Render Managed Postgres │   │  ChromaDB Policy Vector   │
            │   Relational Operational  │   │  Store (59 Enterprise     │
            │   Entities & Audit Logs   │   │  Policy Embeddings)       │
            └───────────────────────────┘   └───────────────────────────┘
```

---

## 2. Frontend Deployment (Vercel)

### 2.1 Repository Setup & Vercel Import
1. Push your repository to **GitHub**.
2. Go to [vercel.com](https://vercel.com) and click **"Add New Project"**.
3. Import your `OpsPilot-AI` repository.

### 2.2 Vercel Project Settings
* **Framework Preset**: `Other` (or Angular)
* **Root Directory**: `frontend`
* **Build Command**: `npm run build`
* **Output Directory**: `dist/frontend/browser`
* **Node.js Version**: `20.x` or `22.x`

### 2.3 Environment Variables on Vercel
In the Vercel dashboard under **Settings > Environment Variables**, add:
| Key | Value | Purpose |
| :--- | :--- | :--- |
| `NG_APP_API_URL` | `https://opspilot-ai-backend.onrender.com/api/v1` | Production Backend API URL |

### 2.4 SPA Route Fallback & Headers (`vercel.json`)
The pre-configured [frontend/vercel.json](file:///d:/OpsPilot%20AI/frontend/vercel.json) automatically enforces client-side routing rewrites and security headers:
```json
{
  "version": 2,
  "buildCommand": "npm run build",
  "outputDirectory": "dist/frontend/browser",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" },
        { "key": "X-XSS-Protection", "value": "1; mode=block" }
      ]
    }
  ]
}
```

---

## 3. Backend Deployment (Render)

### 3.1 One-Click Blueprint Deployment (`render.yaml`)
OpsPilot includes a pre-configured [render.yaml](file:///d:/OpsPilot%20AI/render.yaml) blueprint:
1. In Render, select **"Blueprints"** > **"New Blueprint Instance"**.
2. Connect your GitHub repository.
3. Render automatically provisions:
   * **Web Service**: `opspilot-ai-backend` (Python 3.12, Uvicorn ASGI server).
   * **Database**: `opspilot-postgres` (Managed PostgreSQL instance).

### 3.2 Manual Web Service Configuration (Alternative)
* **Environment**: `Python 3`
* **Build Command**:
  ```bash
  pip install -r requirements.txt && python -m scripts.ingest_policies && python -m scripts.seed_database
  ```
* **Start Command**:
  ```bash
  uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
  ```
* **Health Check Path**: `/health`

### 3.3 Backend Environment Variables
| Variable | Value / Format | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/opspilot` | Managed PostgreSQL connection string |
| `SECRET_KEY` | *Generated 64-char hex string* | JWT signing secret |
| `ENVIRONMENT` | `production` | Production mode switch |
| `BACKEND_CORS_ORIGINS` | `["https://opspilot-ai.vercel.app","http://localhost:4200"]` | Authorized frontend origins |
| `LLM_PROVIDER` | `gemini` or `openai` or `mock` | Primary LLM engine |
| `GEMINI_API_KEY` | `AIzaSy...` | Optional: Google Gemini API key |
| `OPENAI_API_KEY` | `sk-proj-...` | Optional: OpenAI API key |

---

## 4. Real-Time Server-Sent Events (SSE) in Production

### 4.1 Proxy Buffering Prevention
Reverse proxies (like Nginx, Cloudflare, and Render Edge) buffer HTTP streaming responses by default unless explicit headers are returned.
OpsPilot AI includes strict anti-buffering response headers on all SSE endpoints (`/api/v1/events/stream` and `/api/v1/agent/stream`):
```python
headers = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
    "Access-Control-Allow-Origin": "*"
}
```

### 4.2 Keepalive Heartbeat
To prevent cloud load balancers and cellular connections from timing out idle connections, the backend broadcaster issues a keepalive ping every 15 seconds:
```
: keepalive 2026-11-19T00:18:12.000Z
```

### 4.3 Client-Side Reconnection & Polling Fallback
* Angular's `EventSource` automatically handles transient disconnections and retries connection.
* The frontend [overview.component.ts](file:///d:/OpsPilot%20AI/frontend/src/app/features/overview/overview.component.ts) maintains a 30-second interval polling fallback to guarantee real-time telemetry if a corporate firewall blocks long-lived streaming connections.

---

## 5. Local Docker Deployment

To run the complete platform locally using Docker:
```bash
# 1. Build and run backend container
docker build -t opspilot-ai-backend .
docker run -p 8000:8000 -e ENVIRONMENT=production opspilot-ai-backend

# 2. Probe health check
curl http://localhost:8000/health
```

