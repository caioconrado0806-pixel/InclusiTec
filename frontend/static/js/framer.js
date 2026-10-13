/*
 * Inclusitec - Enquadramento do papel Braille em tempo real
 *
 * Fluxo:
 *   1. abrirEnquadramento()  -> câmera traseira em tela cheia
 *   2. a cada quadro, detectarPapel() localiza a folha branca e
 *      desenha o contorno no canvas; a voz orienta o ajuste
 *   3. com a folha alinhada e parada, a foto é tirada sozinha
 *   4. a folha é recortada, "desentortada" (perspectiva) e tem o
 *      relevo realçado antes de ir para /api/detect-braille
 *
 * Tudo roda no navegador (visão computacional em canvas, sem
 * bibliotecas externas).
 */

// -------------------------------------------------------------
// PARÂMETROS
// -------------------------------------------------------------

const FRAMER = {
    procSize: 240,        // lado maior do quadro analisado em tempo real
    refineSize: 960,      // lado maior usado no refino dos cantos da foto final
    maxCapture: 3000,     // lado maior máximo do quadro capturado
    outMin: 1200,         // lado maior mínimo da folha retificada
    outMax: 2000,         // lado maior máximo da folha retificada
    frameInterval: 80,    // ms entre análises (~12 por segundo)
    stableFrames: 10,     // quadros seguidos alinhados para disparar
    stableShift: 0.015,   // movimento máximo dos cantos (fração da diagonal)
    minFit: 0.68,         // a folha deve ocupar ao menos isto do quadro
    maxOffset: 0.13,      // desvio máximo do centro (fração do quadro)
    maxSkew: 1.3,         // razão máxima entre lados opostos (perspectiva)
    minLum: 95,           // luminância média mínima da folha
    cropInset: 0.012,     // margem cortada para dentro da folha
    speakGap: 2500,       // ms mínimos entre orientações faladas
    speakRepeat: 7000     // ms para repetir a mesma orientação
};

// -------------------------------------------------------------
// DETECÇÃO DA FOLHA (visão computacional)
// -------------------------------------------------------------

/** Ajusta uma reta (mínimos quadrados totais) a um conjunto de pontos. */
function ajustarReta(pts) {
    let mx = 0, my = 0;
    for (const p of pts) { mx += p.x; my += p.y; }
    mx /= pts.length;
    my /= pts.length;

    let sxx = 0, syy = 0, sxy = 0;
    for (const p of pts) {
        const dx = p.x - mx, dy = p.y - my;
        sxx += dx * dx;
        syy += dy * dy;
        sxy += dx * dy;
    }
    const ang = 0.5 * Math.atan2(2 * sxy, sxx - syy);
    return { x: mx, y: my, dx: Math.cos(ang), dy: Math.sin(ang) };
}

/** Distância (com sinal) de um ponto a uma reta. */
function distanciaReta(reta, p) {
    return (p.x - reta.x) * reta.dy - (p.y - reta.y) * reta.dx;
}

/** Interseção de duas retas (ou null se paralelas). */
function cruzarRetas(a, b) {
    const det = a.dx * b.dy - a.dy * b.dx;
    if (Math.abs(det) < 1e-9) return null;
    const t = ((b.x - a.x) * b.dy - (b.y - a.y) * b.dx) / det;
    return { x: a.x + t * a.dx, y: a.y + t * a.dy };
}

/** Área (com sinal) de um polígono. */
function areaPoligono(pts) {
    let a = 0;
    for (let i = 0; i < pts.length; i++) {
        const p = pts[i], q = pts[(i + 1) % pts.length];
        a += p.x * q.y - q.x * p.y;
    }
    return a / 2;
}

/**
 * Refina os 4 cantos: ajusta uma reta a cada lado da silhueta
 * (ignorando as regiões dos cantos e pontos fora da reta, como
 * dedos segurando a folha) e cruza as retas vizinhas.
 */
