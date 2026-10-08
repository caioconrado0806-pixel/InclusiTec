"""
Conversão de texto em português brasileiro para Braille.

A partir de um mesmo texto esta fonte gera três representações:

- Unicode : caracteres Braille Unicode (⠿, ⠁ ...), usados na tela
            e no arquivo ``.brl`` (editável/visualizável).
- ASCII   : um caractere ASCII por célula, usado no arquivo ``.brf``,
            formato simples aceito por impressoras/embossers Braille
            (e legível também em impressora de papel).
- Células : lista de tuplas de 6 pontos, para reutilização por outros
            módulos do projeto.

Convenção dos pontos (idêntica ao resto do projeto):

    1 = superior-esquerdo    4 = superior-direito
    2 = médio-esquerdo       5 = médio-direito
    3 = inferior-esquerdo    6 = inferior-direito
"""

from backend.braille.mapping import (
    BRAILLE_NUMBERS,
    NUMBER_INDICATOR,
    PT_BR_TO_BRAILLE,
)

# Célula indicadora de maiúscula (⠠ = ponto 6).
CAPITAL_INDICATOR = (0, 0, 0, 0, 0, 1)

# Dígito -> padrão de pontos (tabela de números do mapping).
DIGIT_TO_PATTERN = {char: pattern for pattern, char in BRAILLE_NUMBERS.items()}

# Caractere ASCII usado para representar cada célula sem equivalente
# direto em ASCII (acentos do português). Todos são únicos e não
# colidem com letras, dígitos ou a pontuação básica.
CHAR_TO_ASCII = {
    'á': '(',   # pontos 1,2,3,5,6
    'à': '_',   # pontos 1,2,4,6
    'â': '^',   # pontos 1,6
    'ã': '~',   # pontos 3,4,5
    'é': '@',   # pontos 1,2,3,4,5,6
    'ê': '}',   # pontos 1,2,6
    'í': '*',   # pontos 3,4
    'ó': '%',   # pontos 3,4,6
    'ô': '&',   # pontos 1,4,5,6
    'õ': '<',   # pontos 2,4,6
    'ú': ')',   # pontos 2,3,4,5,6
    'ç': '#',   # pontos 1,2,3,4,6
}


def _cell_to_ascii_char(pattern):
    """Retorna o caractere ASCII que representa a célula informada."""
    source_char = PT_BR_TO_BRAILLE.get(pattern, '')
    if not source_char:
        return '?'
    if source_char in CHAR_TO_ASCII:
        return CHAR_TO_ASCII[source_char]
    if source_char.isascii():
        return source_char
    return '?'


class PortugueseToBraille:
    """Converte texto PT-BR para Braille (Unicode e ASCII)."""

    def __init__(self, wrap_width=40):
        """
        Args:
            wrap_width: quantidade de células por linha (40 = folha A4
                        na horizontal, padrão de impressoras Braille).
        """
        self.wrap_width = max(10, int(wrap_width))

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def to_unicode(self, text):
        """Texto -> representação Braille Unicode (⠿)."""
        return self._render(self._items(text), self._render_unicode)

    def to_ascii(self, text):
        """Texto -> representação ASCII (1 caractere por célula)."""
        return self._render(self._items(text), self._render_ascii)

    def to_cells(self, text):
        """Texto -> lista de tuplas de 6 pontos (células reais)."""
        cells = []
        for kind, value in self._items(text):
            if kind in ('cell', 'indicator'):
                cells.append(value)
        return cells

    # ------------------------------------------------------------------
    # Classificação caractere a caractere
    # ------------------------------------------------------------------
    def _items(self, text):
        """
        Percorre o texto e produz tuplas (tipo, valor) onde o tipo é:

        - 'cell'      -> padrão de pontos (tupla de 6)
        - 'indicator' -> célula indicadora (maiúscula / número)
        - 'raw'       -> caractere mantido como está (espaço, quebra,
                         caractere fora da tabela)
        """
        number_mode = False

        for char in text:
            # Quebras de linha e tabulação.
            if char in '\r':
                continue
            if char == '\n':
                number_mode = False
                yield ('raw', '\n')
                continue
            if char == '\t':
                number_mode = False
                yield ('raw', ' ')
                continue

            # Espaço: mantido como espaço (quebra de linha continua útil).
            if char == ' ':
                yield ('raw', ' ')
                continue

            # Dígitos: exibem a célula indicadora de número (⠼) uma vez
            # por sequência e depois o próprio dígito.
            if char in DIGIT_TO_PATTERN:
                if not number_mode:
                    number_mode = True
                    yield ('indicator', NUMBER_INDICATOR)
                yield ('cell', DIGIT_TO_PATTERN[char])
                continue

            number_mode = False

            key = char.lower()
            pattern = PT_BR_TO_BRAILLE.get(key)

            if pattern is None:
                # Fora da tabela (@, %, ...): mantém o caractere original.
                yield ('raw', char)
                continue

            if char.isupper() and char != key:
                yield ('indicator', CAPITAL_INDICATOR)

            yield ('cell', pattern)

    # ------------------------------------------------------------------
    # Renderização (com quebra de linha em self.wrap_width células)
    # ------------------------------------------------------------------
    @staticmethod
    def _render_unicode(kind, value):
        if kind == 'raw':
            return value
        code = 0x2800
        bits = {1: 0x01, 2: 0x02, 3: 0x04, 4: 0x08, 5: 0x10, 6: 0x20}
        for index, active in enumerate(value, start=1):
            if active:
                code += bits[index]
        return chr(code)

    @staticmethod
    def _render_ascii(kind, value):
        if kind == 'raw':
            # Mantém apenas ASCII imprimível (o arquivo é para impressora).
            return value if (value.isascii() and (value.isprintable() or value in '\n')) else '?'
        if kind == 'indicator':
            return ''  # no ASCII o caso/número já está no próprio caractere
        return _cell_to_ascii_char(value)

    def _render(self, items, renderer):
        """Renderiza os itens aplicando quebra de linha na largura útil."""
        output = []
        line_length = 0

        for kind, value in items:
            piece = renderer(kind, value)

            if piece == '\n':
                output.append('\n')
                line_length = 0
                continue

            if not piece:
                continue

            # Evita começar linha com espaço.
            if line_length == 0 and piece.isspace():
                continue

            if line_length + len(piece) > self.wrap_width:
                output.append('\n')
                line_length = 0
                if piece.isspace():
                    continue

            output.append(piece)
            line_length += len(piece)

        # Remove linhas em branco duplicadas no final.
        return ''.join(output).rstrip('\n') + '\n'
