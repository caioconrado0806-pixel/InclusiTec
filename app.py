"""
Inclusitec - Backend de Detecção de Braille com YOLO
=====================================================
Servidor Flask que recebe imagens, detecta padrões de Braille usando YOLO
e converte para texto em português brasileiro.
"""

import os
import io
import base64
import cv2
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Tenta importar YOLO (Ultralytics) - opcional
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Aviso: Ultralytics não instalado. Usando detecção por OpenCV.")

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ============================================================
# MAPEAMENTO BRAILLE -> PORTUGUÊS BRASILEIRO
# ============================================================

# Mapeamento completo de células Braille (6 pontos) para letras do português
# Formato: (ponto1, ponto2, ponto3, ponto4, ponto5, ponto6) -> letra
# Pontos: 1=superior-esquerdo, 2=médio-esquerdo, 3=inferior-esquerdo
#         4=superior-direito, 5=médio-direito, 6=inferior-direito

BRAILLE_TO_PT_BR = {
    # Letras básicas
    (1, 0, 0, 0, 0, 0): 'a',
    (1, 1, 0, 0, 0, 0): 'b',
    (1, 0, 0, 1, 0, 0): 'c',
    (1, 0, 0, 1, 1, 0): 'd',
    (1, 0, 0, 0, 1, 0): 'e',
    (1, 1, 0, 1, 0, 0): 'f',
    (1, 1, 0, 1, 1, 0): 'g',
    (1, 1, 0, 0, 1, 0): 'h',
    (0, 1, 0, 1, 0, 0): 'i',
    (0, 1, 0, 1, 1, 0): 'j',
    (1, 0, 1, 0, 0, 0): 'k',
    (1, 1, 1, 0, 0, 0): 'l',
    (1, 0, 1, 1, 0, 0): 'm',
    (1, 0, 1, 1, 1, 0): 'n',
    (1, 0, 1, 0, 1, 0): 'o',
    (1, 1, 1, 1, 0, 0): 'p',
    (1, 1, 1, 1, 1, 0): 'q',
    (1, 1, 1, 0, 1, 0): 'r',
    (0, 1, 1, 1, 0, 0): 's',
    (0, 1, 1, 1, 1, 0): 't',
    (1, 0, 1, 0, 0, 1): 'u',
    (1, 1, 1, 0, 0, 1): 'v',
    (0, 1, 0, 1, 1, 1): 'w',
    (1, 0, 1, 1, 0, 1): 'x',
    (1, 0, 1, 1, 1, 1): 'y',
    (1, 0, 1, 0, 1, 1): 'z',
    
    # Acentos e caracteres especiais do português
    (0, 0, 0, 0, 0, 1): 'á',  # ponto 6
    (0, 1, 0, 0, 1, 0): 'à',  # pontos 2,5
    (0, 1, 0, 0, 1, 1): 'â',  # pontos 2,5,6
    (0, 1, 0, 0, 0, 1): 'ã',  # pontos 2,6
    (0, 0, 0, 0, 1, 1): 'é',  # pontos 5,6
    (0, 0, 0, 1, 0, 1): 'ê',  # pontos 4,6
    (0, 0, 0, 1, 1, 1): 'í',  # pontos 4,5,6
    (0, 0, 1, 0, 0, 1): 'ó',  # pontos 3,6
    (0, 0, 1, 0, 1, 1): 'ô',  # pontos 3,5,6
    (0, 0, 1, 0, 1, 0): 'õ',  # pontos 3,5
    (0, 0, 1, 1, 0, 1): 'ú',  # pontos 3,4,6
    (0, 0, 1, 1, 1, 1): 'ç',  # pontos 3,4,5,6
    
    # Números (prefixo: ponto 3,4,5,6 = ⠼)
    (0, 0, 1, 1, 1, 1): '#',  # indicador de número
    
    # Pontuação
    (0, 1, 0, 0, 0, 0): ',',
    (0, 1, 1, 0, 0, 0): ';',
    (0, 1, 0, 0, 1, 0): ':',
    (0, 0, 1, 0, 0, 0): '.',
    (0, 1, 0, 1, 0, 0): '!',
    (0, 1, 0, 0, 0, 1): '?',
    (0, 0, 1, 0, 0, 1): '"',
    (0, 0, 0, 0, 0, 0): ' ',  # espaço (célula vazia)
}