function refinarCantos(cantos, silhueta, w, h) {
    const tol = Math.max(2.5, 0.03 * Math.max(w, h));
    const lados = [[], [], [], []];

    for (const p of silhueta) {
        let melhor = -1, menor = tol;
        for (let k = 0; k < 4; k++) {
            const a = cantos[k], b = cantos[(k + 1) % 4];
            const vx = b.x - a.x, vy = b.y - a.y;
            const len2 = vx * vx + vy * vy;
            if (len2 < 1) continue;
            const t = ((p.x - a.x) * vx + (p.y - a.y) * vy) / len2;
            if (t < 0.08 || t > 0.92) continue;
            const d = Math.abs((p.x - a.x) * vy - (p.y - a.y) * vx) / Math.sqrt(len2);
            if (d < menor) { menor = d; melhor = k; }
        }
        if (melhor >= 0) lados[melhor].push(p);
    }

    const retas = [];
    for (let k = 0; k < 4; k++) {
        let pts = lados[k];
        if (pts.length < 6) return cantos;
        let reta = ajustarReta(pts);
        // Duas rodadas descartando os pontos mais distantes da reta.
        for (let rodada = 0; rodada < 2; rodada++) {
            let soma = 0;
            for (const p of pts) soma += distanciaReta(reta, p) ** 2;
            const limite = Math.max(0.75, 2 * Math.sqrt(soma / pts.length));
            const filtrados = pts.filter(p => Math.abs(distanciaReta(reta, p)) <= limite);
            if (filtrados.length < 6) break;
            pts = filtrados;
            reta = ajustarReta(pts);
        }
        retas.push(reta);
    }

    const maxDesvio = 0.12 * Math.hypot(w, h);
    const refinados = [];
    for (let k = 0; k < 4; k++) {
        const c = cruzarRetas(retas[(k + 3) % 4], retas[k]);
        if (!c || Math.hypot(c.x - cantos[k].x, c.y - cantos[k].y) > maxDesvio) return cantos;
        refinados.push(c);
    }
    return refinados;
}

/**
 * Localiza a folha branca em um quadro RGBA.
 *
 * Returns:
 *   null se não houver folha, ou um objeto com os 4 cantos
 *   (ordem: superior-esquerdo, superior-direito, inferior-direito,
 *   inferior-esquerdo, em pixels do quadro) e as medidas usadas
 *   para orientar o usuário.
 */
