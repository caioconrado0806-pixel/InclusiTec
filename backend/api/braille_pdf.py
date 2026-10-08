"""
Rotas de conversão PDF -> Braille e de impressão.

POST /api/braille/pdf
    Envia um PDF (multipart 'pdf') e recebe de volta o documento
    convertido em Braille, mais os arquivos gerados (.brf/.brl/.txt).

GET /api/braille/jobs/<job_id>/download/<fmt>
    Baixa o arquivo gerado (brf, brl ou txt).

GET /api/printers
    Lista as impressoras instaladas no computador.

POST /api/print
    Envia o arquivo Braille convertido para a impressora escolhida
    (impressora Braille/embosser ou impressora de papel comum).
"""

import io
import json
import os
import re
import uuid

from flask import Blueprint, jsonify, request, send_from_directory

import config
from backend.braille import PortugueseToBraille

bp = Blueprint('braille_pdf', __name__)

# Formatos aceitos no download.
FORMATOS = {
    'brf': ('.brf', 'ASCII Braille (arquivo para impressora Braille)'),
    'brl': ('.brl', 'Braille Unicode (⠿)'),
    'txt': ('.txt', 'Texto original extraído do PDF'),
}

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:  # pragma: no cover - dependência declarada no requirements
    PdfReader = None
    PYPDF_AVAILABLE = False


# ==================================================================
# Utilidades de PDF
# ==================================================================

def _ler_pdf(conteudo):
    """Extrai o texto de um PDF. Retorna (texto, nº de páginas)."""
    if not PYPDF_AVAILABLE:
        raise ValueError('Biblioteca pypdf não instalada. Execute: pip install pypdf')

    reader = PdfReader(io.BytesIO(conteudo))

    if reader.is_encrypted:
        try:
            reader.decrypt('')
        except Exception:
            raise ValueError('PDF protegido por senha. Remova a proteção e tente novamente.')

    paginas = []
    for page in reader.pages:
        try:
            paginas.append(page.extract_text() or '')
        except Exception:
            paginas.append('')

    texto = '\n\n'.join(paginas)
    texto = texto.replace('\r\n', '\n').replace('\r', '\n')

    # Remove sequências absurdas de linhas vazias.
    texto = re.sub(r'\n{4,}', '\n\n\n', texto)

    if len(texto) > config.MAX_PDF_TEXT_CHARS:
        texto = texto[:config.MAX_PDF_TEXT_CHARS] + '\n\n[texto truncado]'

    return texto, len(reader.pages)


# ==================================================================
# Armazenamento dos trabalhos convertidos
# ==================================================================

def _job_dir():
    os.makedirs(config.BRAILLE_JOBS_DIR, exist_ok=True)
    return config.BRAILLE_JOBS_DIR


def _caminho(job_id, extensao):
    return os.path.join(_job_dir(), f'{job_id}{extensao}')


def _carregar_job(job_id):
    """Lê o JSON do trabalho. Retorna dict ou None."""
    if not job_id or not re.fullmatch(r'[0-9a-f\-]{8,64}', str(job_id)):
        return None
    caminho = _caminho(job_id, '.json')
    if not os.path.isfile(caminho):
        return None
    try:
        with open(caminho, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# ==================================================================
# Impressoras do sistema
# ==================================================================

def _listar_impressoras():
    """
    Retorna (nomes, padrão, backend).

    Backend 'win32print' (pywin32) é o preferido no Windows; caso não
    exista, usa o .NET via PowerShell; se tudo falhar, lista vazia.
    """
    try:
        import win32print

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        try:
            entradas = win32print.EnumPrinters(flags)
        except Exception:
            entradas = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL)

        nomes = sorted({entrada[2] for entrada in entradas})
        padrao = win32print.GetDefaultPrinter()
        return nomes, padrao, 'win32print'
    except Exception:
        pass

    try:
        import subprocess

        comando = '[System.Drawing.Printing.PrinterSettings]::InstalledPrinters'
        saida = subprocess.run(
            ['powershell', '-NoProfile', '-Command', comando],
            capture_output=True, text=True, timeout=20,
        )
        nomes = sorted({linha.strip() for linha in saida.stdout.splitlines() if linha.strip()})
        return nomes, (nomes[0] if nomes else None), 'dotnet'
    except Exception:
        return [], None, 'nenhum'


