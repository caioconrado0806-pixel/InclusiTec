# Inclusitec - Detector de Braille

Sistema de detecção de Braille em imagens com conversão para
português brasileiro. **Backend e frontend 100% em Python.**

```
  ┌──────────────────────────────────────────────────┐
  │  Python app.py (Flask)                           │
  │  ├─ API REST        /api/detect-braille          │
  │  │                  /api/cadastro, /api/health   │
  │  └─ Frontend web    templates + static (HTML/JS) │
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

<<<<<<< HEAD
- **Detecção de Braille**: OpenCV (padrão) ou YOLO (opcional,
  coloque `braille_yolo.pt` na raiz)
- **Conversão para PT-BR**: células Braille → texto brasileiro,
  incluindo acentos e numeração (indicador ⠼)
- **Frontend web acessível**: alto contraste, síntese de voz,
  vibração, câmera por comando de voz e célula interativa
- **Frontend desktop**: cliente em Python (Tkinter) com voz
  e captura de câmera
- **Cadastro de usuários**: API + persistência em
  JSON/CSV (abre no Excel)
=======
- **Detecção de Braille**: Usa YOLO (Ultralytics) ou OpenCV para detectar padrões de Braille em imagens
- **Conversão para PT-BR**: Converte células Braille para texto em português brasileiro
- **Interface Acessível**: Mantém o frontend existente com suporte a TalkBack e alto contraste
- **Câmera em Tempo Real**: Captura imagens da câmera para detecção instantânea
- **Upload de Imagens**: Permite selecionar arquivos de imagem para análise
- **Conversor de Documentos**: Botão que converte arquivos **PDF** e **DOCX** em texto Braille pronto para impressão
- **Impressão em Braille**: Após a conversão, aparece o botão **Imprimir**, que abre a impressão do celular ou do
  computador para enviar o documento à impressora conectada (Wi-Fi, Bluetooth ou cabo) ou salvar como PDF
>>>>>>> origin/main

## Requisitos

- Python 3.8+
- pip

## Instalação

```bash
pip install -r requirements.txt
```

No Windows, você pode usar o `install.bat`.

## Uso

### 1. Iniciar o servidor (backend + frontend web)

```bash
python app.py
```

Acesse **http://localhost:5000** — a interface web é servida
pelo próprio Python.

### 2. (Opcional) Cliente desktop em Python

```bash
python desktop/client.py
```

Interface gráfica com câmera, leitura de arquivo e voz.

### 3. Usar a detecção

1. **Por câmera**: "Capturar Foto Agora" ou "Tirar Foto
   (Comando de Voz)" → diga "tirar foto"
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

## Estrutura do Projeto

```
inclusitec/
├── app.py                  # ponto de entrada (Flask)
├── config.py               # configuração central
├── backend/
│   ├── braille/            # núcleo: mapeamentos, detector,
│   │                       #         conversor (fonte única)
│   ├── api/                # rotas: detect, cadastro, health
│   └── services/           # lógica de negócio (cadastro)
├── frontend/
│   ├── templates/index.html
│   └── static/{css,js}/    # servidos pelo Flask
├── desktop/client.py       # frontend Python (Tkinter)
├── tests/test_braille.py   # testes do núcleo
├── scripts/                # utilitários (gerar folha
│                           #   Braille, apresentações)
├── assets/                 # imagens e mídia
└── data/                   # cadastros (criado em runtime)
```

## Testes

```bash
python -m unittest discover -s tests -v
```

## Usando um Modelo YOLO Treinado

1. Treine um modelo com seu dataset de imagens de Braille
   (26 classes a-z ou 6 classes de pontos)
2. Salve como `braille_yolo.pt` na raiz do projeto
3. O detector carrega o modelo automaticamente

### Estrutura do Dataset

```
dataset/
├── images/
│   ├── train/  (img001.jpg, ...)
│   └── val/    (img101.jpg, ...)
└── labels/
    ├── train/  (img001.txt, ...)
    └── val/    (...)
```

## Notas de Acessibilidade

- Tabela de aprendizado com foco por teclado e vibração
- Botões navegáveis por Tab, saída de voz em todas as ações
- Modo de alto contraste (preto/amarelo)
- `aria-live` nas regiões de status

## Licença

Projeto open-source para fins educacionais e de acessibilidade.
