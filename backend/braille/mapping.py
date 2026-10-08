"""
Mapeamentos Braille <-> Português brasileiro (PT-BR).

Fonte única da verdade do projeto: a API web, o cliente
desktop, os testes e os scripts geradores importam
estes mapeamentos.

Convenção dos pontos de uma célula Braille:

    1 = superior-esquerdo    4 = superior-direito
    2 = médio-esquerdo       5 = médio-direito
    3 = inferior-esquerdo    6 = inferior-direito

Uma célula é representada por uma tupla de 6 valores binários:
    (ponto1, ponto2, ponto3, ponto4, ponto5, ponto6)

Tabela oficial: "Grafia Braille para a Língua Portuguesa"
(MEC/SEESP, Portaria nº 2.678/2002), conforme ABRES.
"""

# Célula indicadora de numeração (⠼ = pontos 3, 4, 5 e 6).
NUMBER_INDICATOR = (0, 0, 1, 1, 1, 1)

# Letras básicas (a-z), acentos do português e pontuação.
BRAILLE_TO_PT_BR = {
    # ---------------------------------------------------------
    # Letras básicas (padrão internacional)
    # ---------------------------------------------------------
    (1, 0, 0, 0, 0, 0): 'a',   # ⠁
    (1, 1, 0, 0, 0, 0): 'b',   # ⠃
    (1, 0, 0, 1, 0, 0): 'c',   # ⠉
    (1, 0, 0, 1, 1, 0): 'd',   # ⠙
    (1, 0, 0, 0, 1, 0): 'e',   # ⠑
    (1, 1, 0, 1, 0, 0): 'f',   # ⠋
    (1, 1, 0, 1, 1, 0): 'g',   # ⠛
    (1, 1, 0, 0, 1, 0): 'h',   # ⠓
    (0, 1, 0, 1, 0, 0): 'i',   # ⠊
    (0, 1, 0, 1, 1, 0): 'j',   # ⠚
    (1, 0, 1, 0, 0, 0): 'k',   # ⠅
    (1, 1, 1, 0, 0, 0): 'l',   # ⠇
    (1, 0, 1, 1, 0, 0): 'm',   # ⠍
    (1, 0, 1, 1, 1, 0): 'n',   # ⠝
    (1, 0, 1, 0, 1, 0): 'o',   # ⠕
    (1, 1, 1, 1, 0, 0): 'p',   # ⠏
    (1, 1, 1, 1, 1, 0): 'q',   # ⠟
    (1, 1, 1, 0, 1, 0): 'r',   # ⠗
    (0, 1, 1, 1, 0, 0): 's',   # ⠎
    (0, 1, 1, 1, 1, 0): 't',   # ⠞
    (1, 0, 1, 0, 0, 1): 'u',   # ⠥
    (1, 1, 1, 0, 0, 1): 'v',   # ⠧
    (0, 1, 0, 1, 1, 1): 'w',   # ⠺
    (1, 0, 1, 1, 0, 1): 'x',   # ⠭
    (1, 0, 1, 1, 1, 1): 'y',   # ⠽
    (1, 0, 1, 0, 1, 1): 'z',   # ⠵

    # ---------------------------------------------------------
    # Acentos do português (tabela oficial MEC/ABRES)
    # ---------------------------------------------------------
    (1, 1, 1, 0, 1, 1): 'á',   # ⠷  pontos 1,2,3,5,6
    (1, 1, 0, 1, 0, 1): 'à',   # ⠫  pontos 1,2,4,6
    (1, 0, 0, 0, 0, 1): 'â',   # ⠡  pontos 1,6
    (0, 0, 1, 1, 1, 0): 'ã',   # ⠜  pontos 3,4,5
    (1, 1, 1, 1, 1, 1): 'é',   # ⠿  pontos 1,2,3,4,5,6
    (1, 1, 0, 0, 0, 1): 'ê',   # ⠣  pontos 1,2,6
    (0, 0, 1, 1, 0, 0): 'í',   # ⠌  pontos 3,4
    (0, 0, 1, 1, 0, 1): 'ó',   # ⠬  pontos 3,4,6
    (1, 0, 0, 1, 1, 1): 'ô',   # ⠹  pontos 1,4,5,6
    (0, 1, 0, 1, 0, 1): 'õ',   # ⠪  pontos 2,4,6
    (0, 1, 1, 1, 1, 1): 'ú',   # ⠾  pontos 2,3,4,5,6
    (1, 1, 1, 1, 0, 1): 'ç',   # ⠯  pontos 1,2,3,4,6

    # ---------------------------------------------------------
    # Pontuação (tabela oficial)
    # ---------------------------------------------------------
    (0, 1, 0, 0, 0, 0): ',',   # ⠂  ponto 2
    (0, 1, 1, 0, 0, 0): ';',   # ⠆  pontos 2,3
    (0, 1, 0, 0, 1, 0): ':',   # ⠒  pontos 2,5
    (0, 1, 1, 0, 1, 0): '!',   # ⠖  pontos 2,3,5
    (0, 1, 0, 0, 0, 1): '?',   # ⠢  pontos 2,6
    (0, 1, 1, 0, 0, 1): '"',   # ⠦  pontos 2,3,6
    (0, 0, 1, 0, 0, 0): '.',   # ⠄  ponto 3
    (0, 0, 1, 0, 0, 1): '-',   # ⠤  pontos 3,6
    (0, 0, 0, 0, 0, 0): ' ',   # célula vazia = espaço
}

# Dígitos utilizados após o indicador de número (⠼).
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

# Mapa reverso: caractere -> padrão de pontos (usado para gerar Braille).
PT_BR_TO_BRAILLE = {char: pattern for pattern, char in BRAILLE_TO_PT_BR.items()}
