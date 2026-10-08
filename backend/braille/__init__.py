"""
Pacote Braille: mapeamentos, detecção e conversão.

Fonte única da verdade — importe daqui em qualquer lugar
do projeto (API, cliente desktop, testes).
"""

from backend.braille.converter import BrailleToPortuguese
from backend.braille.detector import BrailleDetector, YOLOBrailleDetector, YOLO_AVAILABLE
from backend.braille.mapping import (
    BRAILLE_NUMBERS,
    BRAILLE_TO_PT_BR,
    NUMBER_INDICATOR,
    PT_BR_TO_BRAILLE,
)
from backend.braille.text_to_braille import PortugueseToBraille

__all__ = [
    'BrailleDetector',
    'BrailleToPortuguese',
    'PortugueseToBraille',
    'YOLOBrailleDetector',
    'YOLO_AVAILABLE',
    'BRAILLE_NUMBERS',
    'BRAILLE_TO_PT_BR',
    'PT_BR_TO_BRAILLE',
    'NUMBER_INDICATOR',
]
