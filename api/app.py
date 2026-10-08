"""
Inclusitec - Ponto de entrada da aplicação.

Inicia o servidor Flask que expõe:
- A API de detecção de Braille (/api/...)
- O cadastro de usuários (/api/cadastro)
- A conversão PDF -> impressora Braille (/api/braille/pdf, /api/print)
- O frontend web (http://localhost:5000/)

Uso:
    python app.py
"""

import os
import threading
import webbrowser

import config
from backend import create_app

app = create_app()


def _abrir_navegador(url, atraso=1.2):
    """Abre a interface web no navegador padrão (frontend + backend)."""
    def _abrir():
        try:
            webbrowser.open(url, new=2)
        except Exception:  # noqa: BLE001 - navegador indisponível não é erro fatal
            pass

    timer = threading.Timer(atraso, _abrir)
    timer.daemon = True
    timer.start()


if __name__ == '__main__':
    url = f'http://localhost:{config.PORT}/'
    reinicio_reloader = os.environ.get('WERKZEUG_RUN_MAIN') == '1'

    print("=" * 60)
    print("  Inclusitec - Detector de Braille")
    print("=" * 60)
    print(f"  Servidor iniciando em: {url}")
    print(f"  Frontend web:          {url}")
    print(f"  API de deteccao:       POST http://localhost:{config.PORT}/api/detect-braille")
    print(f"  Cadastro:              POST http://localhost:{config.PORT}/api/cadastro")
    print(f"  PDF -> Braille:        POST http://localhost:{config.PORT}/api/braille/pdf")
    print(f"  Impressoras:           GET  http://localhost:{config.PORT}/api/printers")
    print(f"  Impressao:             POST http://localhost:{config.PORT}/api/print")
    print("=" * 60)
    print("  Abrindo a interface web no navegador...")

    # Com debug o reloader sobe duas vezes; abre só na aplicação real.
    if not config.DEBUG or reinicio_reloader:
        _abrir_navegador(url)

    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
