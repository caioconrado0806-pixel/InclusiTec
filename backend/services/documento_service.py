"""
Serviço de extração de texto de documentos.

Usado pelo conversor "Documento -> Braille" para os formatos que
não são PDF:

- Word (.docx), LibreOffice (.odt), PowerPoint (.pptx), Excel (.xlsx)
- Rich Text (.rtf), páginas HTML (.html/.htm)
- Texto puro (.txt, .md, .csv, .json, ... qualquer arquivo de texto)

Usa apenas a biblioteca padrão do Python (zipfile + XML), para
funcionar também em ambiente serverless.
"""

import io
import os
import re
import zipfile
from html.parser import HTMLParser
from xml.etree import ElementTree

import config

# Tamanho máximo (descompactado) de cada XML lido de dentro de um
# documento compactado (proteção contra "zip bomb").
MAX_XML_BYTES = 60 * 1024 * 1024

NS_WORD = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NS_DRAWING = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
NS_SHEET = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
NS_ODF_TEXT = '{urn:oasis:names:tc:opendocument:xmlns:text:1.0}'


# ==================================================================
# Utilidades
# ==================================================================

def _decodificar(conteudo):
    """Decodifica bytes de texto (UTF-8, UTF-16 ou Windows-1252)."""
    if conteudo.startswith(b'\xef\xbb\xbf'):
        return conteudo[3:].decode('utf-8', errors='replace')
    if conteudo.startswith((b'\xff\xfe', b'\xfe\xff')):
        return conteudo.decode('utf-16', errors='replace')
    try:
        return conteudo.decode('utf-8')
    except UnicodeDecodeError:
        return conteudo.decode('cp1252', errors='replace')


def _parece_texto(conteudo):
    """Heurística: arquivo de texto não tem bytes nulos nem de controle."""
    amostra = conteudo[:8192]
    if conteudo.startswith((b'\xff\xfe', b'\xfe\xff')):
        return True
    if b'\x00' in amostra:
        return False
    controle = sum(1 for b in amostra if b < 9 or 13 < b < 32)
    return controle <= len(amostra) * 0.02


def _xml_do_zip(pacote, nome):
    """Lê e interpreta um XML de dentro do documento compactado."""
    info = pacote.getinfo(nome)
    if info.file_size > MAX_XML_BYTES:
        raise ValueError('Documento grande demais para ser convertido.')
    dados = pacote.read(nome)
    if b'<!DOCTYPE' in dados[:4096] or b'<!ENTITY' in dados[:4096]:
        raise ValueError('Documento com estrutura XML não suportada.')
    return ElementTree.fromstring(dados)


def _numero(nome):
    """Número contido no nome do arquivo (slide12.xml -> 12)."""
    achado = re.search(r'(\d+)\.xml$', nome)
    return int(achado.group(1)) if achado else 0


# ==================================================================
# Leitores por formato
# ==================================================================

def _ler_docx(pacote):
    """Word (.docx): um parágrafo por linha, incluindo tabelas."""
    raiz = _xml_do_zip(pacote, 'word/document.xml')
    linhas = []
    for paragrafo in raiz.iter(f'{NS_WORD}p'):
        partes = []
        for no in paragrafo.iter():
            if no.tag == f'{NS_WORD}t':
                partes.append(no.text or '')
            elif no.tag == f'{NS_WORD}tab':
                partes.append('\t')
            elif no.tag in (f'{NS_WORD}br', f'{NS_WORD}cr'):
                partes.append('\n')
        linhas.append(''.join(partes))
    return '\n'.join(linhas), None


def _texto_odf(elemento):
    """Texto de um elemento ODF, respeitando espaços, tabs e quebras."""
    partes = [elemento.text or '']
    for filho in elemento:
        if filho.tag == f'{NS_ODF_TEXT}s':
            partes.append(' ' * int(filho.get(f'{NS_ODF_TEXT}c', '1')))
        elif filho.tag == f'{NS_ODF_TEXT}tab':
            partes.append('\t')
        elif filho.tag == f'{NS_ODF_TEXT}line-break':
            partes.append('\n')
        else:
            partes.append(_texto_odf(filho))
        partes.append(filho.tail or '')
    return ''.join(partes)


def _ler_odt(pacote):
    """LibreOffice/OpenDocument (.odt): parágrafos e títulos."""
    raiz = _xml_do_zip(pacote, 'content.xml')
    linhas = []

    def percorrer(elemento):
        if elemento.tag in (f'{NS_ODF_TEXT}p', f'{NS_ODF_TEXT}h'):
            linhas.append(_texto_odf(elemento))
            return
        for filho in elemento:
            percorrer(filho)

    percorrer(raiz)
    return '\n'.join(linhas), None


