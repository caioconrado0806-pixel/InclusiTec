# Inclusitec - Detector de Braille

Sistema de detecção de Braille em imagens com conversão para
português brasileiro. **Backend e frontend 100% em Python.**

🔗 **Versão online: https://inclusitec.com**

```
  ┌──────────────────────────────────────────────────┐
  │  Python api/index.py (Flask)                     │
  │  ├─ API REST    /api/detect-braille              │
  │  │                /api/cadastro, /api/health     │
  │  │                /api/braille/pdf, /api/print   │
  │  └─ Frontend web  templates + static (HTML/JS)   │
  └──────────────────────────────────────────────────┘
        ▲                          ▲
        │ HTTP                     │ HTTP
  ┌─────────────┐        ┌──────────────────┐
  │ Navegador   │        │ desktop/client.py│
  │ (frontend)  │        │ frontend em      │
  │             │        │ Python (Tkinter) │
  └─────────────┘        └──────────────────┘
```

## Funcionalidades

- **Detecção de Braille**: IA única baseada em visão
  computacional (OpenCV) — localiza os pontos elevados
  e traduz para texto
- **Conversão para PT-BR**: células Braille → texto brasileiro,
  incluindo acentos e numeração (indicador ⠼)
- **Frontend web acessível**: alto contraste, síntese de voz,
  vibração, câmera por comando de voz e célula interativa
- **Câmera em tempo real**: captura imagens da câmera para
  detecção instantânea
- **Upload de imagens**: permite selecionar arquivos de imagem
  para análise
- **Conversor de documentos**: converte **PDF**, Word (.docx),
  .odt, .rtf, .pptx, .xlsx, HTML e arquivos de texto em
  Braille pronto para impressão (.brf/.brl/.txt)
- **Impressão em Braille**: envia o documento à impressora
  conectada (Wi-Fi, Bluetooth ou cabo) ou salva como PDF
- **Frontend desktop**: cliente em Python (Tkinter) com voz
  e captura de câmera
- **Cadastro de usuários**: API + persistência em
  JSON/CSV (abre no Excel)

## Requisitos

- Python 3.8+
- pip

## Instalação

```bash
pip install -r requirements.txt
```

No Windows, você pode usar o `install.bat`.

## Uso

### 1. Versão online

A aplicação já está no ar em **https://inclusitec.com**
(implantada na Vercel — o entrypoint serverless é
`api/index.py`, apontado no `vercel.json`).

### 2. Iniciar o servidor localmente (backend + frontend web)

```bash
python -m flask --app api.index run
```

Acesse **http://localhost:5000** — a interface web é servida
pelo próprio Python.

Alternativa: `vercel dev` roda localmente no mesmo modo
serverless da nuvem.

### 3. (Opcional) Cliente desktop em Python

```bash
python desktop/client.py
```

Interface gráfica com câmera, leitura de arquivo e voz.

### 4. Usar a detecção

1. **Por câmera**: "Tirar Foto (Comando de Voz)" → diga
   "tirar foto"; a câmera abre, enquadra a folha em tempo
   real e fotografa sozinha quando estiver alinhada
2. **Por arquivo**: "Selecionar Arquivo de Mídia"
3. O sistema detecta os padrões de Braille, exibe o texto
   traduzido e a imagem com os pontos destacados

## API

### `POST /api/detect-braille`

Imagem via multipart (`image`) ou JSON (`image_base64`):

```json
{
  "image_base64": "data:image/jpeg;base64,..."
}
```

Resposta:

```json
{
  "success": true,
  "text": "inclusitec",
  "cells_detected": 11,
  "detector": "opencv",
  "cells": [[1,0,0,0,0,0], "..."],
  "annotated_image": "data:image/jpeg;base64,...",
  "message": "11 células de Braille detectadas e traduzidas."
}
```

### `POST /api/cadastro`

```json
{
  "nome": "Maria Silva",
  "email": "maria@exemplo.com",
  "telefone": "(11) 99999-9999",
  "perfil": "Deficiente Visual"
}
```

Salva em `data/cadastros.json` e exporta
`data/cadastros.csv` (compatível com Excel).

### `GET /api/health`

Verifica o servidor e mostra o detector ativo.

### `POST /api/braille/pdf`

Documento via multipart (`pdf`): PDF, .docx, .odt, .rtf, .pptx,
.xlsx, HTML ou texto. Extrai o texto e devolve
a conversão em Braille, pronta para impressão:

```json
{
  "success": true,
  "paginas": 3,
  "celulas": 1204,
  "braille_preview": "⠊⠝⠉⠇⠥⠎⠊⠞⠑⠉...",
  "arquivos": {
    "brf": { "url": "/api/braille/jobs/<id>/download/brf" },
    "brl": { "url": "/api/braille/jobs/<id>/download/brl" },
    "txt": { "url": "/api/braille/jobs/<id>/download/txt" }
  }
}
```

### `GET /api/printers` e `POST /api/print`

Lista as impressoras do sistema e envia o arquivo
convertido (`.brf`) à impressora Braille conectada
(Wi-Fi, Bluetooth ou cabo).

## Estrutura do Projeto

```
inclusitec/
├── api/index.py            # entrypoint da app (Vercel)
├── config.py               # configuração central
├── backend/
│   ├── braille/            # núcleo: mapeamentos, detector,
│   │                       #         conversor (fonte única)
│   ├── api/                # rotas: detect, cadastro, health,
│   │                       #         pdf -> braille, print
│   └── services/           # lógica de negócio (cadastro)
├── frontend/
│   ├── templates/index.html
│   └── static/{css,js}/    # servidos pelo Flask
├── desktop/client.py       # frontend Python (Tkinter)
├── tests/test_braille.py   # testes do núcleo
├── assets/                 # imagens e mídia
└── data/                   # cadastros (criado em runtime)
```

## Testes

```bash
python -m unittest discover -s tests -v
```

## IA de Detecção

O projeto utiliza **uma única IA** para detectar Braille:
o detector baseado em OpenCV (`backend/braille/detector.py`).
Não há dependência de modelos externos — a detecção roda
100% no servidor com apenas `opencv-python-headless`.

Essa mesma IA única atende todos os clientes: o site
**https://inclusitec.com**, o cliente desktop e os testes.

## Notas de Acessibilidade

- Tabela de aprendizado com foco por teclado e vibração
- Botões navegáveis por Tab, saída de voz em todas as ações
- Modo de alto contraste (preto/amarelo)
- `aria-live` nas regiões de status

## Licença

Projeto open-source para fins educacionais e de acessibilidade.