function detectarPapel(rgba, w, h) {
    const n = w * h;
    const lum = new Uint8Array(n);
    const claro = new Uint8Array(n);
    const hist = new Uint32Array(256);

    let soma = 0, somaQ = 0;
    for (let i = 0, p = 0; i < n; i++, p += 4) {
        const l = (rgba[p] * 77 + rgba[p + 1] * 150 + rgba[p + 2] * 29) >> 8;
        lum[i] = l;
        hist[l]++;
        soma += l;
        somaQ += l * l;
    }

    // Limiar de Otsu: separa a folha clara do fundo.
    let somaB = 0, pesoB = 0, melhorVar = 0, limiar = 127;
    for (let t = 0; t < 256; t++) {
        pesoB += hist[t];
        if (!pesoB) continue;
        const pesoF = n - pesoB;
        if (!pesoF) break;
        somaB += t * hist[t];
        const dif = somaB / pesoB - (soma - somaB) / pesoF;
        const v = pesoB * pesoF * dif * dif;
        if (v > melhorVar) { melhorVar = v; limiar = t; }
    }
    const media = soma / n;
    const varTotal = somaQ / n - media * media;
    const separacao = varTotal > 1 ? (melhorVar / n / n) / varTotal : 0;

    // Folha = claro e sem cor (branco).
    for (let i = 0, p = 0; i < n; i++, p += 4) {
        if (lum[i] <= limiar) continue;
        const r = rgba[p], g = rgba[p + 1], b = rgba[p + 2];
        const sat = Math.max(r, g, b) - Math.min(r, g, b);
        if (sat < 90) claro[i] = 1;
    }

    // Maior região clara conectada.
    const rotulo = new Int32Array(n);
    const pilha = new Int32Array(n);
    let melhorId = 0, melhorArea = 0, id = 0;
    for (let ini = 0; ini < n; ini++) {
        if (!claro[ini] || rotulo[ini]) continue;
        id++;
        let topo = 0, area = 0;
        pilha[topo++] = ini;
        rotulo[ini] = id;
        while (topo) {
            const i = pilha[--topo];
            area++;
            const x = i % w;
            if (x > 0 && claro[i - 1] && !rotulo[i - 1]) { rotulo[i - 1] = id; pilha[topo++] = i - 1; }
            if (x < w - 1 && claro[i + 1] && !rotulo[i + 1]) { rotulo[i + 1] = id; pilha[topo++] = i + 1; }
            if (i >= w && claro[i - w] && !rotulo[i - w]) { rotulo[i - w] = id; pilha[topo++] = i - w; }
            if (i < n - w && claro[i + w] && !rotulo[i + w]) { rotulo[i + w] = id; pilha[topo++] = i + w; }
        }
        if (area > melhorArea) { melhorArea = area; melhorId = id; }
    }
    if (melhorArea < 0.04 * n) return null;

    // Silhueta externa: extremos de cada linha e de cada coluna.
    const linMin = new Int32Array(h).fill(-1), linMax = new Int32Array(h).fill(-1);
    const colMin = new Int32Array(w).fill(-1), colMax = new Int32Array(w).fill(-1);
    let cx = 0, cy = 0, somaLum = 0;
    for (let y = 0, i = 0; y < h; y++) {
        for (let x = 0; x < w; x++, i++) {
            if (rotulo[i] !== melhorId) continue;
            if (linMin[y] < 0) linMin[y] = x;
            linMax[y] = x;
            if (colMin[x] < 0) colMin[x] = y;
            colMax[x] = y;
            cx += x;
            cy += y;
            somaLum += lum[i];
        }
    }
    cx /= melhorArea;
    cy /= melhorArea;

    const silhueta = [];
    const bordas = { esquerda: 0, direita: 0, cima: 0, baixo: 0 };
    for (let y = 0; y < h; y++) {
        if (linMin[y] < 0) continue;
        silhueta.push({ x: linMin[y], y }, { x: linMax[y], y });
        if (linMin[y] === 0) bordas.esquerda++;
        if (linMax[y] === w - 1) bordas.direita++;
    }
    for (let x = 0; x < w; x++) {
        if (colMin[x] < 0) continue;
        silhueta.push({ x, y: colMin[x] }, { x, y: colMax[x] });
        if (colMin[x] === 0) bordas.cima++;
        if (colMax[x] === h - 1) bordas.baixo++;
    }
    bordas.esquerda /= h;
    bordas.direita /= h;
    bordas.cima /= w;
    bordas.baixo /= w;

    // Cantos iniciais: A = mais longe do centro; C = mais longe de A;
    // B e D = mais afastados da diagonal AC, um de cada lado.
    const maisLonge = (ox, oy) => {
        let melhor = silhueta[0], maior = -1;
        for (const p of silhueta) {
            const d = (p.x - ox) ** 2 + (p.y - oy) ** 2;
            if (d > maior) { maior = d; melhor = p; }
        }
        return melhor;
    };
    const A = maisLonge(cx, cy);
    const C = maisLonge(A.x, A.y);
    let B = A, D = A, maxB = 0, maxD = 0;
    for (const p of silhueta) {
        const lado = (C.x - A.x) * (p.y - A.y) - (C.y - A.y) * (p.x - A.x);
        if (lado > maxB) { maxB = lado; B = p; }
        if (lado < maxD) { maxD = lado; D = p; }
    }
    if (B === A || D === A) return null;

    // Ordena no sentido horário, começando pelo canto superior-esquerdo.
    const ordenar = (pts) => {
        const mx = (pts[0].x + pts[1].x + pts[2].x + pts[3].x) / 4;
        const my = (pts[0].y + pts[1].y + pts[2].y + pts[3].y) / 4;
        const ord = pts.slice().sort((p, q) =>
            Math.atan2(p.y - my, p.x - mx) - Math.atan2(q.y - my, q.x - mx));
        let ini = 0;
        for (let k = 1; k < 4; k++) {
            if (ord[k].x + ord[k].y < ord[ini].x + ord[ini].y) ini = k;
        }
        return [0, 1, 2, 3].map(k => ord[(ini + k) % 4]);
    };

    let cantos = ordenar([A, B, C, D]);
    cantos = ordenar(refinarCantos(cantos, silhueta, w, h));

    // O quadrilátero precisa ser convexo e coincidir com a região clara.
    let sinal = 0;
    for (let k = 0; k < 4; k++) {
        const a = cantos[k], b = cantos[(k + 1) % 4], c = cantos[(k + 2) % 4];
        const cruz = (b.x - a.x) * (c.y - b.y) - (b.y - a.y) * (c.x - b.x);
        if (cruz === 0) return null;
        if (sinal && Math.sign(cruz) !== sinal) return null;
        sinal = Math.sign(cruz);
    }
    const areaQuad = Math.abs(areaPoligono(cantos));
    const preenchimento = melhorArea / areaQuad;
    if (preenchimento < 0.82 || preenchimento > 1.12) return null;

    return {
        cantos,
        bordas,
        separacao,
        luminancia: somaLum / melhorArea,
        centro: { x: cx / w, y: cy / h }
    };
}

