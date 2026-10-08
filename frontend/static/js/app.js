/*
 * Inclusitec - Lógica do frontend
 *
 * Fluxo da aplicação:
 *   1. Cadastro  -> POST /api/cadastro   (salva no servidor + cópia local)
 *   2. Leitura   -> POST /api/detect-braille (câmera ou arquivo -> texto PT-BR)
 *   3. Tradução  -> texto <-> Braille (tabela local, mesma convenção do backend)
 */

// -------------------------------------------------------------
// TABELA BRAILLE (convenção oficial MEC/ABRES, idêntica ao
// backend/braille/mapping.py)
// Pontos: 1=esq.topo 2=esq.meio 3=esq.base 4=dir.topo 5=dir.meio 6=dir.base
// -------------------------------------------------------------

const BRAILLE_PATTERNS = {
    'a': [1], 'b': [1, 2], 'c': [1, 4], 'd': [1, 4, 5], 'e': [1, 5],
    'f': [1, 2, 4], 'g': [1, 2, 4, 5], 'h': [1, 2, 5], 'i': [2, 4], 'j': [2, 4, 5],
    'k': [1, 3], 'l': [1, 2, 3], 'm': [1, 3, 4], 'n': [1, 3, 4, 5], 'o': [1, 3, 5],
    'p': [1, 2, 3, 4], 'q': [1, 2, 3, 4, 5], 'r': [1, 2, 3, 5], 's': [2, 3, 4],
    't': [2, 3, 4, 5], 'u': [1, 3, 6], 'v': [1, 2, 3, 6], 'w': [2, 4, 5, 6],
    'x': [1, 3, 4, 6], 'y': [1, 3, 4, 5, 6], 'z': [1, 3, 5, 6],
    'á': [1, 2, 3, 5, 6], 'à': [1, 2, 4, 6], 'â': [1, 6], 'ã': [3, 4, 5],
    'é': [1, 2, 3, 4, 5, 6], 'ê': [1, 2, 6], 'í': [3, 4], 'ó': [3, 4, 6],
    'ô': [1, 4, 5, 6], 'õ': [2, 4, 6], 'ú': [2, 3, 4, 5, 6], 'ç': [1, 2, 3, 4, 6],
    ',': [2], ';': [2, 3], ':': [2, 5], '!': [2, 3, 5], '?': [2, 6],
    '"': [2, 3, 6], '.': [3], '-': [3, 6], ' ': []
};

// Letras para a célula interativa (combinação de pontos -> letra)
const cellMap = {
    '1': 'A', '12': 'B', '14': 'C', '145': 'D', '15': 'E', '124': 'F', '1245': 'G',
    '125': 'H', '24': 'I', '245': 'J', '13': 'K', '123': 'L', '134': 'M', '1345': 'N',
    '135': 'O', '1234': 'P', '12345': 'Q', '1235': 'R', '234': 'S', '2345': 'T',
    '136': 'U', '1236': 'V', '2456': 'W', '1346': 'X', '13456': 'Y', '1356': 'Z'
};

// -------------------------------------------------------------
// BANCO DE DADOS LOCAL (IndexedDB) - cópia de segurança dos cadastros
// -------------------------------------------------------------

let db;
const request = indexedDB.open('InclusitecDB', 1);

request.onupgradeneeded = function (e) {
    db = e.target.result;
    if (!db.objectStoreNames.contains('cadastros')) {
        db.createObjectStore('cadastros', { keyPath: 'id', autoIncrement: true });
    }
};

request.onsuccess = function (e) {
    db = e.target.result;
};

// -------------------------------------------------------------
// ACESSIBILIDADE (voz, vibração, alto contraste)
// -------------------------------------------------------------

function toggleContrast() {
    document.body.classList.toggle('high-contrast');
    speakText('Modo de alto contraste alterado.');
}

function speakText(text) {
    if (!text) return;
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'pt-BR';
        utterance.rate = 0.9;
        window.speechSynthesis.speak(utterance);
    }
}

