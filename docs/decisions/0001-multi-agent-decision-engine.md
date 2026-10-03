# ADR-001: Multi-Agent Decision Engine Architecture

## Status
Accepted

## Date
2026-07-12

## Context
The Stratify project requires a decision-making layer that evaluates real-time business operations, financial liquidity, inventory levels, customer risk, and supplier performance. To achieve this, the platform needs a modular, testable, and explainable intelligence system. Key requirements include:
- **Decoupling**: Database ORM entities must not leak directly into decision/synthesis outputs.
- **Explainability**: Every recommendation must trace back to the initiating domain specialist, complete with the specific data thresholds and evidence that triggered it.
- **Prioritization**: Recommendations must be dynamically sorted based on domain confidence and enterprise risk weights to present the most critical actions first.
- **Scalability**: New business domains (e.g., tax compliance, payroll) should be addable with minimal friction.

## Decision
We implemented a **Specialist-Orchestrator Multi-Agent Pattern** in the [agent_engine.py](backend/app/services/agent_engine.py) service layer.

### Specialist Agents
Each specialist agent extends `BaseAgent` and implements an async `analyse()` method returning a standardized Python dictionary (`AgentReport`) instead of raw SQLAlchemy model instances.

1. **FinanceAgent**:
   - **Focus**: Cash flow, profitability (GPM), accounts receivable (AR), and accounts payable (AP).
   - **Thresholds**:
     - Gross Profit Margin (GPM) < 25%: Flag urgent review.
     - GPM < 35%: Recommend supplier cost optimization or pricing adjustments.
     - AP > AR: Alert on negative net working capital and suggest deferring non-critical payments.

2. **OperationsAgent**:
   - **Focus**: Stock level health, supply chain efficiency, and replenishment.
   - **Thresholds**:
     - Out-of-Stock SKUs > 0: Critical alerts to expedite reorders.
     - Below Reorder Point SKUs: Alert to trigger purchase orders.
     - Supplier Reliability < 80%: Alert to source backup vendor options.

3. **MarketingAgent**:
   - **Focus**: Customer lifetime value (CLV) growth and churn mitigation.
   - **Thresholds**:
     - CLV > $5,000: VIP customer identification and loyalty incentives.
     - Churn Probability > 40%: Targeted customer retention campaign suggestions.

4. **SupplierAgent**:
   - **Focus**: Vendor relationship management, procurement diversification, and logistics risk.
   - **Thresholds**:
     - High Delay Risk: Flag backup vendor protocols.
     - Total Suppliers < 3: Highlight supplier concentration risks.

5. **CustomerAgent**:
   - **Focus**: Credit risk, payment behavior, and lifetime value optimization.
   - **Thresholds**:
     - High Late Payment Risk: Recommend pre-payment or tighter credit terms.

6. **RiskAgent**:
   - **Focus**: Cross-functional operational, financial, and market risk aggregation.
   - **Thresholds**:
     - Computes overall enterprise risk level (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) based on aggregated active warning signals.

### Orchestration (CEOAgent)
The `CEOAgent` orchestrates the pipeline:
1. **Context Loading**: Compiles transactional state data from `BusinessMemoryService`.
2. **Prediction Pipeline**: Loads forecasts (revenue, cash flow, demand, customer churn, and supplier reliability) from `PredictionEngineService`.
3. **Execution**: Sequentially calls all 6 specialist agents.
4. **Synthesis & Sorting**: Consolidates all specialist recommendations. Recommends sorting by:
   $$\text{Score} = \text{Confidence} \times \text{Risk Weight}$$
   Where risk weights are:
   - `LOW`: 1.0
   - `MEDIUM`: 0.7
   - `HIGH`: 0.5
   - `CRITICAL`: 0.3
   - `UNKNOWN`: 0.5
5. **Payload Emission**: Produces an executive briefing and prioritized recommendations with clear affected department tags and supporting evidence logs.

## Alternatives Considered

### 1. Monolithic LLM Prompt
- **Pros**: Simple code footprint; offloads orchestration logic to the model.
- **Cons**: High token usage, poor determinism, unpredictable logic changes, lack of test coverage for individual business rules, and context-window degradation on large ledgers.
- **Decision**: Rejected in favor of deterministic python code for specialist calculations, augmented with targeted LLM briefings.

### 2. Direct ORM Propagation
- **Pros**: Direct access to relationships and lazy loading attributes.
- **Cons**: Memory leak risks, thread safety issues over async SQL sessions, serialization complexity, and tight coupling of the database schema to frontend views.
- **Decision**: Rejected. Agents must convert ORM entities to plain dictionaries immediately.

## Consequences
- **Testing**: We can unit test each agent's analysis method in isolation by mock-injecting context and predictions payloads.
- **Explainability**: Recommendations show the specific data points that triggered them (e.g. `Gross profit margin: 23.4%`).
- **Performance**: Specialist executions can be trivially wrapped in `asyncio.gather` for parallel database operations as the platform grows.
- **Safety**: Frontend components read plain data transfer objects (DTOs) without risking database transaction errors or session exhaustion.