// -------------------------------------------------------------
// RETIFICAÇÃO (perspectiva) E REALCE DO RELEVO
// -------------------------------------------------------------

/**
 * Recorta a folha e corrige a perspectiva, devolvendo a imagem em
 * tons de cinza vista "de cima".
 *
 * cantos: superior-esquerdo, superior-direito, inferior-direito,
 * inferior-esquerdo, em pixels da imagem de origem.
 */
function retificarFolha(rgba, sw, sh, cantos) {
    const [p0, p1, p2, p3] = cantos;
    const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);
    const largura = (dist(p0, p1) + dist(p3, p2)) / 2;
    const altura = (dist(p1, p2) + dist(p0, p3)) / 2;
    const maior = Math.max(largura, altura);
    const escala = Math.min(FRAMER.outMax, Math.max(FRAMER.outMin, maior)) / maior;
    const W = Math.round(largura * escala), H = Math.round(altura * escala);

    // Homografia do quadrado unitário para o quadrilátero da folha.
    const dx1 = p1.x - p2.x, dx2 = p3.x - p2.x, sx = p0.x - p1.x + p2.x - p3.x;
    const dy1 = p1.y - p2.y, dy2 = p3.y - p2.y, sy = p0.y - p1.y + p2.y - p3.y;
    const det = dx1 * dy2 - dx2 * dy1;
    const g = det ? (sx * dy2 - dx2 * sy) / det : 0;
    const hh = det ? (dx1 * sy - sx * dy1) / det : 0;
    const a = p1.x - p0.x + g * p1.x, b = p3.x - p0.x + hh * p3.x, c = p0.x;
    const d = p1.y - p0.y + g * p1.y, e = p3.y - p0.y + hh * p3.y, f = p0.y;

    const cinza = new Float32Array(W * H);
    const lumEm = (i) => rgba[i] * 0.299 + rgba[i + 1] * 0.587 + rgba[i + 2] * 0.114;

    for (let y = 0, o = 0; y < H; y++) {
        const v = (y + 0.5) / H;
        for (let x = 0; x < W; x++, o++) {
            const u = (x + 0.5) / W;
            const den = g * u + hh * v + 1;
            let fx = (a * u + b * v + c) / den - 0.5;
            let fy = (d * u + e * v + f) / den - 0.5;
            fx = Math.min(sw - 1.001, Math.max(0, fx));
            fy = Math.min(sh - 1.001, Math.max(0, fy));
            const x0 = fx | 0, y0 = fy | 0;
            const tx = fx - x0, ty = fy - y0;
            const i = (y0 * sw + x0) * 4;
            const cima = lumEm(i) * (1 - tx) + lumEm(i + 4) * tx;
            const baixo = lumEm(i + sw * 4) * (1 - tx) + lumEm(i + sw * 4 + 4) * tx;
            cinza[o] = cima * (1 - ty) + baixo * ty;
        }
    }
    return { cinza, W, H };
}