function triggerVibration(pattern = 50) {
    if ('vibrate' in navigator) {
        navigator.vibrate(pattern);
    }
}

// -------------------------------------------------------------
// UTILIDADES BRAILLE
// -------------------------------------------------------------

/** Converte pontos ativos (1-6) no caractere Braille Unicode. */
function brailleUnicode(dots) {
    const bit = { 1: 0x01, 2: 0x02, 3: 0x04, 4: 0x08, 5: 0x10, 6: 0x20 };
    let code = 0x2800;
    for (const d of dots) code += bit[d];
    return String.fromCharCode(code);
}

/** Traduz texto para a representação Braille (mesma convenção do backend). */
function translateToBraille() {
    const text = document.getElementById('textInput').value.toLowerCase();
    let result = '';
    for (const char of text) {
        const pattern = BRAILLE_PATTERNS[char];
        result += pattern ? brailleUnicode(pattern) : char;
    }
    document.getElementById('brailleResult').innerText = result;
}

// -------------------------------------------------------------
// CÉLULA INTERATIVA
// -------------------------------------------------------------

let activeDots = new Set();

function toggleDot(num) {
    const dotElem = document.getElementById(`dot${num}`);
    if (activeDots.has(num)) {
        activeDots.delete(num);
        dotElem.classList.remove('active');
    } else {
        activeDots.add(num);
        dotElem.classList.add('active');
    }
    playBeep(200 + (num * 100));
    triggerVibration(30);
}

function playBeep(freq) {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        osc.frequency.value = freq;
        osc.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + 0.1);
    } catch (e) { /* áudio indisponível */ }
}

function handleCellKeyDown(e) {
    if (e.key === 'Enter') {
        const key = Array.from(activeDots).sort().join('');
        const letter = cellMap[key] || 'Combinação não reconhecida';
        document.getElementById('cellOutput').innerText = `Letra: ${letter}`;
        speakText(`Letra ${letter}`);
    }
}

// -------------------------------------------------------------
// FLUXO 1 - CADASTRO
// -------------------------------------------------------------

async function salvarCadastro(event) {
    event.preventDefault();

    const dados = {
        nome: document.getElementById('nome').value,
        email: document.getElementById('email').value,
        telefone: document.getElementById('telefone').value,
        perfil: document.getElementById('perfil').value,
        dataCadastro: new Date().toLocaleString('pt-BR')
    };

    // 1. Salva no banco local do navegador (IndexedDB) - cópia de segurança
    try {
        const transaction = db.transaction(['cadastros'], 'readwrite');
        transaction.objectStore('cadastros').add(dados);
    } catch (e) {
        console.error('Erro ao salvar localmente:', e);
    }

    // 2. Envia para a API Python (salva no servidor)
    try {
        speakText('Processando cadastro...');
        const response = await fetch('/api/cadastro', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dados)
        });

        if (!response.ok) {
            const erro = await response.json().catch(() => ({}));
            throw new Error(erro.error || 'Erro no servidor');
        }

        speakText('Cadastro efetuado com sucesso!');
        alert('Cadastro realizado com sucesso! Dados salvos no servidor.');
        document.getElementById('cadastroForm').reset();
    } catch (error) {
        console.error('Erro no envio:', error);
        speakText('Cadastro salvo localmente, mas não foi possível conectar ao servidor.');
        alert(`Cadastro salvo localmente no navegador! Erro ao conectar com o servidor: ${error.message}`);
    }
}

// -------------------------------------------------------------
// FLUXO 2 - LEITURA DE BRAILLE (CÂMERA E ARQUIVO)
// -------------------------------------------------------------

function setStatus(msg) {
    document.getElementById('detectStatus').innerText = msg;
}

