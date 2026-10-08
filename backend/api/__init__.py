"""Pacote da API: expõe os blueprints das rotas."""

from backend.api.detect import bp as detect_bp
from backend.api.cadastro import bp as cadastro_bp
from backend.api.health import bp as health_bp
from backend.api.braille_pdf import bp as braille_pdf_bp

# Blueprints registrados no app em backend/__init__.py.
API_BLUEPRINTS = (detect_bp, cadastro_bp, health_bp, braille_pdf_bp)

__all__ = ['API_BLUEPRINTS']
