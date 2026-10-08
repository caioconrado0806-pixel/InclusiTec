"""
Inclusitec - Cliente Desktop (frontend em Python)
====================================================
Interface gráfica (Tkinter) que consome a API do servidor
Inclusitec. Funciona como frontend alternativo ao navegador,
com saída de voz (pyttsx3) e captura de câmera (OpenCV).

Uso:
    1. Inicie o servidor:  python app.py
    2. Inicie este cliente: python desktop/client.py

Recursos:
- Carregar imagem de arquivo -> detecta Braille -> fala o texto
- Capturar da câmera -> detecta Braille -> fala o texto
- Digitar texto -> mostra a representação Braille -> fala a letra
"""

import base64
import io
import tkinter as tk
from tkinter import filedialog, messagebox

import requests

import config
from backend.braille import PT_BR_TO_BRAILLE

# -------------------------------------------------------------
# Utilidades
# -------------------------------------------------------------

API_BASE = f'http://localhost:{config.PORT}'

# Converte um padrão de pontos (ex.: (1,0,0,1,0,0)) no caractere
# Braille Unicode correspondente.
_DOT_BITS = {1: 0x01, 2: 0x02, 3: 0x04, 4: 0x08, 5: 0x10, 6: 0x20}


def padrao_para_unicode(pontos):
    codigo = 0x2800
    for i, ativo in enumerate(pontos, start=1):
        if ativo:
            codigo += _DOT_BITS[i]
    return chr(codigo)


def texto_para_braille(texto):
    """Traduz texto para Braille usando a tabela do backend."""
    resultado = []
    for char in texto.lower():
        padrao = PT_BR_TO_BRAILLE.get(char)
        resultado.append(padrao_para_unicode(padrao) if padrao else char)
    return ''.join(resultado)


class InclusitecDesktop:
    """Interface gráfica do Inclusitec."""

    def __init__(self, root):
        self.root = root
        root.title('Inclusitec - Leitor de Braille')
        root.geometry('520x560')
        root.configure(bg='#030814')

        estilo = {
            'bg': '#030814', 'fg': '#00f3ff',
            'font': ('Segoe UI', 11),
        }
        estilo_btn = {**estilo, 'width': 40, 'bg': '#002244', 'relief': 'raised'}

        tk.Label(root, text='INCLUSITEC', font=('Segoe UI', 20, 'bold'),
                 **estilo).pack(pady=(15, 5))
        tk.Label(root, text='Leitor de Braille - Frontend Python',
                 **estilo).pack()

        # -------------------- Leitura de imagem --------------------
        tk.Button(root, text='📷  Capturar da Câmera',
                  command=self.capturar_camera, **estilo_btn).pack(pady=5)
        tk.Button(root, text='📁  Carregar Imagem',
                  command=self.carregar_imagem, **estilo_btn).pack(pady=5)

        self.status = tk.StringVar(value='Pronto. Conectado ao servidor?')
        tk.Label(root, textvariable=self.status, wraplength=460,
                 **estilo).pack(pady=5)

        self.resultado = tk.StringVar(value='Texto traduzido: —')
        tk.Label(root, textvariable=self.resultado, wraplength=460,
                 font=('Segoe UI', 13, 'bold'), **estilo).pack(pady=5)

        tk.Button(root, text='🔊  Ouvir Tradução',
                  command=self.ouvir, **estilo_btn).pack(pady=5)

        # -------------------- Texto -> Braille --------------------
        tk.Label(root, text='Digite para traduzir em Braille:',
                 **estilo).pack(pady=(15, 0))
        self.entrada = tk.Entry(root, width=42, font=('Segoe UI', 12),
                                bg='#001122', fg='#00f3ff',
                                insertbackground='#00f3ff')
        self.entrada.pack(pady=5)
        self.entrada.bind('<KeyRelease>', lambda e: self.atualizar_braille())

        self.braille_view = tk.StringVar()
        tk.Label(root, textvariable=self.braille_view,
                 font=('Segoe UI', 18), **estilo).pack(pady=5)

        # -------------------- Falar --------------------
        self._inicializar_fala()

    # -------------------------------------------------------------
    # Saída de voz
    # -------------------------------------------------------------

    def _inicializar_fala(self):
        self.engine = None
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', 130)
        except Exception:
            pass  # sem síntese de voz: a interface continua funcionando

    def falar(self, texto):
        if self.engine and texto:
            self.engine.say(texto)
            self.engine.runAndWait()

    # -------------------------------------------------------------
    # Ações
    # -------------------------------------------------------------

    def _detectar_bytes(self, image_bytes, origem):
        """Envia bytes de imagem para a API e atualiza a interface."""
        self.status.set(f'Processando imagem de {origem}...')
        self.root.update_idletasks()
        try:
            resposta = requests.post(
                f'{API_BASE}/api/detect-braille',
                json={'image_base64': base64.b64encode(image_bytes).decode('utf-8')},
                timeout=30,
            )
            dados = resposta.json()
        except requests.ConnectionError:
            self.status.set('Erro: servidor não encontrado. Execute "python app.py" primeiro.')
            return
        except Exception as e:
            self.status.set(f'Erro ao conectar com o servidor: {e}')
            return

        if not dados.get('success'):
            self.status.set(f"Erro: {dados.get('error')}")
            return

        texto = dados.get('text', '')
        if dados.get('cells_detected', 0) == 0:
            self.status.set(dados.get('message', 'Nenhum padrão detectado.'))
            self.resultado.set('Texto traduzido: —')
        else:
            self.status.set(dados.get('message', ''))
            self.resultado.set(f'Texto traduzido: {texto}')
            self.falar(f'Texto traduzido: {texto}')

    def carregar_imagem(self):
        caminho = filedialog.askopenfilename(
            title='Selecione uma imagem de Braille',
            filetypes=[('Imagens', '*.png *.jpg *.jpeg *.bmp *.webp')],
        )
        if not caminho:
            return
        with open(caminho, 'rb') as f:
            self._detectar_bytes(f.read(), origem='arquivo')

    def capturar_camera(self):
        """Captura um frame da câmera e envia para detecção."""
        import cv2

        camera = cv2.VideoCapture(0)
        if not camera.isOpened():
            self.status.set('Erro ao acessar a câmera.')
            return

        ok, frame = camera.read()
        camera.release()
        if not ok:
            self.status.set('Erro ao capturar o frame da câmera.')
            return

        _, buffer = cv2.imencode('.jpg', frame)
        self._detectar_bytes(buffer.tobytes(), origem='câmera')

    def atualizar_braille(self):
        texto = self.entrada.get()
        self.braille_view.set(texto_para_braille(texto))

    def ouvir(self):
        texto = self.resultado.get().replace('Texto traduzido: ', '')
        if texto and texto != '—':
            self.falar(texto)
        else:
            self.falar('Nenhum texto traduzido.')


def main():
    # Verifica se o servidor está no ar
    try:
        requests.get(f'{API_BASE}/api/health', timeout=3)
    except requests.ConnectionError:
        print('AVISO: servidor não encontrado em', API_BASE)
        print('Inicie o servidor primeiro com: python app.py')

    root = tk.Tk()
    InclusitecDesktop(root)
    root.mainloop()


if __name__ == '__main__':
    main()
