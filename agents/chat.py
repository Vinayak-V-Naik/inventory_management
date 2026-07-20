'''Copilot chat loop — Groq LLM + tool calling over app.py analytics.

ask() runs a simple ReAct-style loop: the model picks tools, we execute
them locally, feed results back, and return the final answer plus the
list of tools it used (shown in the dashboard for transparency).
'''

from datetime import date

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from agents.llm import get_llm
from agents.tools import TOOLS

MAX_TOOL_ROUNDS = 6

SYSTEM_PROMPT = '''You are the InventIP Copilot, an AI assistant for an automotive-parts
inventory and procurement intelligence platform. The factory tracks 15 raw materials,
their suppliers, purchase orders and daily consumption.

Rules:
- Always answer from tool results — never invent stock numbers, dates or suppliers.
- Call the most specific tool for the question; combine tools when needed
  (e.g. supplier choice = supplier_scorecard + material_details).
- Money is Indian Rupees (INR). Round to whole rupees.
- Be concise and actionable: lead with the answer, then the supporting numbers.
- Status meanings: STOCKOUT = zero stock, CRITICAL = at/below safety stock,
  REORDER = at/below reorder point, OVERSTOCK = well above reorder point, NORMAL = healthy.
- Safety stock uses a 1.65 z-score (95% service level). ROP = avg daily demand
  x predicted lead time + safety stock. EOQ is the classic Wilson formula.
- If a question is outside inventory/procurement, say so briefly.

Today's date is {today}.'''


def ask(question, history=None, tools=None, system_prompt=None):
    '''Answers one question with a ReAct tool loop.
    tools / system_prompt default to the full toolset and copilot prompt —
    the specialist agents in agents/graph.py pass their own subsets.
    Returns {"answer": str, "tools_used": [tool names]}.'''
    tools    = tools if tools is not None else TOOLS
    prompt   = (system_prompt or SYSTEM_PROMPT).format(today=date.today().isoformat())
    tool_map = {t.name: t for t in tools}

    llm      = get_llm().bind_tools(tools)
    messages = [SystemMessage(prompt)] + list(history or []) + [HumanMessage(question)]

    tools_used = []
    for _ in range(MAX_TOOL_ROUNDS):
        ai = llm.invoke(messages)
        messages.append(ai)

        if not ai.tool_calls:
            return {"answer": ai.content, "tools_used": tools_used}

        for call in ai.tool_calls:
            fn = tool_map.get(call["name"])
            if fn is None:
                result = f"Unknown tool: {call['name']}"
            else:
                try:
                    result = fn.invoke(call["args"])
                except Exception as e:
                    result = f"Tool {call['name']} failed: {e}"
            tools_used.append(call["name"])
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

    return {
        "answer": "I couldn't finish answering within the tool-call limit — try a more specific question.",
        "tools_used": tools_used,
    }


def to_lc_history(pairs, max_turns=6):
    '''Converts [(role, text), ...] chat history into LangChain messages,
    keeping only the last max_turns exchanges to save tokens.'''
    msgs = []
    for role, text in pairs[-max_turns * 2:]:
        msgs.append(HumanMessage(text) if role == "user" else AIMessage(text))
    return msgs
