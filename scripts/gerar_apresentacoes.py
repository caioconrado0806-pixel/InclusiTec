"""
Gera as apresentacoes do projeto Inclusitec.
1) PowerPoint7.pptx - print do sistema (slide 1) + folha braille (slide 2)
2) SegundaGuerraMundial.pptx - 10 slides sobre a 2a Guerra Mundial
Salvos na area de trabalho.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from PIL import Image

PROJETO = os.path.dirname(os.path.abspath(__file__))
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")

PRINT_APP = os.path.join(PROJETO, "print_inclusitec.png")
FOLHA_BRAILLE = os.path.join(PROJETO, "folha_braille_inclusitec.png")

AZUL = RGBColor(0x1F, 0x3B, 0x57)
CINZA = RGBColor(0x44, 0x4A, 0x53)


def novo_apresentacao():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs


def adicionar_titulo(slide, titulo, subtitulo=None):
    caixa = slide.shapes.title
    caixa.text = titulo
    paragrafo = caixa.text_frame.paragraphs[0]
    paragrafo.font.size = Pt(32)
    paragrafo.font.bold = True
    paragrafo.font.color.rgb = AZUL
    if subtitulo:
        linha = caixa.text_frame.add_paragraph()
        linha.text = subtitulo
        linha.font.size = Pt(16)
        linha.font.color.rgb = CINZA
    return caixa


def preencher_topicos(slide, topicos):
    caixa = slide.placeholders[1].text_frame
    caixa.word_wrap = True
    for i, item in enumerate(topicos):
        p = caixa.paragraphs[0] if i == 0 else caixa.add_paragraph()
        p.text = item
        p.level = 0
        p.font.size = Pt(20)


def centralizar_imagem(slide, caminho, topo=Inches(1.9), altura_max=Inches(5.0)):
    """Insere a imagem centralizada horizontalmente, mantendo proporcao."""
    with Image.open(caminho) as img:
        largura_px, altura_px = img.size
    largura_slide = slide.part.package.presentation_part.presentation.slide_width
    escala = min(altura_max / altura_px, (largura_slide - Inches(1.0)) / largura_px)
    largura = int(largura_px * escala)
    altura = int(altura_px * escala)
    esquerda = int((largura_slide - largura) / 2)
    return slide.shapes.add_picture(caminho, esquerda, topo, largura, altura)


# ============================================================
# 1) POWERPOINT7 - INCLUSITEC
# ============================================================

def gerar_inclusitec():
    prs = novo_apresentacao()

    slide = prs.slides.add_slide(prs.slide_layouts[0])
    adicionar_titulo(
        slide,
        "Inclusitec - Detector de Braille (Python + Flask + OpenCV)",
        "Print da tela com o servidor rodando em http://localhost:5000",
    )
    centralizar_imagem(slide, PRINT_APP, topo=Inches(2.0), altura_max=Inches(4.8))

    slide = prs.slides.add_slide(prs.slide_layouts[0])
    adicionar_titulo(
        slide,
        "Folha em Braille explicando o Inclusitec",
        "Texto em Braille traduzido pela inteligencia artificial do projeto",
    )
    centralizar_imagem(slide, FOLHA_BRAILLE, topo=Inches(1.7), altura_max=Inches(5.2))

    destino = os.path.join(DESKTOP, "PowerPoint7.pptx")
    prs.save(destino)
    print("Criado:", destino)
    return destino


# ============================================================
# 2) 10 SLIDES - 2a GUERRA MUNDIAL
# ============================================================

SLIDES_GM = [
    (
        "A 2a Guerra Mundial",
        "De 1939 a 1945 - o conflito mais destructivo da historia",
        [
            "Durou 6 anos (1939-1945) e atingiu quase todo o planeta.",
            "Conflito entre os Aliados e os paises do Eixo.",
            "Causou mais de 60 milhoes de mortos, incluindo civis.",
            "Deixou marcas em fronteiras, economias e instituicoes ate hoje.",
        ],
    ),
    (
        "Causas do conflito",
        "Tensoes acumuladas depois da 1a Guerra Mundial",
        [
            "Punicoes severas impostas a Alemanha pelo Tratado de Versalhes.",
            "Crise economica mundial de 1929, com desemprego em massa.",
            "Ascensao de regimes autoritarios na Alemanha, Italia e Japao.",
            "Revisao de fronteiras e disputas territoriais na Europa.",
        ],
    ),
    (
        "As potencias em 1939",
        "Dois blocos, ideologias opostas",
        [
            "Aliados: Reino Unido, Franca, URSS, EUA e China.",
            "Eixo: Alemanha, Italia e Japao.",
            "Ainda nao existia a Guerra Fria: era a era das ideologias totais.",
            "O Plano Marshall (1947) marcaria a reconstrucao pos-guerra.",
        ],
    ),
    (
        "Invasao da Polonia e inicio da guerra",
        "1 de setembro de 1939",
        [
            "Alemanha invade a Polonia usando a tecnica de blitzkrieg.",
            "Franca e Reino Unido declaram guerra em 3 de setembro de 1939.",
            "A URSS ocupa o leste da Polonia conforme os pactos com a Alemanha.",
            "Comecam os primeiros grandes combates terrestres.",
        ],
    ),
    (
        "Blitzkrieg: a guerra-relampago",
        "1940 - 1941",
        [
            "Avancos rapidos na Polonia, Dinamarca, Noruega, Belgica, Holandia e Franca.",
            "As tropas do Eixo evitam o combate frontal e cercam o inimigo.",
            "A blitzkrieg dominou a Europa ocidental em 1940 e 1941.",
            "Queda da Franca em junho de 1940 e Regime de Vichy.",
        ],
    ),
    (
        "A muralha do Atlantico",
        "1941 - 1943",
        [
            "Alemanha e U-boots atacam comboioses aliados no Oceano Atlantico.",
            "A ocupacao da Islanda pelos britanicos corta o eixo Atlantico.",
            "Batalhas navais, de superficie e submarinos marcaram o periodo.",
            "A derrota dos U-boots em 1943 abre caminho para o desembarque.",
        ],
    ),
    (
        "Stalingrado e Midway: viradas decisivas",
        "1942 - 1943",
        [
            "Stalingrado (URSS): o Exercito Vermelho cerca e vence o VI Corpo.",
            "Midway (Pacifico): 4 porta-avioes EUA afundam 4 japoneses.",
            "El Alamein: Montgomery derrota Rommel no Norte da Africa.",
            "A partir dai os Aliados avancam em todas as frentes.",
        ],
    ),
    (
        "O Holocausto",
        "1933 - 1945 - crime contra a humanidade",
        [
            "A Solucao Final planejava o exterminio dos 6 milhoes de judeus.",
            "Campos de concentracao: Auschwitz, Treblinka, Sobibor e outros.",
            "Pessoas com deficiencia, rom e outras minorias tambem foram perseguidas.",
            "Em 1945 os Aliados libertaram os campos e abriram os julgamentos de Nuremberg.",
        ],
    ),
    (
        "D-Day e a queda do Eixo",
        "6 de junho de 1944 - 1945",
        [
            "6 de junho de 1944: desembarque aliado na Normandia (Dia D).",
            "A operacao Overlord abre a frente ocidental contra a Alemanha.",
            "O avanco sovietico toma Berlim em abril de 1945.",
            "Hitler suicida-se em 30 de abril; Alemanha se rende em 8 de maio de 1945.",
            "Japão: bombas atomicas em Hiroshima e Nagasaki; rendicao em 2 de setembro de 1945.",
        ],
    ),
    (
        "Legado e memoria",
        "O que a guerra deixou para o mundo",
        [
            "A ONU (1945), criada para evitar novas guerras e proteger direitos.",
            "Declaracao Universal dos Direitos Humanos (1948).",
            "Processos de crimes de guerra e o conceito de crimes contra a humanidade.",
            "Dividiu o mundo em dois blocos na Guerra Fria.",
            "Paz e cooperacao internacional ficaram como principal heranca.",
        ],
    ),
]


def gerar_guerra_mundial():
    prs = novo_apresentacao()

    titulo, subtitulo, topicos = SLIDES_GM[0]
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    adicionar_titulo(slide, titulo, subtitulo)
    preencher_topicos(slide, topicos)

    for titulo, subtitulo, topicos in SLIDES_GM[1:]:
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        adicionar_titulo(slide, titulo, subtitulo)
        preencher_topicos(slide, topicos)

    destino = os.path.join(DESKTOP, "SegundaGuerraMundial.pptx")
    prs.save(destino)
    print("Criado:", destino)
    return destino


if __name__ == "__main__":
    gerar_inclusitec()
    gerar_guerra_mundial()