"""
Rota de health check.

GET /api/health
"""

from flask import Blueprint, jsonify

import config
from backend.api.detect import detector_name

bp = Blueprint('health', __name__)


@bp.route('/api/health', methods=['GET'])
def health_check():
    """Verifica se o servidor está funcionando."""
    import cv2

    return jsonify({
        'status': 'ok',
        'service': 'Inclusitec Braille Detector',
        'detector': detector_name(),
        'opencv_version': cv2.__version__,
        'data_dir': config.DATA_DIR,
    })
