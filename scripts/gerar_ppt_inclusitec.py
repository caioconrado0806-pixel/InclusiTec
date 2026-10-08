"""
Gera a apresentacao do Inclusitec:
  Slide 1 -> print de tela do app.py rodando
  Slide 2 -> texto explicando o Inclusitec escrito em Braille

Grafia Braille conforme "Grafia Braille para a Lingua Portuguesa"
(portaria no 2.678/2002 - MEC / Secretaria de Educacao Especial).
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image, ImageDraw

# ============================================================
# CONFIGURACOES
# ============================================================

RAIZ = os.path.dirname(os.path.abspath(__file__))
PRINT_TELA = os.path.join(RAIZ, "print_tela_inclusitec.png")
PNG_BRAILLE = os.path.join(RAIZ, "braile_texto.png")
ARQ_PPTX = os.path.join(os.path.expanduser("~"), "Desktop", "Inclusitec.pptx")

TEXTO = (
    "O Inclusitec e um sistema de inteligencia artificial que converte imagens "
    "de braille em texto. Ele usa visao computacional e aprendizado profundo "
    "para identificar os pontos em relevo de cada celula e transformar o "
    "conteudo em palavras em portugues. Assim, pessoas cegas ou com baixa "
    "visao conseguem ler documentos, cartazes e materiais impressos em "
    "braille com mais autonomia e dignidade."
)

# ============================================================
# TABELA BRAILLE PORTUGUES - BRASIL (6 PONTOS)
# "123" indica os pontos levantados da celula.
# ============================================================

BRAILLE = {
    # --- Alfabeto basico ---
    "a": "1", "b": "12", "c": "14", "d": "145", "e": "15",
    "f": "124", "g": "1245", "h": "125", "i": "24", "j": "245",
    "k": "13", "l": "123", "m": "134", "n": "1345", "o": "135",
    "p": "1234", "q": "12345", "r": "1235", "s": "234", "t": "2345",
    "u": "136", "v": "1236", "w": "2456", "x": "1346", "y": "13456",
    "z": "1356",

    # --- Acentos e letra cedilha ---
    "\u00e1": "12356",   # a-agudo
    "\u00e0": "1246",    # a-grave
    "\u00e2": "16",      # a-circunflexo
    "\u00e3": "345",     # a-til
    "\u00e9": "2345",    # e-agudo
    "\u00ea": "126",     # e-circunflexo
    "\u00ed": "34",      # i-agudo
    "\u00f3": "346",     # o-agudo
    "\u00f4": "1456",    # o-circunflexo
    "\u00f5": "246",     # o-til
    "\u00fa": "23456",   # u-agudo
    "\u00fc": "1256",    # u-trema
    "\u00e7": "12346",   # c-cedilha

    # --- Pontuacao ---
    ",": "2",
    ".": "256",
    ";": "23",
    ":": "25",
    "!": "235",
    "?": "26",
    "-": "36",
    "\u2014": "36",       # traco
    "\"": "35",
    "'": "3",
    "/": "34",
    "*": "45",
    "$": "456",
    "+": "5",
    "=": "2356",

    # --- Indicadores ---
    "#": "3456",   # indicador de numero
}

# Numeros:-indicator 3456 seguido da celula a-j (a=1 ... i=9, j=0)
NUMEROS = {ch: str(n) for n, ch in enumerate("abcdefghij", start=1)}
NUMEROS["j"] = "0"


def pontos_para_bits(pontos):
    """'145' -> mascara de bits (bit 0 = ponto 1 ... bit 5 = ponto 6)."""
    return sum(1 << (int(p) - 1) for p in pontos)


def celula(ch):
    """Caractere -> mascara de pontos (0..63)."""
    return pontos_para_bits(BRAILLE.get(ch, "0"))


def para_unicode_br(texto):
    """Texto latin -> braille unicode (padrao digital, U+2800)."""
    saida = []
    em_numero = False
    for ch in texto.lower():
        if ch in NUMEROS:
            if not em_numero:
                saida.append("\u283c")  # indicador de numero
                em_numero = True
            saida.append(chr(0x2800 + pontos_para_bits(BRAILLE[ch])))
            continue
        em_numero = False
        saida.append(chr(0x2800 + pontos_para_bits(BRAILLE.get(ch, ""))))
    return "".join(saida)


def linhas_unicode(max_colunas=52):
    """Mesmo quebra de linha da imagem, mas em braille unicode."""
    return ["".join(chr(0x2800 + bits) for bits in linha)
            for linha in texto_para_celulas(TEXTO, max_colunas)]


def texto_para_celulas(texto, max_colunas=52):
    """Texto -> lista de linhas, cada linha uma lista de mascaras de pontos.

    A quebra acontece sempre antes de uma palavra (nunca no meio dela).
    """
    linhas, linha = [], []
    for palavra in texto.split():
        celulas = [celula(c) for c in palavra.lower()]
        if linha and len(linha) + 1 + len(celulas) > max_colunas:
            linhas.append(linha)
            linha = list(celulas)
        else:
            if linha:
                linha.append(0)  # celula vazia = espaco
            linha.extend(celulas)
    if linha:
        linhas.append(linha)
    return linhas


def render_braille_png(linhas, caminho, escala=34):
    """Desenha as celulas de braille como pontos em relevo."""
    margem = int(escala * 0.9)
    espaco_x = int(escala * 1.62)
    espaco_y = int(escala * 1.50)
    col_max = max(len(l) for l in linhas)

    larg = margem * 2 + col_max * espaco_x
    alt = margem * 2 + len(linhas) * espaco_y

    img = Image.new("RGB", (larg, alt), (255, 255, 255))
    dr = ImageDraw.Draw(img)

    r = int(escala * 0.40)
    dx = int(espaco_x * 0.54)
    dy = int(espaco_y * 0.54)

    for li, linha in enumerate(linhas):
        y0 = margem + li * espaco_y
        for ci, bits in enumerate(linha):
            x0 = margem + ci * espaco_x
            for ponto in range(1, 7):
                if bits & (1 << (ponto - 1)):
                    col = 0 if ponto <= 3 else 1
                    linha_p = (ponto - 1) % 3
                    cx = x0 + col * dx
                    cy = y0 + linha_p * dy
                    dr.ellipse([cx - r + 2, cy - r + 3, cx + r + 2, cy + r + 3],
                               fill=(200, 204, 210))   # sombra
                    dr.ellipse([cx - r, cy - r, cx + r, cy + r],
                               fill=(28, 42, 74))      # ponto em relevo
    img.save(caminho)
    return caminho


# ============================================================
# MONTAGEM DO POWERPOINT
# ============================================================

AZUL = RGBColor(0x1C, 0x2A, 0x4A)
CINZA = RGBColor(0x55, 0x5D, 0x6D)
BRANCO = RGBColor(0xFF, 0xFF, 0xFF)


def imagem_centralizada(slide, prs, caminho, y_inch, larg_max, alt_max):
    """Insere a imagem centralizada horizontalmente, cabendo na area dada."""
    with Image.open(caminho) as im:
        w, h = im.size
    esc = min(larg_max / w, alt_max / h)
    larg, alt = w * esc, h * esc
    return slide.shapes.add_picture(
        caminho,
        int((prs.slide_width - larg) / 2),
        int(y_inch + (alt_max - alt) / 2),
        width=int(larg), height=int(alt),
    )


def construir():
    if not os.path.exists(PRINT_TELA):
        raise SystemExit("Print de tela nao encontrado: %s" % PRINT_TELA)

    COLUNAS = 36  # largura escolhida para o bloco de braille caber na area util
    render_braille_png(texto_para_celulas(TEXTO, COLUNAS), PNG_BRAILLE)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    vazio = prs.slide_layouts[6]

    # ---------------- SLIDE 1: print de tela ----------------
    s1 = prs.slides.add_slide(vazio)
    imagem_centralizada(s1, prs, PRINT_TELA, Inches(0.28),
                        Inches(12.4), Inches(5.85))

    barra = s1.shapes.add_shape(1, 0, int(Inches(6.42)),
                                prs.slide_width, int(Inches(1.08)))
    barra.fill.solid()
    barra.fill.fore_color.rgb = AZUL
    barra.line.fill.background()
    barra.shadow.inherit = False

    tf = barra.text_frame
    tf.word_wrap = True
    tf.margin_top = Inches(0.18)
    p = tf.paragraphs[0]
    p.text = "Inclusitec - Detector de Braille com IA"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = BRANCO
    p.alignment = PP_ALIGN.CENTER

    p2 = tf.add_paragraph()
    p2.text = "Servidor Flask + OpenCV em execucao em http://localhost:5000"
    p2.font.size = Pt(14)
    p2.font.color.rgb = RGBColor(0xC9, 0xD3, 0xE6)
    p2.alignment = PP_ALIGN.CENTER

    # ---------------- SLIDE 2: texto em braille ----------------
    s2 = prs.slides.add_slide(vazio)

    t = s2.shapes.add_textbox(Inches(0.7), Inches(0.38), Inches(11.9), Inches(0.65))
    p = t.text_frame.paragraphs[0]
    p.text = "O que \u00e9 o Inclusitec?"
    p.font.size = Pt(34)
    p.font.bold = True
    p.font.color.rgb = AZUL

    sub = s2.shapes.add_textbox(Inches(0.72), Inches(1.04), Inches(11.9), Inches(0.38))
    p = sub.text_frame.paragraphs[0]
    p.text = ("Texto em Braille \u2014 grafia oficial da l\u00edngua portuguesa "
              "(portaria 2.678/2002)")
    p.font.size = Pt(13)
    p.font.italic = True
    p.font.color.rgb = CINZA

    imagem_centralizada(s2, prs, PNG_BRAILLE, Inches(1.44),
                        Inches(11.9), Inches(3.80))

    # Versao em braille unicode como texto selecionavel / copiavel
    rotulo = s2.shapes.add_textbox(Inches(0.7), Inches(5.36), Inches(11.9), Inches(0.30))
    p = rotulo.text_frame.paragraphs[0]
    p.text = "Braille digital (texto unicode, copi\u00e1vel):"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = CINZA
    p.alignment = PP_ALIGN.CENTER

    rodape = s2.shapes.add_textbox(Inches(0.5), Inches(5.68), Inches(12.3), Inches(1.62))
    rodape.text_frame.word_wrap = True
    for i, linha in enumerate(linhas_unicode(COLUNAS)):
        p = (rodape.text_frame.paragraphs[0] if i == 0
             else rodape.text_frame.add_paragraph())
        p.text = linha
        p.font.size = Pt(10)
        p.font.color.rgb = CINZA
        p.alignment = PP_ALIGN.CENTER
        p.space_after = Pt(0)

    prs.save(ARQ_PPTX)
    print("OK -> PowerPoint salvo em:", ARQ_PPTX)
    print("    Slide 1 usa:", PRINT_TELA)
    print("    Slide 2 usa:", PNG_BRAILLE)


if __name__ == "__main__":
    construir()
