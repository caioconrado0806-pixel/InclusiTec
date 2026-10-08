"""
Rotas de cadastro de usuários.

POST /api/cadastro   -> salva um novo cadastro
GET  /api/cadastros  -> lista os cadastros armazenados
"""

from flask import Blueprint, jsonify, request

from backend.services import cadastro_service
from backend.services.cadastro_service import CadastroInvalido

bp = Blueprint('cadastro', __name__)


@bp.route('/api/cadastro', methods=['POST'])
def cadastro():
    """Recebe os dados do formulário e salva no servidor."""
    dados = request.get_json(silent=True)

    if not dados:
        return jsonify({
            'success': False,
            'error': 'Envie os dados como JSON (nome, email, telefone, perfil).'
        }), 400

    try:
        registro = cadastro_service.save_cadastro(dados)
    except CadastroInvalido as e:
        return jsonify({'success': False, 'error': str(e)}), 400

    return jsonify({
        'success': True,
        'message': 'Cadastro realizado com sucesso! Dados salvos no servidor.',
        'cadastro': registro
    }), 201


@bp.route('/api/cadastros', methods=['GET'])
def listar_cadastros():
    """Lista todos os cadastros (para educadores/gestores)."""
    return jsonify({
        'success': True,
        'total': len(cadastro_service.list_cadastros()),
        'cadastros': cadastro_service.list_cadastros()
    })
