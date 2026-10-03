"""
PromptBuilder — Modular, composable LLM prompt construction.

All prompts are built here. No hardcoded prompt strings should exist anywhere else.
Supports: chat, executive brief, agent briefings, CEO synthesis.
"""

from typing import Any, Dict, List


class PromptBuilder:
    """
    Stateless factory for constructing optimised LLM prompt strings.

    Design goals:
      - Prompts are data-driven from context dicts — not hardcoded
      - Each builder method is independently testable
      - Output is plain text (string) consumed by any LLM endpoint
    """

    # ----------------------------------------------------------------
    # System Preamble
    # ----------------------------------------------------------------

    _SYSTEM_PREAMBLE = (
        "You are the Core Intelligence System of the SME Business Operating System (SME-OS).\n"
        "You are advising the business owner of a small-to-medium enterprise.\n"
        "Be concise, data-driven, and actionable. Avoid generic platitudes.\n"
        "Always cite the specific data from the context when making recommendations.\n\n"
    )

    # ----------------------------------------------------------------
    # Chat Prompt
    # ----------------------------------------------------------------

    @classmethod
    def build_chat_prompt(cls, user_query: str, context: Dict[str, Any]) -> str:
        """Build a business-aware chat prompt injecting full operational context."""
        profile = context.get("profile", {})
        recent_events = context.get("recent_events", [])
        low_stock = context.get("low_stock_products", [])
        top_customers = context.get("top_customers", [])
        risky_suppliers = context.get("risky_suppliers", [])
        decision_history = context.get("decision_history", [])

        prompt = cls._SYSTEM_PREAMBLE
        prompt += "=== BUSINESS CONTEXT ===\n"
        prompt += f"Company: {profile.get('name', 'N/A')} | Industry: {profile.get('industry', 'N/A')}\n"
        prompt += f"Cash Balance: ${profile.get('cash_balance', 0):,.2f}\n"
        prompt += f"Annual Revenue Target: ${profile.get('annual_revenue_target', 0):,.2f}\n\n"

        if recent_events:
            prompt += "=== RECENT EVENTS (last 10) ===\n"
            for ev in recent_events[:10]:
                severity = ev.get("severity", "INFO")
                evt = ev.get("event_type", "INFO")
                desc = ev.get("description", "")
                tstamp = ev.get("timestamp", "")[:10]
                metadata = ev.get("metadata_json")

                prompt += f"  [{severity}] {tstamp} — {evt}: {desc}"
                if metadata:
                    simple_meta = {}
                    for k, v in metadata.items():
                        if k == "transactions" and isinstance(v, list):
                            simple_meta["transactions_count"] = len(v)
                        elif k == "products" and isinstance(v, list):
                            simple_meta["products"] = v
                        else:
                            simple_meta[k] = v
                    meta_str = ", ".join([f"{k}: {v}" for k, v in simple_meta.items() if v is not None])
                    if meta_str:
                        prompt += f" ({meta_str})"
                prompt += "\n"
            prompt += "\n"

        if low_stock:
            prompt += "=== CRITICAL INVENTORY ALERTS ===\n"
            for p in low_stock:
                prompt += f"  ⚠ {p.get('name')} (SKU: {p.get('sku')}) — Stock: {p.get('stock')}, Reorder Point: {p.get('reorder')}\n"
            prompt += "\n"

        if top_customers:
            prompt += "=== TOP CUSTOMERS BY LIFETIME VALUE ===\n"
            for c in top_customers:
                prompt += f"  • {c.get('name')} — CLV: ${c.get('clv', 0):,.2f}, Credit Score: {c.get('credit_score')}\n"
            prompt += "\n"

        if risky_suppliers:
            prompt += "=== AT-RISK SUPPLIERS (lowest reliability) ===\n"
            for s in risky_suppliers:
                prompt += f"  • {s.get('name')} — Reliability: {s.get('reliability_score', 0):.0%}, Avg Lead: {s.get('average_lead_days')}d\n"
            prompt += "\n"

        if decision_history:
            prompt += "=== RECENT DECISION OUTCOMES ===\n"
            for d in decision_history:
                prompt += f"  [{d.get('user_action')}] {d.get('timestamp', '')[:10]} — {d.get('business_outcome', 'No outcome recorded')}\n"
            prompt += "\n"

        prompt += f"=== OPERATOR QUESTION ===\n{user_query}\n\n"
        prompt += (
            "Format your response using structured sections starting with '###' headers, clean Markdown tables (Metric | Value | Status/Action) summarizing the relevant data, and a bulleted list of recommended action steps.\n"
            "CRITICAL: Only generate sections, tables, and action steps that directly answer the operator's question. Do NOT include tables, sections, or metrics for unrelated areas of the business context."
        )
        return prompt

    # ----------------------------------------------------------------
    # Executive Brief Prompt
    # ----------------------------------------------------------------

    @classmethod
    def build_executive_brief_prompt(cls, context: Dict[str, Any]) -> str:
        """Build a prompt that produces a structured JSON executive brief."""
        profile = context.get("profile", {})
        events = context.get("recent_events", [])
        low_stock = context.get("low_stock_products", [])

        prompt = cls._SYSTEM_PREAMBLE
        prompt += "Generate a morning executive brief for the CEO based on the following operational data.\n\n"

        prompt += f"Company: {profile.get('name')} | Cash: ${profile.get('cash_balance', 0):,.2f}\n"
        prompt += f"Recent Events: {len(events)} events in memory\n"
        prompt += f"Low Stock Items: {len(low_stock)} products below reorder point\n\n"

        if events:
            prompt += "Latest Events:\n"
            for ev in events[:5]:
                evt = ev.get("event_type", "")
                desc = ev.get("description", "")
                metadata = ev.get("metadata_json")
                prompt += f"  - {evt}: {desc}"
                if metadata:
                    simple_meta = {k: v for k, v in metadata.items() if k not in ("transactions", ("products"))}
                    meta_str = ", ".join([f"{k}: {v}" for k, v in simple_meta.items() if v is not None])
                    if meta_str:
                        prompt += f" ({meta_str})"
                prompt += "\n"

        prompt += "\nRespond ONLY in valid JSON with this exact structure:\n"
        prompt += """{
  "morning_summary": "<2-3 sentence overview of business status>",
  "critical_alerts": ["<alert 1>", "<alert 2>"],
  "top_opportunities": ["<opportunity 1>", "<opportunity 2>"],
  "business_health_summary": "<1-2 sentence health assessment>",
  "top_actions": ["<action 1>", "<action 2>", "<action 3>"]
}"""
        return prompt

    # ----------------------------------------------------------------
    # Agent-Specific Prompts
    # ----------------------------------------------------------------

    @classmethod
    def build_agent_prompt(
        cls,
        agent_name: str,
        agent_role: str,
        agent_focus: str,
        context: Dict[str, Any],
        predictions: Dict[str, Any] = None,
    ) -> str:
        """Build a specialist agent briefing prompt."""
        profile = context.get("profile", {})
        predictions = predictions or {}

        prompt = (
            f"You are the {agent_name} of SME-OS — responsible for {agent_role}.\n"
            f"Your focus area: {agent_focus}\n\n"
        )
        prompt += f"Company: {profile.get('name')} | Industry: {profile.get('industry')}\n"
        prompt += f"Cash Balance: ${profile.get('cash_balance', 0):,.2f}\n\n"

        if predictions:
            prompt += "=== CURRENT PREDICTIONS ===\n"
            for key, val in predictions.items():
                if isinstance(val, dict):
                    prompt += f"  {key}: {val.get('prediction', 'N/A')}\n"
            prompt += "\n"

        events = context.get("recent_events", [])
        if events:
            prompt += "=== RELEVANT EVENTS ===\n"
            for ev in events[:5]:
                desc = ev.get("description", "")
                metadata = ev.get("metadata_json")
                prompt += f"  - {desc}"
                if metadata:
                    simple_meta = {k: v for k, v in metadata.items() if k not in ("transactions", ("products"))}
                    meta_str = ", ".join([f"{k}: {v}" for k, v in simple_meta.items() if v is not None])
                    if meta_str:
                        prompt += f" ({meta_str})"
                prompt += "\n"
            prompt += "\n"

        prompt += (
            "Provide your analysis as a structured response with:\n"
            "1. ANALYSIS: <your assessment of the current situation>\n"
            "2. RECOMMENDATIONS: <3-5 specific, actionable recommendations>\n"
            "3. RISKS: <key risks in your domain>\n"
            "4. CONFIDENCE: <HIGH | MEDIUM | LOW>\n"
        )
        return prompt

    @classmethod
    def build_procurement_agent_prompt(cls, context: Dict[str, Any]) -> str:
        """Build a specialist prompt for ProcurementAgent to analyze raw materials prices."""
        material_history = context.get("material_price_history", [])
        
        prompt = cls._SYSTEM_PREAMBLE
        prompt += "You are the ProcurementAgent of SME-OS — responsible for Raw Materials and Procurement Timing.\n"
        prompt += "Your focus area: raw material price trend analysis, cost forecasting, and spot price monitoring.\n\n"
        
        prompt += "=== RAW MATERIAL PRICE HISTORY ===\n"
        if not material_history:
            prompt += "  No raw material price history available on record.\n"
        else:
            for item in material_history:
                prompt += f"  Material: {item['name']} (ID: {item['material_id']}, Unit: {item['unit']})\n"
                prompt += f"    Current Spot Price: ${item['current_price']:.2f}\n"
                prompt += "    Price History (Newest first):\n"
                history_list = item.get("history", [])
                if not history_list:
                    prompt += "      No historical price entries recorded.\n"
                for h in history_list:
                    prompt += f"      - ${h['recorded_price']:.2f} at {h['recorded_at']} (Source: {h['source']})\n"
        prompt += "\n"
        
        prompt += (
            "Analyze the trailing 90-day price trend against the current spot price.\n"
            "For each raw material, provide exactly one recommended action: STOCKPILE, DELAY, or HOLD.\n"
            "Include a one-sentence justification per material tied directly to the actual price numbers in context. Do not invent any figures.\n\n"
            "You MUST respond ONLY in valid, single-line-safe JSON with the exact keys:\n"
            "{\n"
            '  "analysis": "<brief overall analysis of material cost trends>",\n'
            '  "recommendations": [\n'
            '    "<material name>: [STOCKPILE|DELAY|HOLD] - <justification containing actual price numbers>"\n'
            '  ],\n'
            '  "risk_level": "<LOW|MEDIUM|HIGH|CRITICAL>",\n'
            '  "confidence": <float between 0.0 and 1.0>,\n'
            '  "supporting_evidence": [\n'
            '    "<evidence point 1 with price figures>"\n'
            '  ]\n'
            "}\n"
        )
        return prompt

    # ----------------------------------------------------------------
    # CEO Synthesis Prompt
    # ----------------------------------------------------------------

    @classmethod
    def build_ceo_prompt(
        cls,
        agent_reports: List[Dict[str, Any]],
        context: Dict[str, Any],
        predictions: Dict[str, Any] = None,
    ) -> str:
        """Build the CEO Agent prompt that synthesises all specialist agent reports."""
        profile = context.get("profile", {})
        predictions = predictions or {}

        prompt = (
            "You are the CEO Agent of SME-OS — the executive decision-making intelligence.\n"
            "You have received reports from all specialist agents. Synthesise them into a strategic executive plan.\n\n"
        )
        prompt += f"Company: {profile.get('name')} | Cash: ${profile.get('cash_balance', 0):,.2f}\n\n"

        if predictions:
            prompt += "=== FORECAST SUMMARY ===\n"
            for key, val in predictions.items():
                if isinstance(val, dict):
                    prompt += f"  {key}: {val.get('prediction', 'N/A')} (Confidence: {val.get('confidence_score', 0):.0%})\n"
            prompt += "\n"

        prompt += "=== AGENT REPORTS ===\n"
        for report in agent_reports:
            prompt += f"\n[{report.get('agent_name', 'Unknown Agent')}]\n"
            for rec in report.get("recommendations", []):
                prompt += f"  • {rec}\n"

        prompt += (
            "\nAs CEO Agent, provide:\n"
            "1. EXECUTIVE SUMMARY: Holistic 3-4 sentence business state\n"
            "2. TOP 5 PRIORITIES: Most critical items across all agent reports\n"
            "3. STRATEGIC DECISIONS: 3 key decisions the owner must make this week\n"
            "4. BUSINESS RISKS: Top 3 risks with severity\n"
            "5. GROWTH OPPORTUNITIES: 2-3 opportunities to pursue now\n"
        )
        return prompt

    @classmethod
    def build_strategy_brief_prompt(
        cls,
        agent_reports: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> str:
        """Build the CEO Agent prompt for the 4-point strategy brief with explainability citations."""
        profile = context.get("profile", {})
        
        prompt = cls._SYSTEM_PREAMBLE
        prompt += "You are the CEO Agent of SME-OS. Your task is to produce a 4-point Executive Strategy Brief.\n"
        prompt += f"Company: {profile.get('name')} | Cash: ${profile.get('cash_balance', 0):,.2f}\n\n"
        
        prompt += "=== ACTIVE SPECIALIST REPORTS ===\n"
        for report in agent_reports:
            name = report.get('agent_name', 'Unknown')
            prompt += f"\n[{name} - Risk: {report.get('risk_level', 'MEDIUM')}]\n"
            prompt += f"  Analysis: {report.get('analysis')}\n"
            prompt += "  Recommendations:\n"
            for rec in report.get("recommendations", []):
                prompt += f"    • {rec}\n"
            prompt += "  Supporting Evidence:\n"
            for ev in report.get("supporting_evidence", []):
                prompt += f"    • {ev}\n"
        prompt += "\n"
        
        prompt += (
            "Based ONLY on the specialist reports, construct a 4-point strategic brief with these exact elements:\n"
            "1. Capital Allocation: Where to invest cash surplus or how to manage liquidity pressure.\n"
            "2. Next Product Focus: Which product lines or raw materials to prioritize.\n"
            "3. Cost Reductions: Where to trim operational waste or renegotiate supply terms.\n"
            "4. Promotional Offers: How to engage customer segments or drive conversions.\n\n"
            "For each of the 4 points, you MUST cite which specialist agent's report supported this decision (e.g. '[ProcurementAgent]', '[SupplierAgent]', '[CustomerAgent]', or '[OperationsAgent]'). Do not make up any facts outside the reports.\n\n"
            "You MUST respond ONLY in valid, single-line-safe JSON matching this exact structure:\n"
            "{\n"
            '  "capital_allocation": "<Capital allocation strategy decision>",\n'
            '  "next_product_focus": "<Product focus strategy decision>",\n'
            '  "cost_reductions": "<Cost reductions strategy decision>",\n'
            '  "promotional_offers": "<Promotional offers strategy>",\n'
            '  "supporting_evidence": {\n'
            '    "capital_allocation": "<citation details mentioning agent and evidence>",\n'
            '    "next_product_focus": "<citation details>",\n'
            '    "cost_reductions": "<citation details>",\n'
            '    "promotional_offers": "<citation details>"\n'
            '  }\n'
            "}\n"
        )
        return prompt