def _imprimir_raw(nome_impressora, dados, titulo):
    """Envia bytes em bruto (RAW) para a impressora informada."""
    import win32print

    handle = win32print.OpenPrinter(
        nome_impressora,
        {'Desired Access': win32print.PRINTER_ACCESS_USE},
    )
    try:
        win32print.StartDocPrinter(handle, 1, (titulo, None, 'RAW'))
        try:
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, dados)
        finally:
            win32print.EndPagePrinter(handle)
        win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)


# ==================================================================
# Rotas
# ==================================================================

@bp.route('/api/braille/pdf', methods=['POST'])
def converter_pdf():
    """Converte um PDF em arquivo para impressora Braille."""
    try:
        if 'pdf' in request.files:
            arquivo = request.files['pdf']
            nome_original = arquivo.filename or 'documento.pdf'
            conteudo = arquivo.read()
        elif request.is_json:
            payload = request.get_json(silent=True) or {}
            import base64
            dados_b64 = payload.get('pdf_base64') or ''
            if ',' in dados_b64:
                dados_b64 = dados_b64.split(',', 1)[1]
            nome_original = payload.get('filename') or 'documento.pdf'
            conteudo = base64.b64decode(dados_b64)
        else:
            return jsonify({
                'success': False,
                'error': 'Nenhum PDF enviado. Use o campo "pdf" (multipart).'
            }), 400

        if not conteudo:
            return jsonify({'success': False, 'error': 'O arquivo está vazio.'}), 400

        if not nome_original.lower().endswith('.pdf') and not conteudo.startswith(b'%PDF'):
            return jsonify({
                'success': False,
                'error': 'O arquivo enviado não é um PDF válido.'
            }), 400

        if len(conteudo) > config.MAX_PDF_BYTES:
            return jsonify({
                'success': False,
                'error': f'PDF muito grande (máx. {config.MAX_PDF_BYTES // (1024 * 1024)} MB).'
            }), 413

        texto, paginas = _ler_pdf(conteudo)

        if not texto.strip():
            return jsonify({
                'success': False,
                'error': 'Não foi possível extrair texto do PDF. '
                         'Parece ser um PDF de imagens/escaneado — use OCR antes de converter.'
            }), 422

        conversor = PortugueseToBraille(wrap_width=config.BRAILLE_LINE_WIDTH)
        braille_unicode = conversor.to_unicode(texto)
        braille_ascii = conversor.to_ascii(texto)
        celulas = conversor.to_cells(texto)

        job_id = uuid.uuid4().hex
        base = os.path.splitext(os.path.basename(nome_original))[0] or 'documento'

        # Grava os três arquivos do trabalho.
        arquivos = {}
        for formato, extensao in (('brf', '.brf'), ('brl', '.brl'), ('txt', '.txt')):
            caminho = _caminho(job_id, extensao)
            conteudo_arquivo = {
                '.brf': braille_ascii,
                '.brl': braille_unicode,
                '.txt': texto,
            }[extensao]
            with open(caminho, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write(conteudo_arquivo)
            arquivos[formato] = {
                'nome': f'{base}{extensao}',
                'bytes': os.path.getsize(caminho),
                'url': f'/api/braille/jobs/{job_id}/download/{formato}',
            }

        job = {
            'id': job_id,
            'arquivo_original': nome_original,
            'base': base,
            'paginas': paginas,
            'caracteres': len(texto),
            'celulas': len(celulas),
            'linhas': braille_unicode.count('\n'),
            'largura': config.BRAILLE_LINE_WIDTH,
            'arquivos': arquivos,
        }
        with open(_caminho(job_id, '.json'), 'w', encoding='utf-8') as fh:
            json.dump(job, fh, ensure_ascii=False, indent=2)

        limite_preview = 12000
        return jsonify({
            'success': True,
            'job_id': job_id,
            'filename': nome_original,
            'paginas': paginas,
            'caracteres': len(texto),
            'celulas': len(celulas),
            'linhas': job['linhas'],
            'largura': config.BRAILLE_LINE_WIDTH,
            'braille_preview': braille_unicode[:limite_preview],
            'ascii_preview': braille_ascii[:limite_preview],
            'truncated': len(braille_unicode) > limite_preview,
            'arquivos': arquivos,
            'message': (
                f'"{nome_original}" convertido: {paginas} página(s), '
                f'{len(celulas)} células Braille.'
            ),
        })

    except ValueError as erro:
        return jsonify({'success': False, 'error': str(erro)}), 422
    except Exception as erro:  # noqa: BLE001 - retorna erro amigável
        return jsonify({
            'success': False,
            'error': f'Erro ao converter o PDF: {erro}'
        }), 500


@bp.route('/api/braille/jobs/<job_id>/download/<fmt>', methods=['GET'])
def baixar_job(job_id, fmt):
    """Baixa o arquivo gerado pela conversão."""
    fmt = (fmt or '').lower()
    if fmt not in FORMATOS:
        return jsonify({'success': False, 'error': 'Formato inválido (use brf, brl ou txt).'}), 400

    job = _carregar_job(job_id)
    if job is None:
        return jsonify({'success': False, 'error': 'Trabalho não encontrado. Converta o PDF novamente.'}), 404

    extensao = FORMATOS[fmt][0]
    nome = job['arquivos'].get(fmt, {}).get('nome') or f"{job.get('base', 'documento')}{extensao}"
    caminho = _caminho(job_id, extensao)

    if not os.path.isfile(caminho):
        return jsonify({'success': False, 'error': 'Arquivo não encontrado.'}), 404

    mimetype = 'text/plain; charset=utf-8'
    return send_from_directory(_job_dir(), os.path.basename(caminho),
                               as_attachment=True, download_name=nome,
                               mimetype=mimetype)


@bp.route('/api/printers', methods=['GET'])
def listar_impressoras():
    """Lista as impressoras disponíveis no computador."""
    nomes, padrao, backend = _listar_impressoras()
    return jsonify({
        'success': True,
        'printers': nomes,
        'default': padrao,
        'backend': backend,
        'message': (f'{len(nomes)} impressora(s) encontrada(s).'
                    if nomes else 'Nenhuma impressora detectada no sistema.'),
    })


@bp.route('/api/print', methods=['POST'])
def imprimir():
    """
    Envia o arquivo Braille para a impressora escolhida.

    JSON esperado:
        { "job_id": "...", "printer": "Nome da impressora", "format": "brf" }
    """
    payload = request.get_json(silent=True) or {}
    job_id = payload.get('job_id')
    formato = (payload.get('format') or 'brf').lower()
    nome_impressora = (payload.get('printer') or '').strip()

    if formato not in ('brf', 'brl', 'txt'):
        formato = 'brf'

    job = _carregar_job(job_id)
    if job is None:
        return jsonify({
            'success': False,
            'error': 'Arquivo convertido não encontrado. Converta o PDF novamente.',
        }), 404

    extensao = FORMATOS[formato][0]
    caminho = _caminho(job['id'], extensao)
    if not os.path.isfile(caminho):
        return jsonify({'success': False, 'error': 'Arquivo convertido não existe mais.'}), 404

    with open(caminho, 'rb') as fh:
        dados = fh.read()

    titulo = f"Inclusitec - {job.get('base', 'documento')}{extensao}"
    nomes, padrao, backend = _listar_impressoras()

    if nome_impressora:
        # Aceita o valor enviado pela interface (nome completo ou padrão).
        alvo = nome_impressora
    else:
        alvo = padrao

    # 1) Caminho preferido: envio direto via pywin32.
    if backend == 'win32print' and alvo:
        if nomes and alvo not in nomes and alvo != padrao:
            return jsonify({
                'success': False,
                'error': f'Impressora "{alvo}" não foi encontrada.',
                'printers': nomes,
            }), 400
        try:
            _imprimir_raw(alvo, dados, titulo)
            return jsonify({
                'success': True,
                'printer': alvo,
                'method': 'win32print',
                'bytes': len(dados),
                'format': formato,
                'message': f'Arquivo enviado para "{alvo}" com sucesso.',
            })
        except Exception as erro:  # noqa: BLE001
            return jsonify({
                'success': False,
                'error': f'Falha ao enviar para "{alvo}": {erro}',
                'printers': nomes,
            }), 500

    # 2) Fallback no Windows: entrega o arquivo ao sistema, que abre a
    #    janela de impressão com o aplicativo padrão.
    try:
        if not hasattr(os, 'startfile'):
            raise RuntimeError('Impressão via sistema não suportada nesta plataforma')
        os.startfile(caminho, 'print')  # noqa: S606 - Windows only
        return jsonify({
            'success': True,
            'printer': alvo or 'padrão do sistema',
            'method': 'shell',
            'bytes': len(dados),
            'format': formato,
            'message': 'Janela de impressão do sistema aberta. Escolha a impressora e clique em Imprimir.',
        })
    except Exception as erro:  # noqa: BLE001
        return jsonify({
            'success': False,
            'error': (
                'Não foi possível enviar para a impressora automaticamente '
                f'({erro}). Use "Imprimir pelo navegador" como alternativa.'
            ),
            'printers': nomes,
            'browser_print': True,
        }), 500