def _ler_pptx(pacote):
    """PowerPoint (.pptx): texto de cada slide, na ordem."""
    nomes = sorted(
        (n for n in pacote.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
        key=_numero,
    )
    slides = []
    for nome in nomes:
        raiz = _xml_do_zip(pacote, nome)
        linhas = []
        for paragrafo in raiz.iter(f'{NS_DRAWING}p'):
            partes = []
            for no in paragrafo.iter():
                if no.tag == f'{NS_DRAWING}t':
                    partes.append(no.text or '')
                elif no.tag == f'{NS_DRAWING}br':
                    partes.append('\n')
            linhas.append(''.join(partes))
        slides.append('\n'.join(linhas))
    return '\n\n'.join(slides), len(slides)


def _ler_xlsx(pacote):
    """Excel (.xlsx): células de cada linha separadas por tabulação."""
    compartilhados = []
    if 'xl/sharedStrings.xml' in pacote.namelist():
        raiz = _xml_do_zip(pacote, 'xl/sharedStrings.xml')
        for item in raiz.iter(f'{NS_SHEET}si'):
            compartilhados.append(''.join(t.text or '' for t in item.iter(f'{NS_SHEET}t')))

    nomes = sorted(
        (n for n in pacote.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', n)),
        key=_numero,
    )
    planilhas = []
    for nome in nomes:
        raiz = _xml_do_zip(pacote, nome)
        linhas = []
        for linha in raiz.iter(f'{NS_SHEET}row'):
            valores = []
            for celula in linha.iter(f'{NS_SHEET}c'):
                valor = celula.find(f'{NS_SHEET}v')
                if celula.get('t') == 's' and valor is not None and valor.text:
                    indice = int(valor.text)
                    valores.append(compartilhados[indice] if indice < len(compartilhados) else '')
                elif celula.get('t') == 'inlineStr':
                    valores.append(''.join(t.text or '' for t in celula.iter(f'{NS_SHEET}t')))
                else:
                    valores.append(valor.text if valor is not None and valor.text else '')
            if any(valores):
                linhas.append('\t'.join(valores))
        planilhas.append('\n'.join(linhas))
    return '\n\n'.join(planilhas), len(planilhas)


# Grupos do RTF que não contêm texto do documento.
_RTF_IGNORAR = {
    'fonttbl', 'colortbl', 'stylesheet', 'info', 'pict', 'object', 'header',
    'footer', 'headerl', 'headerr', 'footerl', 'footerr', 'themedata',
    'datastore', 'colorschememapping', 'latentstyles', 'generator',
    'listtable', 'listoverridetable', 'rsidtbl', 'xmlnstbl', 'fldinst',
}
_RTF_ESPECIAIS = {
    'par': '\n', 'sect': '\n\n', 'page': '\n\n', 'line': '\n', 'tab': '\t',
    'emdash': '—', 'endash': '–', 'emspace': ' ', 'enspace': ' ',
    'lquote': '‘', 'rquote': '’', 'ldblquote': '“', 'rdblquote': '”',
    'bullet': '•', 'cell': '\t', 'row': '\n',
}
_RTF_TOKEN = re.compile(
    r"\\([a-z]{1,32})(-?\d{1,10})?[ ]?|\\'([0-9a-f]{2})|\\([^a-z])|([{}])|[\r\n]+|(.)",
    re.IGNORECASE | re.DOTALL,
)


def _ler_rtf(conteudo):
    """Rich Text (.rtf): remove os comandos e mantém o texto."""
    fonte = conteudo.decode('latin-1')
    pilha = []          # (ignorando, saltos unicode) de cada grupo aberto
    ignorando = False
    saltos_unicode = 1  # caracteres a pular depois de um \uN
    pular = 0
    saida = []

    for achado in _RTF_TOKEN.finditer(fonte):
        palavra, argumento, hexa, simbolo, chave, caractere = achado.groups()
        if chave == '{':
            pilha.append((ignorando, saltos_unicode))
        elif chave == '}':
            if pilha:
                ignorando, saltos_unicode = pilha.pop()
        elif simbolo:
            pular = 0
            if simbolo == '*':
                ignorando = True
            elif not ignorando:
                if simbolo == '~':
                    saida.append(' ')
                elif simbolo in '{}\\':
                    saida.append(simbolo)
        elif palavra:
            pular = 0
            if palavra in _RTF_IGNORAR:
                ignorando = True
            elif ignorando:
                pass
            elif palavra in _RTF_ESPECIAIS:
                saida.append(_RTF_ESPECIAIS[palavra])
            elif palavra == 'uc':
                saltos_unicode = int(argumento or 1)
            elif palavra == 'u' and argumento:
                codigo = int(argumento)
                if codigo < 0:
                    codigo += 0x10000
                saida.append(chr(codigo))
                pular = saltos_unicode
        elif hexa:
            if pular > 0:
                pular -= 1
            elif not ignorando:
                saida.append(bytes([int(hexa, 16)]).decode('cp1252', errors='replace'))
        elif caractere:
            if pular > 0:
                pular -= 1
            elif not ignorando:
                saida.append(caractere)

    return ''.join(saida), None


class _ExtratorHTML(HTMLParser):
    """Extrai o texto visível de uma página HTML."""

    BLOCOS = {'p', 'div', 'br', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
              'section', 'article', 'header', 'footer', 'table', 'ul', 'ol',
              'blockquote', 'pre', 'title'}
    OCULTOS = {'script', 'style', 'noscript', 'template'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.oculto = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.OCULTOS:
            self.oculto += 1
        elif tag in self.BLOCOS:
            self.partes.append('\n')

    def handle_endtag(self, tag):
        if tag in self.OCULTOS:
            self.oculto = max(0, self.oculto - 1)
        elif tag in self.BLOCOS:
            self.partes.append('\n')

    def handle_data(self, data):
        if not self.oculto:
            self.partes.append(re.sub(r'\s+', ' ', data))


def _ler_html(conteudo):
    """Página HTML: apenas o texto visível."""
    extrator = _ExtratorHTML()
    extrator.feed(_decodificar(conteudo))
    extrator.close()
    linhas = (linha.strip() for linha in ''.join(extrator.partes).split('\n'))
    return '\n'.join(linhas), None


def _ler_compactado(conteudo):
    """Documentos em pacote ZIP: docx, odt, pptx e xlsx."""
    try:
        pacote = zipfile.ZipFile(io.BytesIO(conteudo))
    except zipfile.BadZipFile:
        raise ValueError('Documento corrompido ou em formato não suportado.')

    with pacote:
        nomes = set(pacote.namelist())
        if 'word/document.xml' in nomes:
            return _ler_docx(pacote)
        if 'ppt/presentation.xml' in nomes:
            return _ler_pptx(pacote)
        if 'xl/workbook.xml' in nomes:
            return _ler_xlsx(pacote)
        if 'content.xml' in nomes:
            return _ler_odt(pacote)

    raise ValueError('Tipo de documento não suportado.')


# ==================================================================
# API do serviço
# ==================================================================

def extrair_texto(nome, conteudo):
    """
    Extrai o texto de um documento que não é PDF.

    Returns:
        (texto, páginas) — páginas é None quando o formato não tem
        paginação fixa (Word, texto puro, etc.).

    Raises:
        ValueError: formato não suportado ou arquivo corrompido.
    """
    extensao = os.path.splitext(nome or '')[1].lower()

    try:
        if conteudo.startswith(b'PK\x03\x04'):
            texto, paginas = _ler_compactado(conteudo)
        elif conteudo.startswith(b'\xd0\xcf\x11\xe0'):
            raise ValueError(
                'Arquivos antigos do Office (.doc, .xls, .ppt) não são suportados. '
                'Salve como .docx ou PDF e tente novamente.'
            )
        elif conteudo.lstrip()[:5] == b'{\\rtf':
            texto, paginas = _ler_rtf(conteudo)
        elif not _parece_texto(conteudo):
            raise ValueError(
                f'Tipo de arquivo não suportado ({extensao or "sem extensão"}). '
                'Envie PDF, Word (.docx), .odt, .rtf, .pptx, .xlsx, HTML ou texto.'
            )
        elif extensao in ('.html', '.htm', '.xhtml'):
            texto, paginas = _ler_html(conteudo)
        else:
            texto, paginas = _decodificar(conteudo), None
    except (ElementTree.ParseError, KeyError, zipfile.BadZipFile):
        raise ValueError('Documento corrompido ou em formato não suportado.')

    texto = texto.replace('\r\n', '\n').replace('\r', '\n')
    texto = re.sub(r'\n{4,}', '\n\n\n', texto)

    if len(texto) > config.MAX_PDF_TEXT_CHARS:
        texto = texto[:config.MAX_PDF_TEXT_CHARS] + '\n\n[texto truncado]'

    return texto, paginas
