# Backend Setup

The backend is intended to stay isolated from the host Python installation. Use the virtual environment in this folder for all backend work.

## 1. Create the virtual environment

From the `backend` directory:

```bash
python -m venv venv
```

If `venv` already exists, keep using it rather than creating a second environment elsewhere.

## 2. Activate the virtual environment

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
.\venv\Scripts\activate.bat
```

Git Bash or another POSIX shell on Windows:

```bash
source venv/Scripts/activate
```

## 3. Install dependencies

Always install packages inside the activated venv:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Run the API

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

To run the backend together with local Ollama in Docker, use:

```bash
docker compose up --build
```

That compose file starts Ollama on port `11434` and points the backend at `http://ollama:11434` inside the Docker network.

## 5. Environment configuration

Create or update `backend/.env` with the values you want to override. The application supports:

- `DATABASE_URL`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TIMEOUT_SECONDS`
- `OLLAMA_TEMPERATURE`
- `GEMMA_API_URL` and `GEMMA_MODEL` are kept as compatibility aliases
- `UPLOAD_DIR`
- `ENVIRONMENT`
- `LOG_LEVEL`
- `SECRET_KEY`

The backend talks to Ollama at `http://127.0.0.1:11434/api/chat` by default and uses `gemma4:latest`. Run `ollama list` to confirm the exact model string that is installed locally.

You can check the live connection with `GET /api/v1/ai/ollama-status` once the backend is running.

The defaults are safe for local development, but `SECRET_KEY` should be changed before any non-local deployment.