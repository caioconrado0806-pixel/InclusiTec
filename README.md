# Inclusitec - Detector de Braille com IA

Sistema de detecção de Braille em imagens usando Inteligência Artificial (YOLO/OpenCV) com conversão para português brasileiro.

## Funcionalidades

- **Detecção de Braille**: Usa YOLO (Ultralytics) ou OpenCV para detectar padrões de Braille em imagens
- **Conversão para PT-BR**: Converte células Braille para texto em português brasileiro
- **Interface Acessível**: Mantém o frontend existente com suporte a TalkBack e alto contraste
- **Câmera em Tempo Real**: Captura imagens da câmera para detecção instantânea
- **Upload de Imagens**: Permite selecionar arquivos de imagem para análise

## Requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)

## Instalação

1. Clone ou baixe os arquivos do projeto
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Uso

### Iniciar o Servidor

```bash
python app.py
```

O servidor iniciará em `http://localhost:5000`

### Acessar a Interface

Abra o navegador e acesse:
```
http://localhost:5000
```

### Usar a Detecção

1. **Por Câmera**: Clique em "Ativar Câmera por Voz" ou use o botão de câmera
2. **Por Arquivo**: Clique em "Selecionar Arquivo de Mídia" e escolha uma imagem
3. O sistema detectará automaticamente os padrões de Braille e exibirá a tradução

## API

### Endpoint: `/api/detect-braille`

**Método**: POST

**Parâmetros**:
- `image_base64`: Imagem codificada em base64 (JSON)
- `image`: Arquivo de imagem (multipart/form-data)

**Resposta**:
```json
{
  "success": true,
  "text": "texto traduzido",
  "cells_detected": 5,
  "detector": "yolo",
  "cells": [[1,0,0,0,0,0], ...],
  "annotated_image": "data:image/jpeg;base64,...",
  "message": "5 células de Braille detectadas e traduzidas."
}
```

### Endpoint: `/api/health`

**Método**: GET

**Resposta**:
```json
{
  "status": "ok",
  "service": "Inclusitec Braille Detector",
  "opencv_version": "4.8.1"
}
```

## Usando um Modelo YOLO Treinado

Para usar um modelo YOLO treinado especificamente para Braille:

1. Treine um modelo YOLO com seu dataset de imagens de Braille
2. Salve o modelo treinado como `braille_yolo.pt` na pasta do projeto
3. O sistema detectará e usará automaticamente o modelo

### Estrutura do Dataset para Treinamento

```
dataset/
├── images/
│   ├── train/
│   │   ├── img001.jpg
│   │   ├── img002.jpg
│   │   └── ...
│   └── val/
│       ├── img101.jpg
│       └── ...
└── labels/
    ├── train/
    │   ├── img001.txt
    │   └── ...
    └── val/
        └── ...
```

### Classes do Modelo

O modelo YOLO pode ser treinado com:
- **26 classes** (a-z): Cada classe representa uma letra
- **6 classes** (pontos 1-6): Cada classe representa um ponto Braille individual

## Arquivos do Projeto

- `app.py`: Servidor Flask com API de detecção
- `index.html`: Interface web acessível
- `requirements.txt`: Dependências Python
- `braille_yolo.pt`: Modelo YOLO treinado (opcional)

## Suporte

Para problemas ou sugestões, verifique:
1. Se o servidor está rodando corretamente
2. Se as dependências estão instaladas
3. Se a câmera está funcionando (para detecção em tempo real)
4. Se a imagem contém padrões de Braille visíveis

## Licença

Projeto open-source para fins educacionais e de acessibilidade.
