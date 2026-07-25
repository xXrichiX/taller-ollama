"""IESPRO-Taller — API web (React frontend + FastAPI backend)."""

import sys


def main():
  print(
    "IESPRO-Taller ahora usa la interfaz web.\n"
    "  API:     uvicorn api.main:app --host 0.0.0.0 --port 8000\n"
    "  Web dev: cd web && npm install && npm run dev\n"
    "  Docker:  docker compose up --build\n"
  )
  if "--agent" in sys.argv:
    from agent_cli import run
    run()
  else:
    sys.exit(0)


if __name__ == "__main__":
  main()
