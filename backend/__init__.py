"""
Backend do Inclusitec (Flask).

Fornece:
- API REST para detecção de Braille (/api/...)
- Endpoint de cadastro de usuários
- Servimento do frontend web (templates + static)

Uso:
    from backend import create_app
    app = create_app()
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

import config
from backend.api import API_BLUEPRINTS


def create_app():
    """Cria e configura a aplicação Flask."""
    app = Flask(
        __name__,
        template_folder=config.TEMPLATE_DIR,
        static_folder=config.STATIC_DIR,
        static_url_path='/static',
    )
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_UPLOAD_BYTES
    CORS(app)

    # Rotas da API.
    for bp in API_BLUEPRINTS:
        app.register_blueprint(bp)

    # Frontend: a raiz serve a interface web.
    @app.route('/')
    def index():
        return render_template('index.html')

    # Páginas desconhecidas caem no frontend (evita "só JSON" na raiz).
    @app.errorhandler(404)
    def nao_encontrado(_erro):
        if request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Rota não encontrada.'}), 404
        return render_template('index.html'), 200

    return app