/**
 * Realça o relevo branco sobre o papel branco: remove a iluminação
 * desigual (divide pelo fundo borrado) e amplia o contraste das
 * pequenas sombras deixadas pelos pontos.
 */
function realcarRelevo(cinza, W, H) {
    // Fundo: média em blocos, suavizada.
    const bloco = 16;
    const gw = Math.ceil(W / bloco), gh = Math.ceil(H / bloco);
    let fundo = new Float32Array(gw * gh);
    const cont = new Uint32Array(gw * gh);
    for (let y = 0, i = 0; y < H; y++) {
        const gy = (y / bloco) | 0;
        for (let x = 0; x < W; x++, i++) {
            const gi = gy * gw + ((x / bloco) | 0);
            fundo[gi] += cinza[i];
            cont[gi]++;
        }
    }
    for (let i = 0; i < fundo.length; i++) fundo[i] /= cont[i];

    for (let rodada = 0; rodada < 2; rodada++) {
        const suave = new Float32Array(gw * gh);
        for (let y = 0; y < gh; y++) {
            for (let x = 0; x < gw; x++) {
                let s = 0, c = 0;
                for (let dy = -2; dy <= 2; dy++) {
                    const yy = y + dy;
                    if (yy < 0 || yy >= gh) continue;
                    for (let dx = -2; dx <= 2; dx++) {
                        const xx = x + dx;
                        if (xx < 0 || xx >= gw) continue;
                        s += fundo[yy * gw + xx];
                        c++;
                    }
                }
                suave[y * gw + x] = s / c;
            }
        }
        fundo = suave;
    }

    // Variação relativa ao fundo (interpolado) e ganho automático.
    const rel = new Float32Array(W * H);
    let somaQ = 0;
    for (let y = 0, i = 0; y < H; y++) {
        const fy = Math.min(gh - 1, Math.max(0, (y + 0.5) / bloco - 0.5));
        const y0 = Math.min(gh - 2, fy | 0), ty = fy - y0;
        for (let x = 0; x < W; x++, i++) {
            const fx = Math.min(gw - 1, Math.max(0, (x + 0.5) / bloco - 0.5));
            const x0 = Math.min(gw - 2, fx | 0), tx = fx - x0;
            const g0 = y0 * gw + x0;
            const bg = (fundo[g0] * (1 - tx) + fundo[g0 + 1] * tx) * (1 - ty)
                + (fundo[g0 + gw] * (1 - tx) + fundo[g0 + gw + 1] * tx) * ty;
            const r = cinza[i] / Math.max(1, bg) - 1;
            rel[i] = r;
            somaQ += r * r;
        }
    }
    const rms = Math.sqrt(somaQ / (W * H));
    const ganho = Math.min(8, Math.max(1, 60 / (3 * rms * 255 + 1e-6)));

    const saida = new Uint8ClampedArray(W * H * 4);
    for (let i = 0, p = 0; i < rel.length; i++, p += 4) {
        const v = 150 + rel[i] * ganho * 255;
        saida[p] = saida[p + 1] = saida[p + 2] = v;
        saida[p + 3] = 255;
    }
    return new ImageData(saida, W, H);
}

// -------------------------------------------------------------
// ORIENTAÇÃO DO USUÁRIO
// -------------------------------------------------------------

/**
 * Decide a orientação a partir da folha detectada.
 * Returns: { chave, texto, ok } — ok = pronto para fotografar.
 */
