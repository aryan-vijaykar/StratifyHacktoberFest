---
name: sme-os-verifier
description: Verification skill to check if the backend, database, and frontend of Stratify (SME OS) are properly configured and operational.
---

# SME OS Verifier Skill

This skill allows agents to test, verify, and audit the status of the Stratify project.

## Checklist for Auditing Stack

1. **Verify Backend Import & compilation**:
   Make sure the FastAPI app is importable without Pydantic syntax or import failures:
   ```bash
   cd backend && ./venv/bin/python -c "import app.main"
   ```

2. **Verify Database Setup**:
   Confirm that `backend/sme_platform.db` exists and has tables:
   ```bash
   sqlite3 backend/sme_platform.db ".tables"
   ```

3. **Check Live Stack Services**:
   Run the verification helper script to confirm port bindings and API return statuses:
   ```bash
   ./.agents/skills/sme_os_verifier/scripts/verify_stack.sh
   ```

4. **Verify Frontend Build**:
   Verify the Vite React app builds cleanly:
   ```bash
   cd frontend && npm run build
   ```
