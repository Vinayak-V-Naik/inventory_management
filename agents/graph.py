'''Multi-agent copilot — LangGraph supervisor routing to 4 specialist agents.

    question → Supervisor (intent classifier)
                 ├─ inventory   agent → stock levels, statuses, EOQ/ROP/safety stock
                 ├─ procurement agent → reorders, suppliers, POs, forecasts
                 ├─ risk        agent → stockout projections, alerts
                 └─ policy      agent → RAG over knowledge_base/ documents

Each specialist is the same Groq LLM with its own system prompt and tool
subset, run through the ReAct loop in agents/chat.py. The graph itself is
LangGraph: supervisor node + conditional edges + one node per agent.
'''

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from agents.chat import SYSTEM_PROMPT, ask
from agents.llm import get_llm
from agents.tools import (
    demand_forecast,
    inventory_snapshot,
    material_details,
    open_purchase_orders,
    reorder_recommendations,
    search_policy_docs,
    stockout_risk_projections,
    supplier_scorecard,
)

# ── Specialist agent definitions ──────────────────────────────
_BASE = SYSTEM_PROMPT + "\n\nYou are acting as the {role}. {focus}"

AGENTS = {
    "inventory": {
        "tools": [inventory_snapshot, material_details, demand_forecast, search_policy_docs],
        "prompt": _BASE.format(
            today="{today}", role="Inventory Agent",
            focus="Focus on current stock, statuses, safety stock, reorder points, "
                  "EOQ and days of stock remaining. Explain WHY a material has its status.",
        ),
    },
    "procurement": {
        "tools": [reorder_recommendations, supplier_scorecard, open_purchase_orders,
                  material_details, demand_forecast, search_policy_docs],
        "prompt": _BASE.format(
            today="{today}", role="Procurement Agent",
            focus="Focus on what to order, how much (EOQ), from which supplier and why. "
                  "Blend supplier scorecard data with procurement policy when recommending.",
        ),
    },
    "risk": {
        "tools": [stockout_risk_projections, inventory_snapshot, material_details,
                  demand_forecast, search_policy_docs],
        "prompt": _BASE.format(
            today="{today}", role="Risk Agent",
            focus="Focus on stockout risk, projected reorder-point breaches, order-by "
                  "dates and demand spikes. Lead with the most urgent risks.",
        ),
    },
    "policy": {
        "tools": [search_policy_docs],
        "prompt": _BASE.format(
            today="{today}", role="Policy Agent",
            focus="Answer ONLY from the retrieved policy passages and cite the source "
                  "document. If the documents do not cover the question, say so.",
        ),
    },
}

ROUTER_PROMPT = '''You are the supervisor of an inventory-management AI team.
Route the user's question to exactly ONE specialist:

- inventory: current stock levels, material status, safety stock, reorder point, EOQ values
- procurement: what/when/how much to order, supplier choice or comparison, purchase orders, demand forecasts
- risk: stockout risk, future projections, what could go wrong, urgency
- policy: company rules, SOPs, procedures, approval limits, rating thresholds, formula explanations

If the question mixes LIVE DATA (a specific material, supplier, stock level or
order) with policy, route to the data specialist (inventory/procurement/risk) —
they can also read the policy documents. Choose policy ONLY when the question is
purely about rules or procedures with no live data involved.

Reply with ONLY the specialist name, nothing else.'''


class CopilotState(TypedDict, total=False):
    question: str
    history: list
    route: str
    answer: str
    tools_used: list


def _supervisor(state):
    '''Classifies intent — falls back to procurement on anything unexpected'''
    reply = get_llm(temperature=0).invoke([
        SystemMessage(ROUTER_PROMPT),
        HumanMessage(state["question"]),
    ])
    route = str(reply.content).strip().lower()
    for name in AGENTS:
        if name in route:
            return {"route": name}
    return {"route": "procurement"}


def _make_agent_node(name):
    spec = AGENTS[name]

    def node(state):
        res = ask(
            state["question"],
            history=state.get("history"),
            tools=spec["tools"],
            system_prompt=spec["prompt"],
        )
        return {"answer": res["answer"], "tools_used": res["tools_used"]}

    return node


def _build_graph():
    g = StateGraph(CopilotState)
    g.add_node("supervisor", _supervisor)
    for name in AGENTS:
        g.add_node(name, _make_agent_node(name))
    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", lambda s: s["route"], {n: n for n in AGENTS})
    for name in AGENTS:
        g.add_edge(name, END)
    return g.compile()


_graph = None


def ask_copilot(question, history=None):
    '''Entry point for the dashboard/CLI.
    Returns {"answer", "agent", "tools_used"}.'''
    global _graph
    if _graph is None:
        _graph = _build_graph()
    out = _graph.invoke({"question": question, "history": list(history or [])})
    return {
        "answer": out.get("answer", ""),
        "agent": out.get("route", "?"),
        "tools_used": out.get("tools_used", []),
    }
