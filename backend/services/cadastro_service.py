"""
Serviço de cadastro de usuários.

Persiste os cadastros em dois formatos no diretório 'data/':
- cadastros.json: registros completos (uma linha por cadastro)
- cadastros.csv:  exportação aberta diretamente no Excel
"""

import csv
import json
import os
import re
from datetime import datetime

import config

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class CadastroInvalido(Exception):
    """Exceção levantada quando os dados do cadastro são inválidos."""


def _ensure_data_dir():
    os.makedirs(config.DATA_DIR, exist_ok=True)


def _load_all():
    """Lê todos os cadastros do arquivo JSON."""
    if not os.path.exists(config.CADASTROS_JSON):
        return []
    try:
        with open(config.CADASTROS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _persist(cadastros):
    """Grava o JSON e reescreve o CSV (compatível com Excel)."""
    _ensure_data_dir()

    with open(config.CADASTROS_JSON, 'w', encoding='utf-8') as f:
        json.dump(cadastros, f, ensure_ascii=False, indent=2)

    with open(config.CADASTROS_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id'] + list(config.CADASTRO_FIELDS) + ['dataCadastro'])
        writer.writeheader()
        writer.writerows(cadastros)


def validate_cadastro(dados):
    """
    Valida os dados do cadastro.

    Returns:
        dict normalizado com nome, email, telefone, perfil.

    Raises:
        CadastroInvalido: se algum campo obrigatório estiver faltando
        ou for inválido.
    """
    if not isinstance(dados, dict):
        raise CadastroInvalido('Dados do cadastro inválidos.')

    campos = {}
    for campo in config.CADASTRO_FIELDS:
        valor = str(dados.get(campo, '') or '').strip()
        if not valor:
            raise CadastroInvalido(f'Campo obrigatório ausente: {campo}')
        campos[campo] = valor

    if not _EMAIL_RE.match(campos['email']):
        raise CadastroInvalido('E-mail inválido.')

    return campos


def save_cadastro(dados):
    """
    Salva um novo cadastro.

    Returns:
        O registro completo (com id e data/hora do cadastro).
    """
    campos = validate_cadastro(dados)

    cadastros = _load_all()
    registro = {
        'id': (cadastros[-1]['id'] + 1) if cadastros else 1,
        **campos,
        'dataCadastro': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
    }

    cadastros.append(registro)
    _persist(cadastros)
    return registro


def list_cadastros():
    """Retorna todos os cadastros armazenados."""
    return _load_all()
