"""
Gera uma apresentacao de 6 slides (tudo em INGLES) sobre os EUA:
nome do pais, moeda, localizacao no mapa, cultura, vestimentas
tipicas, danca, musica, festas populares, curiosidades e
gastronomia (prato: hot dog, local: Nova York).

Contem 3 imagens (mapa, hot dog, skyline de Nova York) e o
restante e composto por topicos (bullets) e texto corrido.
"""

import os

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from PIL import Image

# ============================================================
# CONFIGURACOES
# ============================================================

RAIZ = os.path.dirname(os.path.abspath(__file__))
IMG_MAP = os.path.join(RAIZ, "img_usa_map.png")
IMG_HOTDOG = os.path.join(RAIZ, "img_hotdog.jpg")
IMG_SKYLINE = os.path.join(RAIZ, "img_nyc_skyline.jpg")
ARQ_PPTX = os.path.join(RAIZ, "USA_Culture_Gastronomy.pptx")

# Paleta (bandeira dos EUA + azul marinho)
NAVY = RGBColor(0x1C, 0x2A, 0x4A)
RED = RGBColor(0xB2, 0x22, 0x34)
BLUE = RGBColor(0x3C, 0x3B, 0x6E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x55, 0x5D, 0x6D)
LIGHT = RGBColor(0xEE, 0xF1, 0xF6)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


# ============================================================
# AJUDANTES
# ============================================================

def imagem_na_caixa(slide, caminho, x, y, larg, alt):
    """Insere a imagem centralizada dentro da caixa (x, y, larg, alt)."""
    with Image.open(caminho) as im:
        w, h = im.size
    esc = min(larg / w, alt / h)
    w2, h2 = int(w * esc), int(h * esc)
    return slide.shapes.add_picture(
        caminho, int(x + (larg - w2) / 2), int(y + (alt - h2) / 2),
        width=w2, height=h2,
    )


def barra_titulo(slide, titulo, subtitulo=None):
    """Faixa superior com o titulo do slide."""
    barra = slide.shapes.add_shape(1, 0, 0, SLIDE_W, Inches(0.95))
    barra.fill.solid()
    barra.fill.fore_color.rgb = NAVY
    barra.line.fill.background()
    barra.shadow.inherit = False

    tf = barra.text_frame
    tf.word_wrap = True
    tf.margin_top = Inches(0.08)
    tf.margin_bottom = Inches(0.04)
    p = tf.paragraphs[0]
    p.text = titulo
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.LEFT
    if subtitulo:
        p2 = tf.add_paragraph()
        p2.text = subtitulo
        p2.font.size = Pt(13)
        p2.font.italic = True
        p2.font.color.rgb = RGBColor(0xC9, 0xD3, 0xE6)
    return barra


def caixa_topicos(slide, x, y, larg, alt, titulo, itens):
    """Caixa de topicos (bullets). 'itens' = lista de str ou (negrito, resto)."""
    if titulo:
        tb = slide.shapes.add_textbox(x, y, larg, Inches(0.42))
        p = tb.text_frame.paragraphs[0]
        p.text = titulo
        p.font.size = Pt(17)
        p.font.bold = True
        p.font.color.rgb = RED

    corpo = slide.shapes.add_textbox(x, y + (Inches(0.45) if titulo else 0),
                                     larg, alt - (Inches(0.45) if titulo else 0))
    tf = corpo.text_frame
    tf.word_wrap = True
    for i, item in enumerate(itens):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(7)
        p.level = 0
        if isinstance(item, tuple):
            r1 = p.add_run()
            r1.text = "\u25aa " + item[0]
            r1.font.bold = True
            r1.font.size = Pt(15)
            r1.font.color.rgb = NAVY
            r2 = p.add_run()
            r2.text = item[1]
            r2.font.size = Pt(15)
            r2.font.color.rgb = RGBColor(0x22, 0x28, 0x33)
        else:
            r = p.add_run()
            r.text = "\u25aa " + item
            r.font.size = Pt(15)
            r.font.color.rgb = RGBColor(0x22, 0x28, 0x33)
    return corpo


