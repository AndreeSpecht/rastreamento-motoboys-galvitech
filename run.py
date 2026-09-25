"""Ponto de entrada: python run.py [--debug] [--no-browser]"""

import argparse
import threading
import webbrowser

from radar_tracker import create_app
from radar_tracker.config import Config


def main():
    parser = argparse.ArgumentParser(description="Servidor do módulo de rastreamento de motoboys.")
    parser.add_argument("--debug", action="store_true", help="modo de desenvolvimento do Flask (recarga automática)")
    parser.add_argument("--no-browser", action="store_true", help="não abrir o navegador ao iniciar")
    parser.add_argument("--port", type=int, default=Config.PORT)
    args = parser.parse_args()

    app = create_app()
    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    print(f"Painel disponível em {url}  (Ctrl+C para encerrar)")

    if args.debug:
        app.run(host=Config.HOST, port=args.port, debug=True, use_reloader=False)
    else:
        from waitress import serve

        serve(app, host=Config.HOST, port=args.port, threads=8)


if __name__ == "__main__":
    main()