/** Envia uma imagem (data URL) para a API e exibe o resultado. */
async function detectFromDataUrl(dataUrl) {
    setStatus('Processando imagem...');
    speakText('Processando imagem.');
    try {
        const response = await fetch('/api/detect-braille', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_base64: dataUrl })
        });
        const resultado = await response.json();

        if (!response.ok || !resultado.success) {
            throw new Error(resultado.error || 'Falha na detecção');
        }

        if (resultado.cells_detected === 0) {
            setStatus(resultado.message || 'Nenhum padrão de Braille detectado.');
            speakText(resultado.message || 'Nenhum padrão de Braille detectado.');
            document.getElementById('annotatedImage').style.display = 'none';
            return;
        }

        // Exibe texto traduzido
        document.getElementById('detectResult').innerText = resultado.text;
        setStatus(`${resultado.message} (detector: ${resultado.detector})`);

        // Exibe imagem com os pontos destacados
        if (resultado.annotated_image) {
            const img = document.getElementById('annotatedImage');
            img.src = resultado.annotated_image;
            img.style.display = 'block';
        }

        speakText(`Texto traduzido: ${resultado.text}`);
        triggerVibration([50, 30, 50]);
    } catch (error) {
        console.error('Erro na detecção:', error);
        setStatus(`Erro ao processar imagem: ${error.message}`);
        speakText('Erro ao processar a imagem.');
    }
}

/** Captura o frame atual do vídeo e envia para detecção. */
function detectPhoto() {
    const video = document.getElementById('videoFeed');
    const canvas = document.getElementById('photoCanvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
    detectFromDataUrl(dataUrl);
}

/** Ativa a câmera, captura após 3s e detecta (fluxo por comando de voz). */
function capturePhoto() {
    const video = document.getElementById('videoFeed');
    video.style.display = 'block';
    navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
        video.srcObject = stream;
        video.play();
        setTimeout(() => {
            stream.getTracks().forEach(track => track.stop());
            video.style.display = 'none';
            detectPhoto();
            speakText('Imagem Braille identificada e capturada com sucesso.');
        }, 3000);
    }).catch(() => {
        video.style.display = 'none';
        speakText('Erro ao acessar a câmera.');
        setStatus('Erro ao acessar a câmera.');
    });
}

/** Ativa o reconhecimento de voz; ao ouvir "tirar foto", captura. */
function startVoiceCamera() {
    speakText('Microfone ativado. Diga: tirar foto.');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        alert('Reconhecimento de voz não suportado neste navegador. Use "Capturar Foto Agora".');
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'pt-BR';
    recognition.start();

    recognition.onresult = (event) => {
        const command = event.results[0][0].transcript.toLowerCase();
        if (command.includes('tirar foto')) {
            capturePhoto();
        } else {
            speakText('Comando não reconhecido. Tente dizer tirar foto.');
        }
    };
}

/** Captura a foto diretamente, sem comando de voz. */
function capturarFotoDireta() {
    const video = document.getElementById('videoFeed');
    // Se a câmera já está ativa, captura o frame; caso contrário, ativa e captura.
    if (video.srcObject && video.srcObject.active) {
        detectPhoto();
    } else {
        capturePhoto();
    }
}

/** Lê o arquivo selecionado e envia para detecção. */
function handleFile(input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    speakText(`Arquivo selecionado: ${file.name}. Processando leitura Braille.`);

    const reader = new FileReader();
    reader.onload = () => detectFromDataUrl(reader.result);
    reader.onerror = () => {
        setStatus('Erro ao ler o arquivo.');
        speakText('Erro ao ler o arquivo.');
    };
    reader.readAsDataURL(file);

    // Permite selecionar outro arquivo com o mesmo nome
    input.value = '';
}

/** Fala o texto traduzido da detecção (ou do campo de tradução). */
function ouvirTraducao() {
    const detectado = document.getElementById('detectResult').innerText;
    const digitado = document.getElementById('brailleResult').innerText;
    const texto = (detectado && detectado !== '—') ? detectado
        : (document.getElementById('textInput').value || 'Nenhum texto traduzido');
    speakText(texto);
}

// -------------------------------------------------------------
// APRENDIZADO E DESCRIÇÃO DA PÁGINA
// -------------------------------------------------------------