function avaliarEnquadramento(papel, w, h) {
    if (!papel) {
        return {
            chave: 'procurando',
            texto: 'Procurando o papel. Aponte a câmera para a folha, sobre uma superfície escura.',
            ok: false
        };
    }

    const { cantos, bordas, centro } = papel;
    const tocando = Object.keys(bordas).filter(k => bordas[k] > 0.15);
    if (tocando.length >= 2) {
        return { chave: 'afastar', texto: 'Afaste o celular. O papel está saindo da imagem.', ok: false };
    }
    if (tocando.length === 1) {
        const direcao = { esquerda: 'para a esquerda', direita: 'para a direita', cima: 'para cima', baixo: 'para baixo' };
        return { chave: `cortado-${tocando[0]}`, texto: `Mova o celular ${direcao[tocando[0]]}. O papel está cortado.`, ok: false };
    }

    const xs = cantos.map(c => c.x), ys = cantos.map(c => c.y);
    const ajuste = Math.max((Math.max(...xs) - Math.min(...xs)) / w, (Math.max(...ys) - Math.min(...ys)) / h);
    if (ajuste < FRAMER.minFit) {
        return { chave: 'aproximar', texto: 'Aproxime o celular do papel.', ok: false };
    }

    const offX = centro.x - 0.5, offY = centro.y - 0.5;
    if (Math.abs(offX) > FRAMER.maxOffset || Math.abs(offY) > FRAMER.maxOffset) {
        if (Math.abs(offX) > Math.abs(offY)) {
            return offX < 0
                ? { chave: 'esquerda', texto: 'Mova o celular para a esquerda.', ok: false }
                : { chave: 'direita', texto: 'Mova o celular para a direita.', ok: false };
        }
        return offY < 0
            ? { chave: 'cima', texto: 'Mova o celular para cima.', ok: false }
            : { chave: 'baixo', texto: 'Mova o celular para baixo.', ok: false };
    }

    const lado = (i, j) => Math.hypot(cantos[i].x - cantos[j].x, cantos[i].y - cantos[j].y);
    const razao = (a, b) => Math.max(a, b) / Math.max(1, Math.min(a, b));
    if (razao(lado(0, 1), lado(3, 2)) > FRAMER.maxSkew || razao(lado(1, 2), lado(0, 3)) > FRAMER.maxSkew) {
        return { chave: 'inclinado', texto: 'Deixe o celular paralelo ao papel.', ok: false };
    }

    if (papel.luminancia < FRAMER.minLum) {
        return { chave: 'escuro', texto: 'Pouca luz. Vá para um lugar mais iluminado.', ok: false };
    }

    return { chave: 'ok', texto: 'Alinhado. Segure firme.', ok: true };
}

// -------------------------------------------------------------
// TELA DE ENQUADRAMENTO
// -------------------------------------------------------------

let enquadramento = null;

function falarOrientacao(estado, avaliacao) {
    document.getElementById('framerHint').innerText = avaliacao.texto;
    const agora = performance.now();
    const mudou = avaliacao.chave !== estado.ultimaChave;
    const espera = mudou ? FRAMER.speakGap : FRAMER.speakRepeat;
    if (agora - estado.ultimaFala < espera) return;
    estado.ultimaChave = avaliacao.chave;
    estado.ultimaFala = agora;
    speakText(avaliacao.texto);
}

function desenharEnquadramento(estado, papel, avaliacao) {
    const canvas = estado.overlay;
    const ctx = canvas.getContext('2d');
    const k = canvas.width / estado.pw;
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!papel) {
        // Moldura-guia enquanto a folha não é encontrada.
        const mx = canvas.width * 0.1, my = canvas.height * 0.1;
        ctx.setLineDash([14, 10]);
        ctx.lineWidth = 3;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.8)';
        ctx.strokeRect(mx, my, canvas.width - 2 * mx, canvas.height - 2 * my);
        ctx.setLineDash([]);
        return;
    }

    const pts = estado.cantos.map(c => ({ x: (c.x + 0.5) * k, y: (c.y + 0.5) * k }));
    const cor = avaliacao.ok ? '#00ff7f' : '#ffd400';

    // Escurece tudo fora da folha.
    ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
    ctx.beginPath();
    ctx.rect(0, 0, canvas.width, canvas.height);
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < 4; i++) ctx.lineTo(pts[i].x, pts[i].y);
    ctx.closePath();
    ctx.fill('evenodd');

    ctx.lineWidth = 4;
    ctx.strokeStyle = cor;
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    for (let i = 1; i < 4; i++) ctx.lineTo(pts[i].x, pts[i].y);
    ctx.closePath();
    ctx.stroke();

    ctx.fillStyle = cor;
    for (const p of pts) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, 9, 0, 2 * Math.PI);
        ctx.fill();
    }

    // Barra de progresso até o disparo automático.
    if (estado.estavel > 0) {
        const fracao = Math.min(1, estado.estavel / FRAMER.stableFrames);
        ctx.fillStyle = 'rgba(0, 255, 127, 0.9)';
        ctx.fillRect(0, canvas.height - 12, canvas.width * fracao, 12);
    }
}

