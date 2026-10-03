"""
AI Router — Ollama-powered chat and executive intelligence endpoints.

Endpoints:
    POST /ai/chat              — Context-aware business Q&A via the local Gemma model
    GET  /ai/executive-brief   — Structured morning executive brief

Falls back gracefully when Ollama is offline.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.schemas.business import ChatRequest, ChatResponse
from app.services.business_memory import BusinessMemoryService
from app.services.ollama_client import OllamaClient
from app.utils.prompt_builder import PromptBuilder

router = APIRouter(prefix="/ai", tags=["Ollama AI Intelligence"])
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Chat Endpoint
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def business_chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    AI-powered business chat endpoint.

    Pipeline:
      1. Compile business context from live DB
      2. Build optimised prompt via PromptBuilder
      3. Call Gemma (Ollama) → return response
      4. Fallback to rule-based response if Gemma offline
    """
    context = await BusinessMemoryService.compile_context(db)
    prompt = PromptBuilder.build_chat_prompt(request.question, context)

    context_summary = {
        "low_stock_count": len(context.get("low_stock_products", [])),
        "recent_events_count": len(context.get("recent_events", [])),
        "company": context.get("profile", {}).get("name", "N/A"),
    }

    try:
        ai_response, model_used = await OllamaClient.chat(prompt)
        return ChatResponse(
            response=ai_response,
            model_used=model_used,
            context_summary=context_summary,
        )
    except Exception as exc:
        logger.warning("Ollama backend unavailable (%s) — serving fallback response.", exc)

    # Intelligent rule-based fallback
    low_stock = context.get("low_stock_products", [])
    events = context.get("recent_events", [])
    fallback_msg = (
        f"### Operational Status Summary [Offline Mode]\n\n"
        f"Your local AI Core is currently offline. Showing live database coordinates:\n\n"
        f"| Metric | Live Value | Status / Alert |\n"
        f"|---|---|---|\n"
        f"| **Cash Balance** | ${context.get('profile', {}).get('cash_balance', 0):,.2f} | Operating Liquidity |\n"
        f"| **Low Stock Items** | {len(low_stock)} | {f'⚠ Action required on {len(low_stock)} products' if low_stock else 'Healthy'} |\n"
        f"| **Recent Events** | {len(events)} | Audit Log Active |\n\n"
        f"Please connect the Ollama daemon with the configured model (**{settings.OLLAMA_MODEL}**) to reactivate full AI analysis."
    )
    return ChatResponse(
        response=fallback_msg,
        model_used="system-fallback",
        context_summary=context_summary,
    )


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Ollama Status Endpoint
# ---------------------------------------------------------------------------

@router.get("/ollama-status")
async def get_ollama_status():
    """
    Check the connection to Ollama and confirm if the configured models are loaded.
    """
    return await OllamaClient.status()


# ---------------------------------------------------------------------------
# Executive Brief
# ---------------------------------------------------------------------------

@router.get("/executive-brief")
async def executive_brief(db: AsyncSession = Depends(get_db)):
    """
    Generate a structured morning executive brief.

    Returns JSON with: morning_summary, critical_alerts, top_opportunities,
    business_health_summary, top_actions.
    """
    context = await BusinessMemoryService.compile_context(db)
    prompt = PromptBuilder.build_executive_brief_prompt(context)

    try:
        brief = await OllamaClient.chat_json(prompt)
        if "raw" not in brief:
            return brief
    except Exception as exc:
        logger.warning("Executive brief AI unavailable (%s) — serving structured fallback.", exc)

    # Structured fallback computed from real context data
    low_stock = context.get("low_stock_products", [])
    events = context.get("recent_events", [])
    profile = context.get("profile", {})

    return {
        "morning_summary": (
            f"Good morning. {profile.get('name', 'Your business')} is operating with "
            f"a cash balance of ${profile.get('cash_balance', 0):,.2f}. "
            f"{len(events)} business events were recorded in the last cycle."
        ),
        "critical_alerts": (
            [f"{len(low_stock)} products are below reorder threshold and require immediate restocking."]
            if low_stock else ["No critical inventory alerts at this time."]
        ),
        "top_opportunities": [
            "Review top customer CLV data and implement a loyalty programme.",
            "Consolidate supplier base to reduce procurement overhead.",
            "Identify high-margin products for targeted promotion.",
        ],
        "business_health_summary": (
            "Business operations appear stable. Focus on cash flow management "
            "and resolving any overdue accounts receivable."
        ),
        "top_actions": [
            f"Reorder stock for {len(low_stock)} products at or below reorder point.",
            "Follow up on any overdue customer invoices.",
            "Review supplier reliability scores and address underperformers.",
            "Analyse this month's revenue vs target and adjust sales strategy.",
        ],
    }
