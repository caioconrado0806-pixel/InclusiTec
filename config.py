"""
Configuração central do Inclusitec.

Todas as constantes do projeto ficam aqui:
porta do servidor, limites de upload, parâmetros
de detecção e diretórios de dados.
"""

import os
import tempfile

# -------------------------------------------------------------
# Diretórios
# -------------------------------------------------------------

# Raiz do projeto (pasta que contém este arquivo).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ambiente serverless (Vercel): o disco é efêmero, então os dados
# de runtime vão para /tmp (o único diretório gravável).
ON_VERCEL = os.environ.get('VERCEL') == '1'

if ON_VERCEL:
    # Diretório de dados persistentes (cadastros) em serverless.
    DATA_DIR = os.path.join(tempfile.gettempdir(), 'inclusitec', 'data')
else:
    # Diretório de dados persistentes (cadastros).
    DATA_DIR = os.path.join(BASE_DIR, 'data')

# Conversões PDF -> Braille geram arquivos aqui (.brf/.brl/.txt).
BRAILLE_JOBS_DIR = os.path.join(DATA_DIR, 'braille_jobs')

# Frontend servido pelo Flask.
TEMPLATE_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'frontend', 'static')

# -------------------------------------------------------------
# Servidor
# -------------------------------------------------------------

HOST = '0.0.0.0'
PORT = int(os.environ.get('INCLUSITEC_PORT', 5000))
# Debug ativo por padrão localmente; desligado na nuvem (serverless).
_default_debug = '0' if ON_VERCEL else '1'
DEBUG = os.environ.get('INCLUSITEC_DEBUG', _default_debug) == '1'

# -------------------------------------------------------------
# Upload de imagens e PDF
# -------------------------------------------------------------

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'webp'}

# PDF convertido para Braille (maior limite: documentos inteiros).
MAX_PDF_BYTES = 25 * 1024 * 1024  # 25 MB

# Teto único de upload da aplicação (o maior dos dois limites).
MAX_UPLOAD_BYTES = max(MAX_IMAGE_BYTES, MAX_PDF_BYTES)

# Limite de texto extraído de um único PDF (proteção de memória).
MAX_PDF_TEXT_CHARS = 300_000

# -------------------------------------------------------------
# Conversão PDF -> Braille / impressão
# -------------------------------------------------------------

# Células por linha no papel Braille (A4 na horizontal).
BRAILLE_LINE_WIDTH = 40

# -------------------------------------------------------------
# Detecção de Braille
# -------------------------------------------------------------

DETECTION_SETTINGS = {
    # Detecção por OpenCV (padrão)
    'min_dot_radius': 3,
    'max_dot_radius': 25,
    'min_distance_between_dots': 15,
    'max_distance_between_dots': 80,

    # Detecção por YOLO (opcional, requer ultralytics + modelo)
    'yolo_model_path': 'braille_yolo.pt',
    'yolo_min_confidence': 0.5,
}

# -------------------------------------------------------------
# Cadastros
# -------------------------------------------------------------

CADASTRO_FIELDS = ('nome', 'email', 'telefone', 'perfil')
CADASTROS_JSON = os.path.join(DATA_DIR, 'cadastros.json')
CADASTROS_CSV = os.path.join(DATA_DIR, 'cadastros.csv')