function analisarQuadro() {
    const estado = enquadramento;
    if (!estado || estado.capturando) return;
    estado.raf = requestAnimationFrame(analisarQuadro);

    const agora = performance.now();
    const video = estado.video;
    if (agora - estado.ultimoQuadro < FRAMER.frameInterval || !video.videoWidth) return;
    estado.ultimoQuadro = agora;

    // Dimensões de análise acompanham o vídeo (muda ao girar o celular).
    const escala = FRAMER.procSize / Math.max(video.videoWidth, video.videoHeight);
    const pw = Math.round(video.videoWidth * escala), ph = Math.round(video.videoHeight * escala);
    if (pw !== estado.pw || ph !== estado.ph) {
        estado.pw = estado.proc.width = pw;
        estado.ph = estado.proc.height = ph;
        estado.overlay.width = pw * 3;
        estado.overlay.height = ph * 3;
        estado.cantos = null;
    }

    const ctx = estado.proc.getContext('2d', { willReadFrequently: true });
    ctx.drawImage(video, 0, 0, pw, ph);
    const papel = detectarPapel(ctx.getImageData(0, 0, pw, ph).data, pw, ph);
    const avaliacao = avaliarEnquadramento(papel, pw, ph);

    if (papel) {
        // Suaviza os cantos entre quadros e mede o quanto se moveram.
        let movimento = Infinity;
        if (estado.cantos) {
            movimento = 0;
            estado.cantos = estado.cantos.map((c, i) => {
                const novo = papel.cantos[i];
                movimento = Math.max(movimento, Math.hypot(novo.x - c.x, novo.y - c.y));
                return { x: c.x * 0.5 + novo.x * 0.5, y: c.y * 0.5 + novo.y * 0.5 };
            });
        } else {
            estado.cantos = papel.cantos;
        }
        const parado = movimento < FRAMER.stableShift * Math.hypot(pw, ph);
        estado.estavel = (avaliacao.ok && parado) ? estado.estavel + 1 : 0;
    } else {
        estado.cantos = null;
        estado.estavel = 0;
    }

    desenharEnquadramento(estado, papel, avaliacao);
    falarOrientacao(estado, avaliacao);

    if (estado.estavel >= FRAMER.stableFrames) {
        capturarEnquadramento();
    }
}

/** Abre a câmera traseira em tela cheia e começa a enquadrar a folha. */
async function abrirEnquadramento() {
    if (enquadramento) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        speakText('Câmera não suportada neste navegador.');
        setStatus('Câmera não suportada neste navegador.');
        return;
    }

    let stream;
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: { ideal: 'environment' },
                width: { ideal: 3840 },
                height: { ideal: 2160 }
            }
        });
    } catch (e) {
        speakText('Erro ao acessar a câmera.');
        setStatus('Erro ao acessar a câmera.');
        return;
    }

    // Foco contínuo, quando o aparelho permite.
    const trilha = stream.getVideoTracks()[0];
    trilha.applyConstraints({ advanced: [{ focusMode: 'continuous' }] }).catch(() => {});

    const video = document.getElementById('framerVideo');
    video.srcObject = stream;
    video.play().catch(() => {});

    enquadramento = {
        stream,
        video,
        overlay: document.getElementById('framerOverlay'),
        proc: document.createElement('canvas'),
        pw: 0,
        ph: 0,
        cantos: null,
        estavel: 0,
        ultimoQuadro: 0,
        ultimaChave: '',
        ultimaFala: performance.now(),
        capturando: false,
        raf: 0
    };

    document.getElementById('framer').classList.add('open');
    document.getElementById('framerHint').innerText = 'Aponte a câmera para o papel.';
    speakText('Enquadramento aberto. Aponte a câmera para o papel. A foto será tirada sozinha quando estiver alinhado.');
    // A primeira orientação espera a fala de abertura terminar.
    enquadramento.ultimaFala = performance.now() + 3500;
    enquadramento.raf = requestAnimationFrame(analisarQuadro);
}

