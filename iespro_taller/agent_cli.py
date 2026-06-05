"""Agente IESPRO-Taller — terminal."""

import json
import sys

from config import DEFAULT_SUCURSAL_ID
from db.init_db import ensure_data_dir, init_database
from services.agent_service import AgentService


def run():
    ensure_data_dir()
    ok, msg = init_database()
    if not ok:
        print(f"Error: {msg}")
        sys.exit(1)

    agent = AgentService(DEFAULT_SUCURSAL_ID)

    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not question:
            continue
        if question.lower() in ("salir", "exit", "quit"):
            break

        result = agent.ask(question)

        for tc in result.get("tool_calls", []):
            print(f"[tool] {tc['name']}({json.dumps(tc.get('arguments', {}), ensure_ascii=False)})")
            print(f"[result] {json.dumps(tc.get('result'), ensure_ascii=False, default=str)}")

        print(result["answer"])
        print()


if __name__ == "__main__":
    run()