# Mapeamento de números (após o indicador ⠼)
BRAILLE_NUMBERS = {
    (1, 0, 0, 0, 0, 0): '1',
    (1, 1, 0, 0, 0, 0): '2',
    (1, 0, 0, 1, 0, 0): '3',
    (1, 0, 0, 1, 1, 0): '4',
    (1, 0, 0, 0, 1, 0): '5',
    (1, 1, 0, 1, 0, 0): '6',
    (1, 1, 0, 1, 1, 0): '7',
    (1, 1, 0, 0, 1, 0): '8',
    (0, 1, 0, 1, 0, 0): '9',
    (0, 1, 0, 1, 1, 0): '0',
}


# ============================================================
# DETECTOR DE BRAILLE COM YOLO (ULTRALYTICS)
# ============================================================

class YOLOBrailleDetector:
    """
    Detector de Braille usando YOLO (Ultralytics).
    
    Para usar um modelo YOLO treinado:
    1. Treine um modelo com dataset de imagens de Braille
    2. Salve o modelo como 'braille_yolo.pt'
    3. O detector carregará automaticamente o modelo
    
    Classes esperadas no modelo YOLO:
    - 26 classes (a-z) ou
    - 6 classes (pontos 1-6) para detecção individual de pontos
    """
    
    def __init__(self, model_path='braille_yolo.pt'):
        self.model = None
        self.model_path = model_path
        
        if YOLO_AVAILABLE and os.path.exists(model_path):
            try:
                self.model = YOLO(model_path)
                print(f"Modelo YOLO carregado: {model_path}")
            except Exception as e:
                print(f"Erro ao carregar modelo YOLO: {e}")
    
    def is_available(self):
        return self.model is not None
    
    def detect(self, image):
        """
        Detecta Braille usando YOLO.
        Retorna lista de células detectadas.
        """
        if not self.is_available():
            return None
        
        results = self.model(image, verbose=False)
        
        cells = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                
                if conf > 0.5:  # Confiança mínima
                    # Converte classe YOLO para padrão de pontos
                    cell = self._class_to_cell(cls)
                    cells.append(cell)
        
        return cells
    
    def _class_to_cell(self, cls):
        """Converte classe YOLO para tupla de pontos Braille."""
        # Mapeamento padrão: classes 0-25 = letras a-z
        letter = chr(ord('a') + cls) if cls < 26 else '?'
        
        # Converte letra para padrão de pontos
        for pattern, char in BRAILLE_TO_PT_BR.items():
            if char == letter:
                return pattern
        
        return (0, 0, 0, 0, 0, 0)


# ============================================================
# DETECTOR DE BRAILLE COM COMPUTAÇÃO VISUAL (OPENCV)
# ============================================================

