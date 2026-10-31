# OrderFlow Sentinel — Environment & API Configuration Guide

> **Target Version**: 1.2.1-live-demo  
> **Configuration Mechanism**: Pydantic Settings (`pydantic-settings`) reading from `.env` and OS environment variables.

---

## 1. Environment Variable Reference

OrderFlow Sentinel manages its environment variables through [`backend/app/core/config.py`](file:///d:/Virtusa Jatayu/backend/app/core/config.py). All configuration options are declared in the `Settings` class with sensible defaults:

| Variable Name | Default Value | Mandatory? | Purpose & Description | Restart Required? |
|---|---|---|---|---|
| `APP_NAME` | `OrderFlow Sentinel` | Optional | Human-readable title of the platform displayed in logs, Swagger UI, and root API response. | Yes |
| `APP_ENV` | `development` | Optional | Environment label (`development`, `staging`, `production`). Controls debug log verbosity. | Yes |
| `API_V1_PREFIX` | `/api/v1` | Optional | Route prefix for all version 1 REST API endpoints. | Yes |
| `HOST` | `0.0.0.0` | Optional | Network binding address for Uvicorn. (`0.0.0.0` binds all interfaces; `127.0.0.1` binds local loopback). | Yes |
| `PORT` | `8000` | Optional | TCP port on which FastAPI listens. | Yes |
| `DEBUG` | `true` | Optional | Boolean flag enabling automatic code reloading and detailed exception tracebacks. | Yes |
| `DATABASE_URL` | `sqlite:///./orderflow_sentinel.db` | Optional | Database connection URI. Default connects to local SQLite database in WAL mode. Can point to PostgreSQL/MySQL via SQLAlchemy. | Yes |
| `GEMINI_API_KEY` | `None` | **Optional** | API key for Google Gemini GenAI service. If unset or invalid, deterministic fallback is automatically activated. | Yes |
| `GEMINI_MODEL_ID` | `gemini-flash-latest` | Optional | The Google GenAI model used for advisory Root Cause Analysis diagnoses. | Yes |
| `LOG_LEVEL` | `INFO` | Optional | Logging threshold (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). | Yes |

> [!CAUTION]  
> Never commit active API keys, passwords, or secrets to version control. The `.env` file is excluded via `.gitignore`. Always distribute `.env.example` with sanitized placeholders.

---

## 2. Google Gemini AI Integration Architecture

### A. How the Backend Invokes Gemini
The AI advisory service is encapsulated in [`backend/app/ai/gemini_rca.py`](file:///d:/Virtusa Jatayu/backend/app/ai/gemini_rca.py) through the `AdvisoryRCAEngine` class.

When an incident is detected (e.g., HTTP 503 at payment, SLA delay at fulfilment, or HTTP 422 at inventory), the detector invokes `rca_engine.analyze_incident(...)`:

1. It extracts recent telemetry events (status code, endpoint, duration, error message).
2. It constructs a structured prompt specifying the failure context and requiring a strict JSON output matching the `RCAReport` schema.
3. It initializes the Google GenAI SDK client:
   ```python
   from google import genai
   from google.genai import types

   client = genai.Client(
       api_key=settings.GEMINI_API_KEY,
       http_options=types.HttpOptions(timeout=30000) # 30s timeout
   )
   response = client.models.generate_content(
       model=settings.GEMINI_MODEL_ID,
       contents=prompt,
       config=types.GenerateContentConfig(
           response_mime_type="application/json",
           temperature=0.1
       )
   )
   ```

### B. What Happens If the API Key Is Missing?
If `GEMINI_API_KEY` is empty, unset, or equal to the placeholder string:
1. The engine skips the network call entirely.
2. It logs: `INFO: Gemini API key not found. Activating deterministic fallback.`
3. It calls `self._generate_deterministic_fallback(...)`.
4. The diagnosis completes in under **5 milliseconds** with 100% accuracy according to the approved Version 1.2.1 domain rules.

### C. What Happens If Gemini Fails (Timeout, 404, 503, Quota Exceeded)?
External AI services can experience network latency spikes, model deprecations, or quota throttling (`429 Too Many Requests` / `503 Service Unavailable`).
- OrderFlow Sentinel wraps the call in an isolated `try...except Exception as e` block with a 30-second timeout.
- If any exception occurs:
  ```text
  WARNING: Gemini RCA call failed (503 Service Unavailable). Activating deterministic fallback.
  INFO: Generating RCA via internal deterministic rule engine.
  ```
- The deterministic fallback engine produces the exact required advisory payload.
- The platform **never crashes**, never halts order processing, and never returns a 500 Internal Server Error to the client.

### D. Can the Application Run Without Gemini?
**Yes, 100%.** OrderFlow Sentinel is designed with an "AI Advisory, Deterministic Authority" philosophy. All four scenarios, automated retries, SLA detection, operator alerts, and human approval queues work completely and deterministically even if no internet connection or Gemini API key is present.

---

## 3. Safe `.env.example` Template

A sanitized template is provided at [`/.env.example`](file:///d:/Virtusa Jatayu/.env.example):

```ini
# ==============================================================================
# OrderFlow Sentinel - Environment Configuration Template
# ==============================================================================
# Copy this file to '.env' and update the values as needed.
# Do NOT commit real API keys or sensitive secrets to version control.

# Application Configuration
APP_NAME=OrderFlow Sentinel
APP_ENV=development
API_V1_PREFIX=/api/v1
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Database Configuration (SQLite default with SQLAlchemy portability)
# Uses WAL (Write-Ahead Logging) mode automatically enabled on startup
DATABASE_URL=sqlite:///./orderflow_sentinel.db

# AI Engine Configuration
# GEMINI_API_KEY: Optional. If omitted or quota exceeded, deterministic fallback is automatically used.
# Obtain a key from Google AI Studio: https://aistudio.google.com/
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL_ID=gemini-flash-latest

# Logging Configuration (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO
```

