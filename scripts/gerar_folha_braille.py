"""
Gera uma imagem de uma folha em Braille com um texto explicando o Inclusitec.

Usa o mapeamento oficial do projeto (backend/braille/mapping.py),
garantindo que a folha gerada seja legível pelo detector.

Uso (da raiz do projeto): py scripts/gerar_folha_braille.py
"""

import os
import sys

# Permite importar o pacote do projeto a partir da raiz.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PIL import Image, ImageDraw, ImageFont

from backend.braille.mapping import PT_BR_TO_BRAILLE

# Converte os padrões (tuplas 0/1) para listas de pontos ativos (1-6).
BRAILLE = {
    char: [i for i, ativo in enumerate(padrao, start=1) if ativo]
    for char, padrao in PT_BR_TO_BRAILLE.items()
}

TEXTO = (
    "inclusitec e um sistema de acessibilidade que transforma "
    "braille em texto falado usando python, flask e visao computacional. "
    "a camera captura a folha em braille, o opencv detecta os pontos "
    "e cada cela e convertida em portugues do brasil. "
    "o projeto roda no seu proprio computador, nao precisa de internet "
    "e responde em tempo real para pessoas ciegas. "
    "acesse localhost na porta 5000."
)


def quebrar_texto(texto, colunas=34):
    """Quebra o texto em linhas de no maximo 'colunas' caracteres."""
    palavras = texto.split()
    linhas = []
    atual = ""
    for palavra in palavras:
        if not atual:
            atual = palavra
        elif len(atual) + 1 + len(palavra) <= colunas:
            atual += " " + palavra
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def ponto_para_xy(ponto, x, y, dx, dy):
    coluna = 0 if ponto in (1, 2, 3) else 1
    linha = {1: 0, 2: 1, 3: 2}[ponto if ponto <= 3 else ponto - 3]
    return x + coluna * dx, y + linha * dy


def main():
    linhas = quebrar_texto(TEXTO)

    # Espaçamento compatível com o detector (backend/braille/detector.py):
    # - pontos dentro da célula: 2*dx e 2*dy < max_distance_between_dots (80)
    # - entre células: gap > max_distance_between_dots (80)
    # - entre linhas: > max_distance_between_dots (80)
    dx, dy = 25, 25
    avancos_x = dx * 2 + 90          # 140 px por célula (gap de 115 px)
    margem_x = 60
    espaco_linha = dy * 2 + 40       # 90 px entre linhas

    largura = margem_x * 2 + avancos_x * max(len(linha) for linha in linhas)
    altura = 150 + espaco_linha * len(linhas) + 120

    img = Image.new('RGB', (largura, altura), (247, 244, 236))
    d = ImageDraw.Draw(img)

    try:
        fonte_titulo = ImageFont.truetype("segoeuib.ttf", 34)
        fonte_legenda = ImageFont.truetype("segoeui.ttf", 22)
    except OSError:
        fonte_titulo = ImageFont.load_default()
        fonte_legenda = ImageFont.load_default()

    d.text((60, 40), "FOLHA BRAILLE - INCLUSITEC", fill=(60, 60, 60), font=fonte_titulo)
    d.line([(60, 90), (largura - 60, 90)], fill=(150, 150, 150), width=2)

    y_linha = 140
    for linha in linhas:
        x_celula = margem_x
        for char in linha.lower():
            pontos = BRAILLE.get(char, BRAILLE.get('?', []))
            for ponto in pontos:
                px, py = ponto_para_xy(ponto, x_celula, y_linha, dx, dy)
                d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=(25, 25, 25))
            x_celula += avancos_x
        y_linha += espaco_linha

    d.text((60, altura - 50),
           "Texto em Braille - Leitura: Inclusitec (Python + OpenCV)",
           fill=(90, 90, 90), font=fonte_legenda)

    img.save("folha_braille_inclusitec.png")
    print(f"folha_braille_inclusitec.png gerado ({largura}x{altura}, {len(linhas)} linhas).")


if __name__ == '__main__':
    main()