class BrailleDetector:
    """
    Detector de padrões de Braille em imagens.
    
    Utiliza técnicas de visão computacional (OpenCV) para detectar
    os pontos elevados do Braille. A arquitetura permite substituir
    facilmente por um modelo YOLO treinado.
    """
    
    def __init__(self):
        self.min_dot_radius = 3
        self.max_dot_radius = 25
        self.min_distance_between_dots = 15
        self.max_distance_between_dots = 80
        
    def preprocess_image(self, image):
        """Pré-processa a imagem para detecção de pontos."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        return gray, blurred
    
    def detect_dots(self, blurred_image):
        """Detecta círculos/pontos usando Transformada de Hough."""
        circles = cv2.HoughCircles(
            blurred_image,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=self.min_distance_between_dots,
            param1=50,
            param2=20,
            minRadius=self.min_dot_radius,
            maxRadius=self.max_dot_radius
        )
        
        if circles is None:
            return []
        
        return np.uint16(np.around(circles[0]))
    
    def cluster_dots_into_cells(self, dots):
        """
        Agrupa os pontos detectados em células Braille.
        Cada célula Braille tem 6 pontos possíveis (2 colunas x 3 linhas).
        """
        if len(dots) < 2:
            return []
        
        # Ordena pontos por posição Y (linhas) e depois X (colunas)
        dots_sorted = sorted(dots, key=lambda d: (d[1], d[0]))
        
        cells = []
        current_cell_dots = []
        last_y = None
        
        for dot in dots_sorted:
            x, y, r = dot
            
            if last_y is not None and abs(y - last_y) > self.max_distance_between_dots:
                # Nova linha de células
                if current_cell_dots:
                    cells.extend(self._split_line_into_cells(current_cell_dots))
                current_cell_dots = []
            
            current_cell_dots.append((x, y, r))
            last_y = y
        
        if current_cell_dots:
            cells.extend(self._split_line_into_cells(current_cell_dots))
        
        return cells
    
    def _split_line_into_cells(self, line_dots):
        """Divide uma linha de pontos em células individuais."""
        if not line_dots:
            return []
        
        # Ordena por X
        line_dots_sorted = sorted(line_dots, key=lambda d: d[0])
        
        cells = []
        current_cell = []
        last_x = None
        
        for dot in line_dots_sorted:
            x, y, r = dot
            
            if last_x is not None and abs(x - last_x) > self.max_distance_between_dots:
                if current_cell:
                    cells.append(self._classify_cell(current_cell))
                current_cell = []
            
            current_cell.append((x, y, r))
            last_x = x
        
        if current_cell:
            cells.append(self._classify_cell(current_cell))
        
        return cells
    
    def _classify_cell(self, cell_dots):
        """
        Classifica uma célula Braille identificando quais dos 6 pontos estão ativos.
        Retorna uma tupla de 6 valores binários.
        """
        if not cell_dots:
            return (0, 0, 0, 0, 0, 0)
        
        # Calcula o centro da célula
        xs = [d[0] for d in cell_dots]
        ys = [d[1] for d in cell_dots]
        center_x = (min(xs) + max(xs)) / 2
        center_y = (min(ys) + max(ys)) / 2
        
        # Determina limites para classificar posição dos pontos
        x_threshold = center_x
        y_range = max(ys) - min(ys) if max(ys) != min(ys) else 1
        
        # Inicializa os 6 pontos como inativos
        points = [0, 0, 0, 0, 0, 0]  # 1,2,3 (esquerda) e 4,5,6 (direita)
        
        for dot in cell_dots:
            x, y, r = dot
            
            # Determina coluna (esquerda=0, direita=1)
            col = 0 if x < x_threshold else 1
            
            # Determina linha (0=topo, 1=meio, 2=baixo)
            y_normalized = (y - min(ys)) / y_range if y_range > 0 else 0.5
            if y_normalized < 0.33:
                row = 0
            elif y_normalized < 0.66:
                row = 1
            else:
                row = 2
            
            # Mapeia para o índice do ponto
            # Pontos 1,2,3 = coluna esquerda (índices 0,1,2)
            # Pontos 4,5,6 = coluna direita (índices 3,4,5)
            point_index = row + (col * 3)
            points[point_index] = 1
        
        return tuple(points)
    
    def detect_braille_in_image(self, image):
        """
        Método principal: detecta Braille em uma imagem e retorna as células.
        """
        gray, blurred = self.preprocess_image(image)
        dots = self.detect_dots(blurred)
        
        if len(dots) == 0:
            return [], image
        
        cells = self.cluster_dots_into_cells(dots)
        
        # Desenha os pontos detectados na imagem para visualização
        vis_image = image.copy()
        for dot in dots:
            x, y, r = dot
            cv2.circle(vis_image, (x, y), r, (0, 255, 0), 2)
            cv2.circle(vis_image, (x, y), 2, (0, 0, 255), 3)
        
        return cells, vis_image


# ============================================================
# CONVERSOR DE BRAILLE PARA PORTUGUÊS
# ============================================================

class BrailleToPortuguese:
    """Converte células Braille para texto em português brasileiro."""
    
    def __init__(self):
        self.number_mode = False
    
    def reset(self):
        self.number_mode = False
    
    def convert_cells(self, cells):
        """
        Converte uma lista de células Braille para texto.
        
        Args:
            cells: Lista de tuplas (6 valores binários)
            
        Returns:
            Texto em português brasileiro
        """
        self.reset()
        result = []
        
        for cell in cells:
            char = self._convert_single_cell(cell)
            result.append(char)
        
        return ''.join(result)
    
    def _convert_single_cell(self, cell):
        """Converte uma única célula Braille para caractere."""
        # Verifica se é o indicador de número
        if cell == (0, 0, 1, 1, 1, 1):
            self.number_mode = True
            return ''
        
        # Se estamos em modo número, converte como dígito
        if self.number_mode:
            if cell in BRAILLE_NUMBERS:
                return BRAILLE_NUMBERS[cell]
            else:
                # Sai do modo número se encontrar não-dígito
                self.number_mode = False
        
        # Converte como letra/caractere normal
        if cell in BRAILLE_TO_PT_BR:
            return BRAILLE_TO_PT_BR[cell]
        
        # Célula desconhecida
        return '?'


# ============================================================
# INICIALIZAÇÃO DO DETECTOR
# ============================================================

# Tenta usar YOLO primeiro, fallback para OpenCV
yolo_detector = YOLOBrailleDetector()
detector = BrailleDetector()
converter = BrailleToPortuguese()

USING_YOLO = yolo_detector.is_available()


# ============================================================
# ROTAS DA API
# ============================================================

@app.route('/')
def index():
    """Serve o frontend."""
    return send_from_directory('.', 'index.html')


@app.route('/api/detect-braille', methods=['POST'])
def detect_braille():
    """
    API para detectar Braille em uma imagem.
    
    Recebe uma imagem (base64 ou upload) e retorna o texto traduzido.
    """
    try:
        # Verifica se a imagem foi enviada como base64 ou arquivo
        if 'image' in request.files:
            file = request.files['image']
            image_bytes = file.read()
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif request.json and 'image_base64' in request.json:
            base64_str = request.json['image_base64']
            # Remove prefixo data:image/...;base64, se presente
            if ',' in base64_str:
                base64_str = base64_str.split(',')[1]
            image_bytes = base64.b64decode(base64_str)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            return jsonify({
                'success': False,
                'error': 'Nenhuma imagem fornecida. Envie como arquivo ou base64.'
            }), 400
        
        if image is None:
            return jsonify({
                'success': False,
                'error': 'Não foi possível processar a imagem.'
            }), 400
        
        # Detecta as células de Braille (YOLO ou OpenCV)
        if USING_YOLO:
            cells = yolo_detector.detect(image)
            vis_image = image.copy()
            if cells is None:
                cells = []
        else:
            cells, vis_image = detector.detect_braille_in_image(image)
        
        if not cells:
            return jsonify({
                'success': True,
                'text': '',
                'cells_detected': 0,
                'detector': 'yolo' if USING_YOLO else 'opencv',
                'message': 'Nenhum padrão de Braille detectado na imagem.'
            })
        
        # Converte para português
        text = converter.convert_cells(cells)
        
        # Codifica a imagem com detecções para retorno
        _, buffer = cv2.imencode('.jpg', vis_image)
        vis_image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'text': text,
            'cells_detected': len(cells),
            'detector': 'yolo' if USING_YOLO else 'opencv',
            'cells': [list(c) for c in cells],
            'annotated_image': f'data:image/jpeg;base64,{vis_image_base64}',
            'message': f'{len(cells)} células de Braille detectadas e traduzidas.'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Erro ao processar imagem: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Verifica se o servidor está funcionando."""
    return jsonify({
        'status': 'ok',
        'service': 'Inclusitec Braille Detector',
        'opencv_version': cv2.__version__
    })


# ============================================================
# PONTO DE ENTRADA
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("  Inclusitec - Detector de Braille com IA")
    print("=" * 60)
    print(f"  OpenCV versão: {cv2.__version__}")
    print(f"  YOLO disponível: {YOLO_AVAILABLE}")
    print(f"  Detector ativo: {'YOLO' if USING_YOLO else 'OpenCV'}")
    print(f"  Servidor iniciando em: http://localhost:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
