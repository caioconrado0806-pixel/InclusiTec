"""
Detecção de padrões de Braille em imagens.

IA única do projeto: utiliza visão computacional (OpenCV)
para localizar os pontos elevados do Braille e agrupá-los
em células de 6 pontos.

Toda a detecção da aplicação (API web, cliente desktop e
testes) passa por esta classe — não existe outro motor de
detecção.
"""

import cv2
import numpy as np

import config


class BrailleDetector:
    """
    Detector de padrões de Braille em imagens (OpenCV).

    Fluxo: pré-processamento -> detecção de pontos (Hough) ->
    agrupamento em linhas -> divisão em células -> classificação
    dos 6 pontos de cada célula.
    """

    def __init__(self):
        settings = config.DETECTION_SETTINGS
        self.min_dot_radius = settings.get('min_dot_radius', 3)
        self.max_dot_radius = settings.get('max_dot_radius', 25)
        self.min_distance_between_dots = settings.get('min_distance_between_dots', 15)
        self.max_distance_between_dots = settings.get('max_distance_between_dots', 80)

    # -------------------------------------------------------------
    # Etapas do pipeline
    # -------------------------------------------------------------

    def preprocess_image(self, image):
        """Pré-processa a imagem para detecção de pontos."""
        # Aceita imagens BGR (3 canais) ou em tons de cinza.
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        return gray, blurred

    def detect_dots(self, blurred_image):
        """Detecta círculos/pontos usando a Transformada de Hough."""
        circles = cv2.HoughCircles(
            blurred_image,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=self.min_distance_between_dots,
            param1=50,
            param2=20,
            minRadius=self.min_dot_radius,
            maxRadius=self.max_dot_radius,
        )

        if circles is None:
            return []

        return np.uint16(np.around(circles[0]))

    def cluster_dots_into_cells(self, dots):
        """Agrupa os pontos detectados em células Braille (6 pontos possíveis)."""
        if len(dots) < 2:
            return []

        # Ordena por linha (Y) e depois por coluna (X).
        dots_sorted = sorted(dots, key=lambda d: (d[1], d[0]))

        cells = []
        line_dots = []
        last_y = None

        for dot in dots_sorted:
            x, y, r = dot
            if last_y is not None and abs(y - last_y) > self.max_distance_between_dots:
                cells.extend(self._split_line_into_cells(line_dots))
                line_dots = []
            line_dots.append((x, y, r))
            last_y = y

        cells.extend(self._split_line_into_cells(line_dots))
        return cells

    def _split_line_into_cells(self, line_dots):
        """Divide uma linha de pontos em células individuais."""
        if not line_dots:
            return []

        # Grade de linhas da célula, estimada a partir de TODOS
        # os pontos da linha (não por célula).
        row_centers = self._estimate_row_centers(line_dots)

        line_dots_sorted = sorted(line_dots, key=lambda d: d[0])

        cells = []
        current_cell = []
        last_x = None

        for dot in line_dots_sorted:
            x, y, r = dot
            if last_x is not None and abs(x - last_x) > self.max_distance_between_dots:
                if current_cell:
                    cells.append(self._classify_cell(current_cell, row_centers))
                current_cell = []
            current_cell.append((x, y, r))
            last_x = x

        if current_cell:
            cells.append(self._classify_cell(current_cell, row_centers))

        return cells

    def _estimate_row_centers(self, line_dots):
        """
        Estima as posições verticais (centros) das até 3 linhas
        de pontos da grade da célula, usando todos os pontos da
        linha.

        Isso corrige a classificação de células que não possuem
        pontos em todas as linhas. Exemplo: 'd' (pontos 1,4,5)
        tem pontos apenas nas linhas superior e do meio; com a
        grade da linha, a linha do meio é reconhecida como tal
        (o algoritmo antigo a confundia com a linha inferior).
        """
        ys = sorted(set(round(dot[1], 1) for dot in line_dots))
        tolerance = max(4, self.min_distance_between_dots // 2)

        clusters = []
        for y in ys:
            if clusters and y - clusters[-1][-1] <= tolerance:
                clusters[-1].append(y)
            else:
                clusters.append([y])

        # Ruídos podem gerar agrupamentos extras: ficam os 3 maiores.
        clusters.sort(key=len, reverse=True)
        return sorted(sum(c) / len(c) for c in clusters[:3])

    def _estimate_column_centers(self, cell_dots):
        """
        Estima as posições horizontais das 2 colunas de pontos
        de uma célula.

        Returns:
            Lista com 1 ou 2 centros (x médio de cada coluna).
        """
        xs = sorted(set(round(dot[0], 1) for dot in cell_dots))
        tolerance = max(4, self.min_distance_between_dots // 2)

        clusters = []
        for x in xs:
            if clusters and x - clusters[-1][-1] <= tolerance:
                clusters[-1].append(x)
            else:
                clusters.append([x])

        clusters.sort(key=len, reverse=True)
        return sorted(sum(c) / len(c) for c in clusters[:2])

    def _classify_cell(self, cell_dots, row_centers):
        """
        Classifica uma célula identificando quais dos 6 pontos estão ativos.
        Retorna uma tupla de 6 valores binários.
        """
        if not cell_dots:
            return (0, 0, 0, 0, 0, 0)

        col_centers = self._estimate_column_centers(cell_dots)

        points = [0, 0, 0, 0, 0, 0]

        for dot in cell_dots:
            x, y, r = dot

            # Coluna: 0 = esquerda, 1 = direita.
            if len(col_centers) == 2:
                mid = (col_centers[0] + col_centers[1]) / 2
                col = 1 if x > mid else 0
            else:
                # Coluna única: sempre a esquerda, pois não
                # existem letras com pontos apenas na coluna direita.
                col = 0

            # Linha: 0 = topo, 1 = meio, 2 = base.
            if row_centers:
                row = min(range(len(row_centers)),
                          key=lambda i: abs(y - row_centers[i]))
                # Com 1 ou 2 centros, os índices correspondem
                # às linhas superiores (células de linha única
                # são sempre a linha do topo; de 2 linhas, as
                # linhas do topo e do meio).
            else:
                row = 0

            point_index = row + (col * 3)
            points[point_index] = 1

        return tuple(points)

    # -------------------------------------------------------------
    # API principal
    # -------------------------------------------------------------

    def detect_braille_in_image(self, image):
        """
        Método principal: detecta Braille em uma imagem.

        Returns:
            (cells, annotated_image) - lista de células e a imagem
            com os pontos destacados para visualização.
        """
        gray, blurred = self.preprocess_image(image)
        dots = self.detect_dots(blurred)

        if len(dots) == 0:
            return [], image

        cells = self.cluster_dots_into_cells(dots)

        # Desenha os pontos detectados para visualização.
        vis_image = image.copy()
        for dot in dots:
            x, y, r = dot
            cv2.circle(vis_image, (x, y), r, (0, 255, 0), 2)
            cv2.circle(vis_image, (x, y), 2, (0, 0, 255), 3)

        return cells, vis_image
