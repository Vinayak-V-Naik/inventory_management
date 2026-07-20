'''Quick command-line test for the copilot, no Streamlit needed:

    uv run python -m agents.cli "Which materials need reordering?"
'''

import sys

from agents.graph import ask_copilot


def main():
    question = " ".join(sys.argv[1:]) or "Which materials need reordering right now?"
    print(f"Q: {question}\n")
    result = ask_copilot(question)
    print(f"[agent: {result['agent']} | tools: {', '.join(result['tools_used']) or 'none'}]\n")
    print(result["answer"])


if __name__ == "__main__":
    main()
