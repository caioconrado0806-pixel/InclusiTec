"""
Rota de detecção de Braille.

POST /api/detect-braille
    Recebe uma imagem (multipart 'image' ou JSON 'image_base64')
    e retorna o texto traduzido para português brasileiro.
"""

import base64

import cv2
import numpy as np
from flask import Blueprint, jsonify, request

from backend.braille import (
    BrailleDetector,
    BrailleToPortuguese,
    YOLOBrailleDetector,
)

bp = Blueprint('detect', __name__)

yolo_detector = YOLOBrailleDetector()
detector = BrailleDetector()
converter = BrailleToPortuguese()

USING_YOLO = yolo_detector.is_available()


def _decode_image(data):
    """
    Decodifica a imagem vinda da requisição.

    Aceita:
    - arquivo multipart com campo 'image'
    - JSON com campo 'image_base64' (com ou sem prefixo data:)

    Returns:
        Imagem OpenCV (BGR) ou None.
    """
    if 'image' in request.files:
        image_bytes = request.files['image'].read()
    elif request.is_json:
        payload = request.get_json(silent=True) or {}
        base64_str = payload.get('image_base64') or ''
        if not base64_str:
            return None
        if ',' in base64_str:  # remove prefixo data:image/...;base64,
            base64_str = base64_str.split(',', 1)[1]
        try:
            image_bytes = base64.b64decode(base64_str)
        except ValueError:  # binascii.Error é subclass de ValueError
            return None
    else:
        return None

    nparr = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


@bp.route('/api/detect-braille', methods=['POST'])
def detect_braille():
    """Detecta Braille em uma imagem e retorna o texto em PT-BR."""
    try:
        image = _decode_image(request)

        if image is None:
            return jsonify({
                'success': False,
                'error': 'Nenhuma imagem fornecida. Envie como arquivo (multipart "image") ou base64 (JSON "image_base64").'
            }), 400

        # Detecta as células (YOLO, se houver modelo; caso contrário OpenCV).
        if USING_YOLO:
            cells = yolo_detector.detect(image) or []
            vis_image = image.copy()
        else:
            cells, vis_image = detector.detect_braille_in_image(image)

        if not cells:
            return jsonify({
                'success': True,
                'text': '',
                'cells_detected': 0,
                'detector': detector_name(),
                'message': 'Nenhum padrão de Braille detectado na imagem.'
            })

        text = converter.convert_cells(cells)

        # Imagem com as detecções destacadas.
        _, buffer = cv2.imencode('.jpg', vis_image)
        annotated = f'data:image/jpeg;base64,{base64.b64encode(buffer).decode("utf-8")}'

        return jsonify({
            'success': True,
            'text': text,
            'cells_detected': len(cells),
            'detector': detector_name(),
            'cells': [list(c) for c in cells],
            'annotated_image': annotated,
            'message': f'{len(cells)} células de Braille detectadas e traduzidas.'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao processar imagem: {str(e)}'
        }), 500


def detector_name():
    """Nome do detector ativo (yolo ou opencv)."""
    return 'yolo' if USING_YOLO else 'opencv'
