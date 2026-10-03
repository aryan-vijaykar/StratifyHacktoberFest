# Gemma SME OS: Deployment & Operations Guide

This guide describes the operational prerequisites, local development setup steps, environment configuration matrices, Docker Compose topologies, and stack verification procedures for the Gemma SME OS.

---

## 1. System Prerequisites

Before initiating the stack, ensure that the following runtime environments and packages are installed:

*   **Operating System**: Linux, macOS, or Windows (WSL2 recommended for Docker operations).
*   **Python**: Python 3.10 to 3.12 (standard virtual environment support).
*   **Node.js**: Node.js v18 or newer with `npm`.
*   **Database**: SQLite3 command-line client (for direct database inspection).
*   **OCR System**: Tesseract OCR engine (required for document processing services):
    *   *macOS*: `brew install tesseract`
    *   *Linux*: `apt-get install -y tesseract-ocr libtesseract-dev`
    *   *Windows*: Download binary installer and add to system PATH.
*   **Local AI Engine**: Ollama daemon installed and running locally, with the target model downloaded:
    ```bash
    ollama run gemma4:latest
    ```

---

## 2. Local Environment Setup

### A. Backend ASGI Server Setup
1.  Navigate into the backend package:
    ```bash
    cd backend
    ```
2.  Initialize the isolated virtual environment:
    ```bash
    python -m venv venv
    ```
3.  Activate the environment:
    *   *Unix (macOS / Linux)*:
        ```bash
        source venv/bin/activate
        ```
    *   *Windows (Git Bash / WSL)*:
        ```bash
        source venv/bin/activate
        ```
    *   *Windows (PowerShell)*:
        ```powershell
        .\venv\Scripts\Activate.ps1
        ```
4.  Upgrade base packaging tools and install python dependencies:
    ```bash
    python -m pip install --upgrade pip
    ```
    ```bash
    python -m pip install -r requirements.txt
    ```
5.  Launch the Uvicorn hot-reloader daemon on the designated development port:
    ```bash
    python -m uvicorn app.main:app --reload --port 8000
    ```

### B. Frontend SPA Client Setup
1.  Navigate to the React application root:
    ```bash
    cd frontend
    ```
2.  Install the package node modules:
    ```bash
    npm install
    ```
3.  Start the Vite local development client:
    ```bash
    npm run dev
    ```
    The client console is exposed at `http://localhost:5173`.

---

## 3. Configuration & Environment Settings

The backend loads its configuration dynamically at boot time using a Pydantic Settings class. All configurations are read from `backend/.env`.

### Configuration Parameter Matrix

| Key Parameter | DataType | Default Value | Description |
| :--- | :---: | :--- | :--- |
| `DATABASE_URL` | String | `sqlite+aiosqlite:///sme_platform.db` | Async SQLAlchemy SQLite database path |
| `OLLAMA_BASE_URL` | String | `http://127.0.0.1:11434` | Root address of the local Ollama backend |
| `OLLAMA_MODEL` | String | `gemma4:latest` | Primary Gemma model tag for business briefings |
| `OLLAMA_FALLBACK_MODEL` | String | `gemma4:e4b` | Secondary model used if primary fails |
| `OLLAMA_TIMEOUT_SECONDS`| Float | `180.0` | Maximum socket timeout duration for LLM inference |
| `OLLAMA_TEMPERATURE` | Float | `0.2` | Creativity level (low value for deterministic briefs) |
| `ENVIRONMENT` | String | `development` | Deployment mode flag (`development` or `production`) |
| `LOG_LEVEL` | String | `INFO` | Level for backend logs (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `UPLOAD_DIR` | String | `./uploads` | Directory where document files are saved |
| `SECRET_KEY` | String | `super-secret-key-change-in-production` | Secret key used for sessions and hashes |

---

## 4. Docker Compose & Containerized Deployment

For fully containerized local stacks (eliminating manual Python or Tesseract dependencies), use the root Docker configurations:

### A. Container Structure
The `docker-compose.yml` orchestrates two primary services:
1.  **`ollama`**: Runs the local AI daemon inside a volume-mounted container (`ollama_data`). Maps internal port `11434` to localhost and tests status using:
    ```bash
    ollama list
    ```
2.  **`backend`**: Builds from the local `Dockerfile` (installing python, system tesseract OCR, and running dependencies). Exposes the FastAPI server on port `8000`.

### B. Deployment Commands
1.  Build and boot the entire stack in detached mode:
    ```bash
    docker compose up -d --build
    ```
2.  Verify the status of the containers:
    ```bash
    docker compose ps
    ```
3.  Inspect active container logs:
    ```bash
    docker compose logs -f backend
    ```

---

## 5. Verification & Health Auditing

The system provides an automated testing checklist to confirm all services are operating correctly.

### A. Automated Verification Script
Execute the system audit script from the root workspace:
```bash
./.agents/skills/sme_os_verifier/scripts/verify_stack.sh
```
This script audits:
1.  **SQLite Database**: Confirms the presence of `backend/sme_platform.db`.
2.  **FastAPI Backend Server**: Issues an HTTP request to `http://localhost:8000/health` and expects a `200 OK` return.
3.  **Vite Frontend Dev Client**: Pings `http://localhost:5173/` to confirm web server port availability.

### B. Manual REST Verification
Validate the status of specific modules by executing these curls:
*   **Base API Connection**:
    ```bash
    curl -i http://localhost:8000/
    ```
*   **Health Status Check**:
    ```bash
    curl -i http://localhost:8000/health
    ```
*   **Ollama Connection State**:
    ```bash
    curl -i http://localhost:8000/api/v1/ai/ollama-status
    ```
