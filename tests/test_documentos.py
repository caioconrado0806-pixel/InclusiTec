"""
Testes da extração de texto de documentos (conversor Documento -> Braille).

Execução:
    python -m unittest tests.test_documentos
"""

import io
import os
import sys
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.documento_service import extrair_texto


def _zip(arquivos):
    """Monta um pacote ZIP em memória: {nome: conteúdo}."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as pacote:
        for nome, conteudo in arquivos.items():
            pacote.writestr(nome, conteudo)
    return buffer.getvalue()


class TestExtrairTexto(unittest.TestCase):

    def test_txt_utf8(self):
        texto, paginas = extrair_texto('nota.txt', 'Olá, coração!\r\nSegunda linha'.encode('utf-8'))
        self.assertEqual(texto, 'Olá, coração!\nSegunda linha')
        self.assertIsNone(paginas)

    def test_txt_windows_1252(self):
        texto, _ = extrair_texto('nota.txt', 'ação e pão'.encode('cp1252'))
        self.assertEqual(texto, 'ação e pão')

    def test_txt_utf16(self):
        texto, _ = extrair_texto('nota.txt', 'maçã'.encode('utf-16'))
        self.assertEqual(texto, 'maçã')

    def test_extensao_desconhecida_com_texto(self):
        texto, _ = extrair_texto('dados.qualquer', b'apenas texto')
        self.assertEqual(texto, 'apenas texto')

    def test_docx(self):
        ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
        documento = (
            f'<?xml version="1.0" encoding="UTF-8"?><w:document {ns}><w:body>'
            '<w:p><w:r><w:t>Título</w:t></w:r></w:p>'
            '<w:p><w:r><w:t xml:space="preserve">Olá </w:t></w:r><w:r><w:t>mundo</w:t><w:tab/><w:t>fim</w:t></w:r></w:p>'
            '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>célula</w:t></w:r></w:p></w:tc></w:tr></w:tbl>'
            '</w:body></w:document>'
        )
        texto, paginas = extrair_texto('a.docx', _zip({'word/document.xml': documento}))
        self.assertEqual(texto, 'Título\nOlá mundo\tfim\ncélula')
        self.assertIsNone(paginas)

    def test_odt(self):
        ns = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
              'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"')
        conteudo = (
            f'<office:document-content {ns}><office:body><office:text>'
            '<text:h>Título</text:h>'
            '<text:p>Olá<text:s text:c="2"/><text:span>mundo</text:span>!</text:p>'
            '</office:text></office:body></office:document-content>'
        )
        texto, _ = extrair_texto('a.odt', _zip({'mimetype': 'x', 'content.xml': conteudo}))
        self.assertEqual(texto, 'Título\nOlá  mundo!')

    def test_pptx_ordem_dos_slides(self):
        ns = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
        slide = lambda t: f'<sld {ns}><a:p><a:r><a:t>{t}</a:t></a:r></a:p></sld>'
        pacote = _zip({
            'ppt/presentation.xml': '<p/>',
            'ppt/slides/slide10.xml': slide('dez'),
            'ppt/slides/slide2.xml': slide('dois'),
            'ppt/slides/slide1.xml': slide('um'),
        })
        texto, paginas = extrair_texto('a.pptx', pacote)
        self.assertEqual(texto, 'um\n\ndois\n\ndez')
        self.assertEqual(paginas, 3)

    def test_xlsx(self):
        ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        pacote = _zip({
            'xl/workbook.xml': '<w/>',
            'xl/sharedStrings.xml': f'<sst {ns}><si><t>Nome</t></si><si><t>Ana</t></si></sst>',
            'xl/worksheets/sheet1.xml': (
                f'<worksheet {ns}><sheetData>'
                '<row><c t="s"><v>0</v></c><c><v>42</v></c></row>'
                '<row><c t="s"><v>1</v></c><c><v>7</v></c></row>'
                '</sheetData></worksheet>'
            ),
        })
        texto, paginas = extrair_texto('a.xlsx', pacote)
        self.assertEqual(texto, 'Nome\t42\nAna\t7')
        self.assertEqual(paginas, 1)

    def test_rtf(self):
        rtf = (r"{\rtf1\ansi\deff0{\fonttbl{\f0 Arial;}}{\*\generator X;}"
               r"\f0\fs24 Ol\'e1, cora\'e7\'e3o\par Segunda \b linha\b0  " + chr(92) + "u8212?fim}")
        texto, _ = extrair_texto('a.rtf', rtf.encode('ascii'))
        self.assertEqual(texto, 'Olá, coração\nSegunda linha —fim')

    def test_html(self):
        html = ('<html><head><title>T</title><style>p{color:red}</style></head>'
                '<body><h1>Título</h1><p>Olá &amp; <b>mundo</b></p><script>x=1</script></body></html>')
        texto, _ = extrair_texto('a.html', html.encode('utf-8'))
        self.assertEqual([l for l in texto.split('\n') if l], ['T', 'Título', 'Olá & mundo'])

    def test_doc_antigo_recusado(self):
        with self.assertRaises(ValueError) as erro:
            extrair_texto('a.doc', b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\x00' * 64)
        self.assertIn('.docx', str(erro.exception))

    def test_binario_recusado(self):
        with self.assertRaises(ValueError):
            extrair_texto('foto.png', b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR' + b'\x00' * 64)

    def test_zip_desconhecido_recusado(self):
        with self.assertRaises(ValueError):
            extrair_texto('a.zip', _zip({'qualquer.bin': 'x'}))

    def test_zip_corrompido_recusado(self):
        with self.assertRaises(ValueError):
            extrair_texto('a.docx', b'PK\x03\x04lixo')


if __name__ == '__main__':
    unittest.main()