/** Fecha a tela de enquadramento e desliga a câmera. */
function fecharEnquadramento() {
    const estado = enquadramento;
    if (!estado) return;
    enquadramento = null;
    cancelAnimationFrame(estado.raf);
    estado.stream.getTracks().forEach(t => t.stop());
    estado.video.srcObject = null;
    document.getElementById('framer').classList.remove('open');
}

/**
 * Fotografa em resolução máxima, refina os cantos da folha, corrige
 * a perspectiva, realça o relevo e envia para a detecção.
 */
function capturarEnquadramento() {
    const estado = enquadramento;
    if (!estado || estado.capturando || !estado.video.videoWidth) return;
    estado.capturando = true;
    cancelAnimationFrame(estado.raf);

    const video = estado.video;
    const k = Math.min(1, FRAMER.maxCapture / Math.max(video.videoWidth, video.videoHeight));
    const fw = Math.round(video.videoWidth * k), fh = Math.round(video.videoHeight * k);
    const cheio = document.createElement('canvas');
    cheio.width = fw;
    cheio.height = fh;
    const ctxCheio = cheio.getContext('2d', { willReadFrequently: true });
    ctxCheio.drawImage(video, 0, 0, fw, fh);

    const cantosAoVivo = estado.cantos;
    const escalaAoVivo = fw / estado.pw;
    fecharEnquadramento();
    triggerVibration([60, 40, 60]);

    // Refino dos cantos em resolução maior, na própria foto.
    const kr = Math.min(1, FRAMER.refineSize / Math.max(fw, fh));
    const rw = Math.round(fw * kr), rh = Math.round(fh * kr);
    const menor = document.createElement('canvas');
    menor.width = rw;
    menor.height = rh;
    const ctxMenor = menor.getContext('2d', { willReadFrequently: true });
    ctxMenor.drawImage(cheio, 0, 0, rw, rh);
    const refinado = detectarPapel(ctxMenor.getImageData(0, 0, rw, rh).data, rw, rh);

    let cantos = null;
    if (refinado) {
        cantos = refinado.cantos.map(c => ({ x: (c.x + 0.5) / kr, y: (c.y + 0.5) / kr }));
    } else if (cantosAoVivo) {
        cantos = cantosAoVivo.map(c => ({ x: (c.x + 0.5) * escalaAoVivo, y: (c.y + 0.5) * escalaAoVivo }));
    }

    if (!cantos) {
        // Sem folha localizada (captura manual): envia a imagem inteira.
        speakText('Papel não localizado. Enviando a imagem inteira.');
        detectFromDataUrl(cheio.toDataURL('image/jpeg', 0.92));
        return;
    }

    // Corta um pouco para dentro, para não levar o fundo junto.
    const mx = (cantos[0].x + cantos[1].x + cantos[2].x + cantos[3].x) / 4;
    const my = (cantos[0].y + cantos[1].y + cantos[2].y + cantos[3].y) / 4;
    cantos = cantos.map(c => ({
        x: c.x + (mx - c.x) * FRAMER.cropInset,
        y: c.y + (my - c.y) * FRAMER.cropInset
    }));

    const origem = ctxCheio.getImageData(0, 0, fw, fh);
    const folha = retificarFolha(origem.data, fw, fh, cantos);
    const saida = document.createElement('canvas');
    saida.width = folha.W;
    saida.height = folha.H;
    saida.getContext('2d').putImageData(realcarRelevo(folha.cinza, folha.W, folha.H), 0, 0);

    detectFromDataUrl(saida.toDataURL('image/jpeg', 0.92));
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && enquadramento) {
        fecharEnquadramento();
        speakText('Enquadramento cancelado.');
    }
});
