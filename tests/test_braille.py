"""
Testes do núcleo Braille (mapeamento, conversor e detector).

Execute com:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

import cv2
import numpy as np

# Permite executar a partir da raiz do projeto.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.braille import (
    BRAILLE_TO_PT_BR,
    BrailleDetector,
    BrailleToPortuguese,
    NUMBER_INDICATOR,
)

# Mapa reverso para montar células a partir de letras.
PT_BR_TO_BRAILLE = {char: padrao for padrao, char in BRAILLE_TO_PT_BR.items()}


class TestMapeamento(unittest.TestCase):

    def test_tabela_nao_vazia(self):
        self.assertGreater(len(BRAILLE_TO_PT_BR), 40)

    def test_celulas_tem_6_pontos(self):
        for padrao in BRAILLE_TO_PT_BR:
            self.assertEqual(len(padrao), 6)
            self.assertTrue(all(p in (0, 1) for p in padrao))

    def test_chaves_unicas(self):
        # Garante que nenhuma célula foi sobrescrita silenciosamente.
        self.assertEqual(len(BRAILLE_TO_PT_BR), len(set(BRAILLE_TO_PT_BR)))

    def test_caracteres_unicos(self):
        # Caracteres distintos não devem compartilhar o mesmo padrão.
        invertido = {}
        for padrao, char in BRAILLE_TO_PT_BR.items():
            self.assertNotIn(char, invertido,
                             f'Caractere {char!r} mapeado por dois padrões')
            invertido[char] = padrao

    def test_indicador_numero(self):
        self.assertEqual(NUMBER_INDICATOR, (0, 0, 1, 1, 1, 1))


class TestConversor(unittest.TestCase):

    def setUp(self):
        self.conversor = BrailleToPortuguese()

    def test_letras_basicas(self):
        cells = [PT_BR_TO_BRAILLE[letra] for letra in 'abc']
        self.assertEqual(self.conversor.convert_cells(cells), 'abc')

    def test_numero_com_indicador(self):
        # ⠼ (indicador) + ⠁ ⠃ = "12"
        cells = [NUMBER_INDICATOR,
                 (1, 0, 0, 0, 0, 0),
                 (1, 1, 0, 0, 0, 0)]
        self.assertEqual(self.conversor.convert_cells(cells), '12')

    def test_numero_termina_em_letra(self):
        # Após indicador + dígito, uma letra que não é dígito
        # encerra o modo número ('k' = pontos 1,3).
        cells = [NUMBER_INDICATOR,
                 (1, 0, 0, 0, 0, 0),   # 1
                 (1, 0, 1, 0, 0, 0)]   # k
        self.assertEqual(self.conversor.convert_cells(cells), '1k')

    def test_celula_desconhecida(self):
        # Pontos 4 apenas: padrão não mapeado na tabela.
        self.assertEqual(self.conversor.convert_cells([(0, 0, 0, 1, 0, 0)]), '?')

    def test_celula_vazia_e_espaco(self):
        self.assertEqual(self.conversor.convert_cells([(0, 0, 0, 0, 0, 0)]), ' ')


class TestDetector(unittest.TestCase):

    def setUp(self):
        self.detector = BrailleDetector()

    def _imagem_com_pontos(self, pontos, espaco_x=60, espaco_y=80,
                           raio=10, largura=400, altura=300):
        """Desenha pontos brancos (ativos) em fundo preto.

        'pontos' é uma lista de tuplas (coluna, linha) onde
        coluna em {0,1} (esquerda/direita) e linha em {0,1,2}.
        """
        img = np.zeros((altura, largura), dtype=np.uint8)
        for coluna, linha in pontos:
            x = 60 + coluna * espaco_x
            y = 60 + linha * espaco_y
            cv2.circle(img, (x, y), raio, 255, -1)
        return img

    def test_detecta_celula_completa(self):
        """Uma célula com todos os 6 pontos ativos."""
        img = self._imagem_com_pontos([(c, l) for l in range(3) for c in range(2)])
        _, blurred = self.detector.preprocess_image(img)
        dots = self.detector.detect_dots(blurred)
        self.assertEqual(len(dots), 6)

    def test_classifica_celula_c(self):
        """Pontos 1 e 4 ativos -> padrão (1,0,0,1,0,0) = 'c'.

        Obs.: o agrupamento requer ao menos 2 pontos e a
        classificação usa as duas colunas, então o teste
        usa uma célula com pontos nas duas colunas.
        """
        img = self._imagem_com_pontos([(0, 0), (1, 0)])
        _, blurred = self.detector.preprocess_image(img)
        dots = self.detector.detect_dots(blurred)
        cells = self.detector.cluster_dots_into_cells(dots)
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0], (1, 0, 0, 1, 0, 0))

    def test_classifica_celula_d_com_grade_linha(self):
        """'d' (pontos 1,4,5) deve usar a grade da linha.

        Regressão: o algoritmo antigo normalizava as
        linhas pelo min/max da própria célula e lia 'd'
        como pontos 1,4,6. Aqui a linha tem células com
        pontos nas 3 linhas, revelando a grade.
        """
        # Células 'c', 'd' e 'o' em uma linha.
        img = np.zeros((300, 520), dtype=np.uint8)
        celulas = {
            'c': [(0, 0), (1, 0)],
            'd': [(0, 0), (1, 0), (1, 1)],
            'o': [(0, 0), (0, 2), (1, 1)],
        }
        for i, char in enumerate('cdo'):
            for coluna, linha in celulas[char]:
                x = 60 + i * 160 + coluna * 60
                y = 60 + linha * 80
                cv2.circle(img, (x, y), 10, 255, -1)

        cells, _ = self.detector.detect_braille_in_image(img)
        self.assertEqual(len(cells), 3)

        # BRAILLE_TO_PT_BR: padrão de pontos -> caractere.
        detectado = ''.join(BRAILLE_TO_PT_BR.get(c, '?') for c in cells)
        self.assertEqual(detectado, 'cdo')

    def test_imagem_sem_pontos(self):
        img = np.zeros((300, 400), dtype=np.uint8)
        cells, _ = self.detector.detect_braille_in_image(img)
        self.assertEqual(cells, [])

    def test_aceita_imagem_bgr(self):
        """Detector deve aceitar imagens coloridas (BGR)."""
        img = self._imagem_com_pontos([(0, 0), (1, 0)])
        img_bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cells, _ = self.detector.detect_braille_in_image(img_bgr)
        self.assertEqual(cells, [(1, 0, 0, 1, 0, 0)])


if __name__ == '__main__':
    unittest.main(verbosity=2)