function toggleLearnTable() {
    const table = document.getElementById('learnTable');
    if (table.style.display === 'block') {
        table.style.display = 'none';
        return;
    }
    table.style.display = 'block';
    if (table.innerHTML !== '') return;

    Object.keys(BRAILLE_PATTERNS).forEach((char, idx) => {
        if (char.trim() === '') return;
        const row = document.createElement('div');
        row.className = 'learn-row';
        row.tabIndex = 0;
        row.innerText = `Letra em tinta: ${char.toUpperCase()}  =>  Representação Braille: ${brailleUnicode(BRAILLE_PATTERNS[char])}`;
        const vibrar = () => triggerVibration(20 * (idx + 1));
        row.onmouseenter = vibrar;
        row.onfocus = () => {
            vibrar();
            speakText(`Letra ${char}`);
        };
        table.appendChild(row);
    });
}

function describePage() {
    const description = (
        'Você está no aplicativo Inclusitec. A página tem cinco seções: ' +
        'cadastro de usuário; leitura de Braille por câmera ou arquivo, com tradução e imagem dos pontos detectados; ' +
        'conversão de PDF em arquivo para impressora Braille, com botão imprimir; ' +
        'tradução de texto digitado para Braille; célula interativa de seis pontos para treino; ' +
        'e tabela de aprendizado com descrição da página.'
    );
    speakText(description);
}

// -------------------------------------------------------------
// FLUXO 3 - PDF -> IMPRESSORA BRAILLE (conversão + impressão)
// -------------------------------------------------------------

// Último trabalho de conversão realizado nesta sessão.
let brailleJob = null;

function setPdfStatus(msg) {
    const el = document.getElementById('pdfStatus');
    if (el) el.innerText = msg || '';
}

function setPrintStatus(msg) {
    const el = document.getElementById('printStatus');
    if (el) el.innerText = msg || '';
}

/** Abre o seletor de arquivos do conversor de PDF. */
function selecionarPdfBraille() {
    triggerVibration(40);
    playBeep(600);
    document.getElementById('pdfInput').click();
}

/** Envia o PDF escolhido para /api/braille/pdf e mostra o resultado. */
async function converterPdfBraille(input) {
    const file = input.files && input.files[0];
    if (!file) return;

    const isPdf = /\.pdf$/i.test(file.name) || file.type === 'application/pdf';
    if (!isPdf) {
        setPdfStatus('Arquivo inválido: escolha um documento com extensão .pdf.');
        speakText('Arquivo inválido. Escolha um arquivo PDF.');
        input.value = '';
        return;
    }

    document.getElementById('pdfResult').style.display = 'none';
    document.getElementById('printBox').style.display = 'none';
    setPdfStatus(`Convertendo "${file.name}" para Braille... Aguarde.`);
    speakText('Convertendo o arquivo PDF para Braille. Aguarde.');
    triggerVibration([40, 40, 40]);

    try {
        const form = new FormData();
        form.append('pdf', file, file.name);

        const response = await fetch('/api/braille/pdf', { method: 'POST', body: form });
        const data = await response.json().catch(() => ({}));

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Falha na conversão do PDF');
        }

        brailleJob = data;
        mostrarResultadoPdf(data);
        setPdfStatus(data.message);
        speakText('Arquivo convertido com sucesso. O botão imprimir está disponível.');
        triggerVibration([60, 30, 60]);
    } catch (error) {
        console.error('Erro na conversão PDF:', error);
        setPdfStatus(`Erro ao converter: ${error.message}`);
        speakText(`Erro ao converter o arquivo: ${error.message}`);
    } finally {
        input.value = '';  // permite selecionar o mesmo arquivo de novo
    }
}