def texto_corrido(slide, x, y, larg, alt, texto, tamanho=13):
    """Bloco de texto corrido (paragrafo)."""
    tb = slide.shapes.add_textbox(x, y, larg, alt)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = texto
    p.font.size = Pt(tamanho)
    p.font.color.rgb = RGBColor(0x2A, 0x30, 0x3C)
    p.line_spacing = 1.15
    return tb


def rodape(slide, texto):
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(7.08), Inches(12.3), Inches(0.32))
    p = tb.text_frame.paragraphs[0]
    p.text = texto
    p.font.size = Pt(9)
    p.font.italic = True
    p.font.color.rgb = GRAY
    p.alignment = PP_ALIGN.CENTER


# ============================================================
# MONTAGEM DOS 6 SLIDES
# ============================================================

def construir():
    for caminho in (IMG_MAP, IMG_HOTDOG, IMG_SKYLINE):
        if not os.path.exists(caminho):
            raise SystemExit("Imagem nao encontrada: %s" % caminho)

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    vazio = prs.slide_layouts[6]

    # ---------------- SLIDE 1: nome do pais, moeda e mapa ----------------
    s1 = prs.slides.add_slide(vazio)

    t = s1.shapes.add_textbox(Inches(0.6), Inches(0.35), Inches(12.1), Inches(1.0))
    p = t.text_frame.paragraphs[0]
    p.text = "The United States of America (USA)"
    p.font.size = Pt(40)
    p.font.bold = True
    p.font.color.rgb = NAVY
    p.alignment = PP_ALIGN.CENTER

    sub = s1.shapes.add_textbox(Inches(0.6), Inches(1.30), Inches(12.1), Inches(0.4))
    p = sub.text_frame.paragraphs[0]
    p.text = "Country overview: name, currency and location on the map"
    p.font.size = Pt(15)
    p.font.italic = True
    p.font.color.rgb = RED
    p.alignment = PP_ALIGN.CENTER

    # Imagem: mapa com a localizacao dos EUA na America do Norte
    imagem_na_caixa(s1, IMG_MAP, Inches(0.55), Inches(1.85), Inches(6.0), Inches(4.6))

    caixa_topicos(
        s1, Inches(6.95), Inches(1.90), Inches(5.85), Inches(4.55),
        "Key facts",
        [
            ("Country name: ", "United States of America (USA / U.S.)"),
            ("Capital: ", "Washington, D.C."),
            ("Currency: ", "United States Dollar (USD, symbol $)"),
            ("Location: ", "North America, between Canada (north) and Mexico (south)"),
            ("Language: ", "English (de facto national language)"),
            ("States: ", "50 states and several territories"),
        ],
    )

    texto_corrido(
        s1, Inches(0.55), Inches(6.42), Inches(12.25), Inches(0.65),
        "The United States is a federal republic located in North America. "
        "Its official currency is the dollar (USD), one of the most traded "
        "currencies in the world, and the country stretches from the Atlantic "
        "Ocean to the Pacific Ocean.",
        tamanho=12,
    )

    # ---------------- SLIDE 2: cultura e vestimentas tipicas ----------------
    s2 = prs.slides.add_slide(vazio)
    barra_titulo(s2, "Culture and Typical Clothing",
                 "A melting pot of traditions, fashion and everyday style")

    caixa_topicos(
        s2, Inches(0.55), Inches(1.20), Inches(6.1), Inches(5.3),
        "Culture",
        [
            ("Melting pot: ", "cultures from immigrants all over the world"),
            ("Global influence: ", "Hollywood movies, TV series and music"),
            ("Sports culture: ", "baseball, basketball and American football"),
            ("Values: ", "freedom, individualism and entrepreneurship"),
            ("Landmarks: ", "Statue of Liberty, Golden Gate Bridge, Grand Canyon"),
        ],
    )

    caixa_topicos(
        s2, Inches(6.95), Inches(1.20), Inches(5.85), Inches(5.3),
        "Typical clothing",
        [
            ("Everyday style: ", "jeans, T-shirts, sneakers and baseball caps"),
            ("Cowboy culture: ", "wide-brim hats, boots and denim in the West"),
            ("Native American: ", "colorful regalia worn at ceremonies and powwows"),
            ("Workwear: ", "denim jackets, flannel shirts and work boots"),
            ("Note: ", "there is no single national costume \u2014 style is regional and casual"),
        ],
    )

    texto_corrido(
        s2, Inches(0.55), Inches(6.30), Inches(12.25), Inches(0.75),
        "American culture is one of the most influential in the world, blending "
        "Indigenous, European, African, Latin American and Asian traditions. "
        "Because of this diversity, typical clothing is mostly casual and regional: "
        "jeans and sneakers are iconic nationwide, while cowboy hats and boots "
        "represent the ranching heritage of the West.",
        tamanho=12,
    )

    # ---------------- SLIDE 3: gastronomia - o hot dog de Nova York ----------------
    s3 = prs.slides.add_slide(vazio)
    barra_titulo(s3, "Gastronomy \u2014 The Hot Dog",
                 "Dish: Hot Dog \u2022 Local: New York City, NY")

    caixa_topicos(
        s3, Inches(0.55), Inches(1.20), Inches(6.4), Inches(3.1),
        "The dish",
        [
            ("Name: ", "Hot Dog (frankfurter / wiener served in a bun)"),
            ("Local: ", "New York \u2014 street carts and Nathan's Famous, Coney Island"),
            ("Since: ", "popular in NYC since the late 19th century"),
        ],
    )

    caixa_topicos(
        s3, Inches(0.55), Inches(3.85), Inches(6.4), Inches(2.4),
        "Utensils used to prepare and serve",
        [
            "Grill or hot dog roller grill",
            "Tongs and a long fork (to turn the sausages)",
            "Knife and cutting board (to slice toppings)",
            "Serving tray, buns, napkins and condiment squeeze bottles",
        ],
    )

    caixa_topicos(
        s3, Inches(7.25), Inches(1.20), Inches(5.55), Inches(3.1),
        "Ingredients",
        [
            "Beef and/or pork sausage (frankfurter)",
            "Soft sliced bun (bread roll)",
            "Yellow mustard and ketchup",
            "Chopped onions and relish",
            "Sauerkraut and pickles (optional)",
        ],
    )

    # Imagem: hot dog
    imagem_na_caixa(s3, IMG_HOTDOG, Inches(7.25), Inches(4.35), Inches(5.55), Inches(2.6))

    texto_corrido(
        s3, Inches(0.55), Inches(6.42), Inches(6.4), Inches(0.65),
        "The hot dog is a fast-food icon of New York City, sold from carts on "
        "almost every corner. It is quick, cheap and delicious \u2014 a true "
        "symbol of American street food.",
        tamanho=12,
    )

    rodape(s3, "Photo: Hot dog with mustard \u2014 Wikimedia Commons (CC BY-SA 2.0)")

    # ---------------- SLIDE 4: danca e musica ----------------
    s4 = prs.slides.add_slide(vazio)
    barra_titulo(s4, "Dance and Music",
                 "From jazz and blues to hip-hop \u2014 rhythm was born in the USA")

    caixa_topicos(
        s4, Inches(0.55), Inches(1.20), Inches(6.1), Inches(5.0),
        "Music",
        [
            ("Jazz and blues: ", "born in New Orleans in the early 1900s"),
            ("Rock 'n' roll: ", "1950s, with Elvis Presley and Chuck Berry"),
            ("Hip-hop: ", "born in the Bronx, New York City, in the 1970s"),
            ("Country: ", "from the rural South and Nashville"),
            ("Pop: ", "global hits by Michael Jackson, Madonna and Beyonc\u00e9"),
        ],
    )

    caixa_topicos(
        s4, Inches(6.95), Inches(1.20), Inches(5.85), Inches(5.0),
        "Dance",
        [
            ("Swing / Lindy Hop: ", "energetic partner dance of the jazz era"),
            ("Hip-hop dance: ", "breakdance, popping and locking"),
            ("Broadway: ", "choreographed musical theatre in New York"),
            ("Square dance: ", "traditional folk dance of the country west"),
            ("Tap dance: ", "percussive shoes, a classic American art form"),
        ],
    )

    texto_corrido(
        s4, Inches(0.55), Inches(6.30), Inches(12.25), Inches(0.75),
        "The United States gave the world some of the most popular music genres "
        "in history. Jazz, blues, rock, country and hip-hop all started on "
        "American soil, and dances like swing, tap and breakdance spread around "
        "the globe. New York City remains the capital of Broadway, hip-hop and "
        "musical innovation.",
        tamanho=12,
    )

    # ---------------- SLIDE 5: festas populares (com skyline de NY) ----------------
    s5 = prs.slides.add_slide(vazio)
    barra_titulo(s5, "Popular Parties and Festivities",
                 "Celebrations that bring the whole country together")

    caixa_topicos(
        s5, Inches(0.55), Inches(1.20), Inches(6.6), Inches(5.6),
        "Most popular parties",
        [
            ("Independence Day (July 4): ", "fireworks, parades and barbecues"),
            ("Thanksgiving (November): ", "family dinner with turkey and pumpkin pie"),
            ("Halloween (October 31): ", "costumes, candy and trick-or-treat"),
            ("New Year's Eve: ", "the famous ball drop in Times Square, NYC"),
            ("Super Bowl Sunday: ", "big game, snacks and parties at home"),
            ("Mardi Gras: ", "colorful parades and carnival in New Orleans"),
        ],
    )

    # Imagem: skyline de Manhattan
    imagem_na_caixa(s5, IMG_SKYLINE, Inches(7.35), Inches(1.35), Inches(5.45), Inches(3.0))

    texto_corrido(
        s5, Inches(7.35), Inches(4.55), Inches(5.45), Inches(2.4),
        "New York City is the stage for some of the biggest celebrations in the "
        "country. On New Year's Eve, over a million people gather in Times Square "
        "to watch the crystal ball drop at midnight, while the Macy's Thanksgiving "
        "Day Parade fills the streets with giant balloons and floats every November.",
        tamanho=12,
    )

    rodape(s5, "Photo: Manhattan skyline at night \u2014 Wikimedia Commons (CC BY-SA 2.0)")

    # ---------------- SLIDE 6: curiosidades e resumo ----------------
    s6 = prs.slides.add_slide(vazio)
    barra_titulo(s6, "Curiosities and Wrap-Up",
                 "Fun facts about the United States")

    caixa_topicos(
        s6, Inches(0.55), Inches(1.20), Inches(12.25), Inches(3.4),
        "Did you know?",
        [
            ("The Statue of Liberty ", "was a gift from France in 1886 and stands in New York Harbor."),
            ("The flag ", "has 50 stars (one for each state) and 13 stripes (the original colonies)."),
            ("The hot dog ", "was made famous by street vendors in New York City over 100 years ago."),
            ("There is no official language ", "at the federal level, but English is spoken by the vast majority."),
            ("The U.S. is the 3rd largest country ", "in the world by area and population."),
        ],
    )

    texto_corrido(
        s6, Inches(0.55), Inches(4.85), Inches(12.25), Inches(1.9),
        "To wrap up: the United States of America is a vast country in North "
        "America whose currency is the United States Dollar. Its culture is a mix "
        "of peoples from all over the world, reflected in casual clothing such as "
        "jeans, in musical genres like jazz, rock and hip-hop, and in dances such "
        "as swing and breakdance. Popular parties range from Independence Day and "
        "Thanksgiving to Halloween and the Times Square New Year's Eve ball drop. "
        "And when it comes to gastronomy, nothing is more New York than a hot dog "
        "from a street cart \u2014 a beef frankfurter in a soft bun with mustard, "
        "onions and relish, prepared on the grill and served on a tray.",
        tamanho=13,
    )

    rodape(s6, "Images: Wikimedia Commons \u2014 North America relief map (CC BY-SA 4.0), hot dog (CC BY-SA 2.0), Manhattan skyline (CC BY-SA 2.0)")

    prs.save(ARQ_PPTX)
    print("OK -> PowerPoint salvo em:", ARQ_PPTX)
    print("Slides:", len(prs.slides.__iter__.__self__._sldIdLst), "| Imagens:", 3)


if __name__ == "__main__":
    construir()
