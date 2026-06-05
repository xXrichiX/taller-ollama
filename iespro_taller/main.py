"""IESPRO-Taller

Modo agente (Actividad 3 — Function Calling en terminal):
  python agent_cli.py

Modo interfaz gráfica (opcional):
  python main.py --ui
"""

import sys


def main():
    if "--ui" in sys.argv:
        from ui.main_app import MainApp
        app = MainApp()
        app.mainloop()
    else:
        from agent_cli import run
        run()


if __name__ == "__main__":
    main()
