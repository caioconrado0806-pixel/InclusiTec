"""
Conversão de células Braille para texto em português brasileiro.
"""

from backend.braille.mapping import (
    BRAILLE_NUMBERS,
    BRAILLE_TO_PT_BR,
    NUMBER_INDICATOR,
)


class BrailleToPortuguese:
    """Converte uma sequência de células Braille para texto em PT-BR."""

    def __init__(self):
        self.number_mode = False

    def reset(self):
        """Desativa o modo de numeração."""
        self.number_mode = False

    def convert_cells(self, cells):
        """
        Converte uma lista de células Braille para texto.

        Args:
            cells: lista de tuplas de 6 valores binários.

        Returns:
            Texto em português brasileiro.
        """
        self.reset()
        return ''.join(self._convert_single_cell(cell) for cell in cells)

    def _convert_single_cell(self, cell):
        """Converte uma única célula Braille para caractere."""
        # Indicador de número: ativa o modo e não emite caractere.
        if cell == NUMBER_INDICATOR:
            self.number_mode = True
            return ''

        # Em modo número, converte como dígito enquanto for possível.
        if self.number_mode:
            if cell in BRAILLE_NUMBERS:
                return BRAILLE_NUMBERS[cell]
            self.number_mode = False  # sai do modo ao encontrar não-dígito

        if cell in BRAILLE_TO_PT_BR:
            return BRAILLE_TO_PT_BR[cell]

        return '?'  # célula desconhecida