/** Exibe pré-visualização, links de download e o botão Imprimir. */
function mostrarResultadoPdf(data) {
    document.getElementById('pdfBraillePreview').innerText = data.braille_preview || '';

    document.getElementById('pdfStats').innerText = [
        `${data.paginas} página(s)`,
        `${data.caracteres} caracteres`,
        `${data.celulas} células Braille`,
        `${data.linhas} linha(s) de ${data.largura} células`,
        data.truncated ? 'pré-visualização parcial' : ''
    ].filter(Boolean).join(' · ');

    const arquivos = data.arquivos || {};
    const brf = arquivos.brf;
    const brl = arquivos.brl;

    if (brf) {
        const link = document.getElementById('downloadBrf');
        link.href = brf.url;
        link.setAttribute('download', brf.nome);
    }
    if (brl) {
        const link = document.getElementById('downloadBrl');
        link.href = brl.url;
        link.setAttribute('download', brl.nome);
    }

    document.getElementById('pdfResult').style.display = 'block';
    carregarImpressoras();
}

/** Carrega a lista de impressoras do sistema no campo de seleção. */
async function carregarImpressoras() {
    const printBox = document.getElementById('printBox');
    const select = document.getElementById('printerSelect');
    printBox.style.display = 'block';
    select.innerHTML = '<option value="">Carregando impressoras...</option>';
    setPrintStatus('');

    try {
        const response = await fetch('/api/printers');
        const data = await response.json();
        const printers = data.printers || [];

        select.innerHTML = '';

        if (!printers.length) {
            select.innerHTML = '<option value="">Nenhuma impressora detectada</option>';
            setPrintStatus('Nenhuma impressora detectada. Use "Imprimir pelo navegador".');
            return;
        }

        printers.forEach(nome => {
            const option = document.createElement('option');
            option.value = nome;
            option.innerText = nome + (nome === data.default ? '  (padrão)' : '');
            if (nome === data.default) option.selected = true;
            select.appendChild(option);
        });

        setPrintStatus(`${printers.length} impressora(s) disponível(is).`);
    } catch (error) {
        console.error('Erro ao listar impressoras:', error);
        select.innerHTML = '<option value="">Impressoras indisponíveis</option>';
        setPrintStatus('Não foi possível listar as impressoras do sistema.');
    }
}

/** Envia o arquivo .brf convertido para a impressora escolhida. */
async function imprimirBraille() {
    if (!brailleJob) {
        setPrintStatus('Nenhum arquivo convertido. Converta um PDF primeiro.');
        speakText('Nenhum arquivo convertido ainda.');
        return;
    }

    const printer = document.getElementById('printerSelect').value;
    const button = document.getElementById('printBtn');

    button.disabled = true;
    setPrintStatus(printer
        ? `Enviando o arquivo para "${printer}"...`
        : 'Enviando o arquivo para a impressora padrão...');
    speakText('Enviando o arquivo para a impressora.');

    try {
        const response = await fetch('/api/print', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                job_id: brailleJob.job_id,
                printer: printer,
                format: 'brf'
            })
        });
        const data = await response.json().catch(() => ({}));

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Falha ao imprimir');
        }

        setPrintStatus(data.message || 'Arquivo enviado para a impressora.');
        speakText('Arquivo enviado para a impressora com sucesso.');
        triggerVibration([80, 40, 80]);
    } catch (error) {
        console.error('Erro ao imprimir:', error);
        setPrintStatus(`Erro ao imprimir: ${error.message} Use "Imprimir pelo navegador".`);
        speakText(`Erro ao imprimir: ${error.message}`);
    } finally {
        button.disabled = false;
    }
}

/** Alternativa: abre a janela de impressão do próprio navegador/Windows. */
function imprimirNoNavegador() {
    const area = document.getElementById('printArea');
    const conteudo = document.getElementById('pdfBraillePreview').innerText || '';
    const titulo = brailleJob ? brailleJob.filename : 'Documento Braille';

    area.innerHTML = '';

    const h = document.createElement('h1');
    h.innerText = `Braille - ${titulo}`;

    const meta = document.createElement('p');
    meta.innerText = document.getElementById('pdfStats').innerText || '';

    const pre = document.createElement('pre');
    pre.innerText = conteudo;

    area.appendChild(h);
    area.appendChild(meta);
    area.appendChild(pre);

    speakText('Abrindo a janela de impressão do navegador.');
    setTimeout(() => window.print(), 150);
}
