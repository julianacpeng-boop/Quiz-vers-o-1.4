# -*- coding: utf-8 -*-

import asyncio
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

from perguntas import QUIZZES

# =========================================================
# JUHQUIZ — MODELO FOLHA ROSA ILUSTRADA
# =========================================================
# - fundo rosa
# - folha branca
# - 5 perguntas na mesma folha
# - ilustração pequena ao lado de cada pergunta
# - aceita PNG/WEBP/JPG/JPEG
# - aceita emoji na pergunta e alternativas
# - emoji aparece na tela, mas não é narrado
# - respostas já reveladas permanecem marcadas
# - voz lê só a pergunta
# - 3, 2, 1 com bip
# - revela a correta e narra só a resposta correta
# =========================================================

VOZ = "pt-BR-AntonioNeural"
VELOCIDADE_VOZ = "+10%"

PERGUNTAS_POR_VIDEO = 5
TEMPO_ESCOLHA = 3
PAUSA_DEPOIS_RESPOSTA = 0.90
DURACAO_FINAL = 1.50

W = 1080
H = 1920
FPS = 30

AUDIO_HZ = 48000
AUDIO_CHANNELS = 1

PASTA_SAIDA = Path("output_ilustrado")
PASTA_ASSETS = Path("assets/imagens")

ROSA_FUNDO = (246, 216, 228)
PAPEL = (255, 253, 248)
TEXTO = (29, 28, 36)
ROSA = (214, 79, 98)
ROSA_ESCURO = (184, 63, 105)
ROSA_CLARO = (248, 217, 228)
LILAS_CLARO = (240, 235, 251)
LILAS = (126, 106, 169)
CINZA = (79, 74, 85)
DIVISORIA = (232, 223, 213)
VERDE = (68, 159, 96)
VERDE_CLARO = (232, 248, 237)

# None = gera TODOS os temas de perguntas.py
QUANTIDADE_VIDEOS = None


# =========================================================
# FONTES
# =========================================================

def achar_fonte(*candidatos):
    for caminho in candidatos:
        if caminho and Path(caminho).exists():
            return caminho
    return None


FONT_BOLD_PATH = achar_fonte(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)

FONT_REG_PATH = achar_fonte(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)

EMOJI_FONT_PATH = achar_fonte(
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
)


def fonte(tamanho, bold=True):
    caminho = FONT_BOLD_PATH if bold else FONT_REG_PATH
    if caminho:
        return ImageFont.truetype(caminho, int(tamanho))
    return ImageFont.load_default()


F_TITULO = fonte(49, True)
F_KICKER = fonte(22, True)
F_PERGUNTA = fonte(34, True)
F_OPCAO = fonte(28, True)
F_NUM = fonte(24, True)
F_CONTADOR = fonte(70, True)
F_CTA = fonte(50, True)
F_CTA2 = fonte(31, True)

try:
    EMOJI_FONT_109 = (
        ImageFont.truetype(EMOJI_FONT_PATH, 109)
        if EMOJI_FONT_PATH
        else None
    )
except Exception:
    EMOJI_FONT_109 = None


# =========================================================
# EMOJI / TEXTO MISTO
# =========================================================

CACHE_EMOJI = {}


def eh_emoji_base(ch):
    cp = ord(ch)
    return (
        0x1F000 <= cp <= 0x1FAFF
        or 0x2600 <= cp <= 0x27BF
        or 0x2300 <= cp <= 0x23FF
        or 0x2B00 <= cp <= 0x2BFF
        or 0x1F1E6 <= cp <= 0x1F1FF
        or cp in (0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139)
    )


def separar_segmentos_emoji(texto):
    texto = str(texto)
    segmentos = []
    normal = []
    i = 0

    def flush_normal():
        nonlocal normal
        if normal:
            segmentos.append(("texto", "".join(normal)))
            normal = []

    while i < len(texto):
        ch = texto[i]

        if eh_emoji_base(ch):
            flush_normal()
            cluster = ch
            i += 1

            # bandeiras
            if (
                0x1F1E6 <= ord(ch) <= 0x1F1FF
                and i < len(texto)
                and 0x1F1E6 <= ord(texto[i]) <= 0x1F1FF
            ):
                cluster += texto[i]
                i += 1

            while i < len(texto):
                cp = ord(texto[i])

                # VS, tons de pele, keycap
                if cp in (0xFE0E, 0xFE0F, 0x20E3) or 0x1F3FB <= cp <= 0x1F3FF:
                    cluster += texto[i]
                    i += 1
                    continue

                # ZWJ
                if cp == 0x200D and i + 1 < len(texto):
                    cluster += texto[i]
                    cluster += texto[i + 1]
                    i += 2

                    while i < len(texto):
                        cp2 = ord(texto[i])
                        if cp2 in (0xFE0E, 0xFE0F, 0x20E3) or 0x1F3FB <= cp2 <= 0x1F3FF:
                            cluster += texto[i]
                            i += 1
                        else:
                            break
                    continue

                break

            segmentos.append(("emoji", cluster))
        else:
            normal.append(ch)
            i += 1

    flush_normal()
    return segmentos


def remover_emojis_tts(texto):
    partes = [
        trecho
        for tipo, trecho in separar_segmentos_emoji(texto)
        if tipo == "texto"
    ]
    limpo = re.sub(r"\s+", " ", "".join(partes)).strip()
    return limpo if limpo else str(texto).strip()


def renderizar_emoji(cluster, tamanho):
    if EMOJI_FONT_109 is None:
        return None

    chave = (cluster, int(tamanho))
    if chave in CACHE_EMOJI:
        return CACHE_EMOJI[chave].copy()

    temp = Image.new("RGBA", (190, 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(temp)

    try:
        d.text(
            (8, 8),
            cluster,
            font=EMOJI_FONT_109,
            embedded_color=True
        )
    except Exception:
        return None

    bbox = temp.getbbox()
    if not bbox:
        return None

    temp = temp.crop(bbox)

    alvo = max(12, int(tamanho))
    escala = alvo / max(1, temp.height)
    nw = max(1, int(temp.width * escala))

    temp = temp.resize(
        (nw, alvo),
        Image.Resampling.LANCZOS
    )

    CACHE_EMOJI[chave] = temp.copy()
    return temp


def medir_texto_misto(draw, texto, font):
    tamanho = int(getattr(font, "size", 30))
    largura = 0

    for tipo, trecho in separar_segmentos_emoji(texto):
        if tipo == "texto":
            if trecho:
                bb = draw.textbbox((0, 0), trecho, font=font)
                largura += bb[2] - bb[0]
        else:
            em = renderizar_emoji(trecho, tamanho)
            if em is not None:
                largura += em.width + max(2, tamanho // 10)
            else:
                # fallback: espaço aproximado
                largura += tamanho

    return largura


def desenhar_texto_misto(img, draw, x, y, texto, font, fill):
    tamanho = int(getattr(font, "size", 30))
    cx = float(x)

    for tipo, trecho in separar_segmentos_emoji(texto):
        if tipo == "texto":
            if trecho:
                draw.text((cx, y), trecho, font=font, fill=fill)
                bb = draw.textbbox((0, 0), trecho, font=font)
                cx += bb[2] - bb[0]
        else:
            em = renderizar_emoji(trecho, tamanho)
            if em is not None:
                yy = int(y - max(0, (em.height - tamanho) * 0.12))
                img.alpha_composite(em, (int(cx), yy))
                cx += em.width + max(2, tamanho // 10)
            else:
                cx += tamanho

    return cx


def wrap_text_misto(draw, texto, font, max_width, max_lines=3):
    palavras = str(texto).split()
    linhas = []
    atual = ""

    for palavra in palavras:
        teste = palavra if not atual else atual + " " + palavra

        if medir_texto_misto(draw, teste, font) <= max_width:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra

    if atual:
        linhas.append(atual)

    if len(linhas) > max_lines:
        linhas = linhas[:max_lines]
        ultima = linhas[-1]

        while (
            medir_texto_misto(draw, ultima + "…", font) > max_width
            and len(ultima) > 3
        ):
            ultima = ultima[:-1]

        linhas[-1] = ultima.rstrip() + "…"

    return linhas


def desenhar_linhas_mistas(
    img,
    draw,
    x,
    y,
    linhas,
    font,
    fill,
    espacamento=8
):
    cursor = y

    for linha in linhas:
        bb = draw.textbbox((0, 0), "Ag", font=font)
        h = bb[3] - bb[1]

        desenhar_texto_misto(
            img,
            draw,
            x,
            cursor,
            linha,
            font,
            fill
        )

        cursor += h + espacamento

    return cursor


# =========================================================
# UTILITÁRIOS
# =========================================================

def slugify(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(
        c for c in texto
        if not unicodedata.combining(c)
    )
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")


def rodar(cmd, quiet=False):
    if not quiet:
        print(" ".join(map(str, cmd)), flush=True)

    subprocess.run(
        cmd,
        check=True
    )


def duracao_audio(caminho):
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(caminho)
        ],
        capture_output=True,
        text=True,
        check=True
    )

    return max(
        0.10,
        float(p.stdout.strip())
    )


def caminho_abs(p):
    return str(
        Path(p).resolve()
    ).replace("\\", "/")


def escapar_concat(p):
    return caminho_abs(p).replace(
        "'",
        "'\\''"
    )


# =========================================================
# IMAGENS
# =========================================================

CACHE_IMG = {}


def buscar_ilustracao(tema, indice, pergunta):
    # 1) Caminho explícito no perguntas.py
    manual = pergunta.get("ilustracao")

    if manual:
        p = Path(manual)

        if p.exists():
            return p

        print(
            f"⚠️ Imagem informada não encontrada: {p}",
            flush=True
        )

    # 2) Busca automática por pasta do tema
    pasta = PASTA_ASSETS / slugify(tema)
    base = f"{indice + 1:02d}"

    for ext in (
        ".png",
        ".webp",
        ".jpg",
        ".jpeg"
    ):
        # 01.png
        p = pasta / f"{base}{ext}"
        if p.exists():
            return p

        # 01_nome.png
        encontrados = sorted(
            pasta.glob(
                f"{base}_*{ext}"
            )
        )

        if encontrados:
            return encontrados[0]

    return None


def carregar_ilustracao(
    caminho,
    max_w=165,
    max_h=155
):
    if caminho is None:
        return None

    chave = (
        str(caminho),
        int(max_w),
        int(max_h)
    )

    if chave in CACHE_IMG:
        return CACHE_IMG[chave].copy()

    try:
        arte = Image.open(
            caminho
        ).convert("RGBA")

        arte.thumbnail(
            (int(max_w), int(max_h)),
            Image.Resampling.LANCZOS
        )

        CACHE_IMG[chave] = arte.copy()
        return arte

    except Exception as e:
        print(
            f"⚠️ Não consegui abrir {caminho}: {e}",
            flush=True
        )
        return None


# =========================================================
# ÁUDIO
# =========================================================

async def tts_mp3(texto, saida):
    saida = Path(saida)
    saida.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    texto_tts = remover_emojis_tts(
        texto
    )

    ultimo_erro = None

    for tentativa in range(1, 4):
        try:
            communicate = edge_tts.Communicate(
                text=texto_tts,
                voice=VOZ,
                rate=VELOCIDADE_VOZ
            )

            await communicate.save(
                str(saida)
            )

            return

        except Exception as e:
            ultimo_erro = e

            print(
                f"⚠️ TTS tentativa {tentativa}/3: {e}",
                flush=True
            )

            await asyncio.sleep(
                2 * tentativa
            )

    raise RuntimeError(
        f"Falha no TTS: {ultimo_erro}"
    )


def mp3_para_wav(mp3, wav):
    rodar(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(mp3),
            "-ar",
            str(AUDIO_HZ),
            "-ac",
            str(AUDIO_CHANNELS),
            "-c:a",
            "pcm_s16le",
            str(wav)
        ],
        quiet=True
    )


def criar_beep_wav(
    caminho,
    frequencia=950
):
    rodar(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequencia}:duration=0.14",
            "-af",
            "volume=0.55,apad=pad_dur=1",
            "-t",
            "1.0",
            "-ar",
            str(AUDIO_HZ),
            "-ac",
            str(AUDIO_CHANNELS),
            "-c:a",
            "pcm_s16le",
            str(caminho)
        ],
        quiet=True
    )


def criar_silencio_wav(
    caminho,
    duracao
):
    rodar(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={AUDIO_HZ}:cl=mono",
            "-t",
            f"{duracao:.3f}",
            "-c:a",
            "pcm_s16le",
            str(caminho)
        ],
        quiet=True
    )


def adicionar_pausa_wav(
    entrada,
    saida,
    pausa
):
    rodar(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(entrada),
            "-af",
            f"apad=pad_dur={pausa}",
            "-ar",
            str(AUDIO_HZ),
            "-ac",
            str(AUDIO_CHANNELS),
            "-c:a",
            "pcm_s16le",
            str(saida)
        ],
        quiet=True
    )


def concatenar_audios(
    wavs,
    saida_m4a,
    temp_dir
):
    lista = temp_dir / "audio_concat.txt"

    with lista.open(
        "w",
        encoding="utf-8"
    ) as f:
        for wav in wavs:
            f.write(
                f"file '{escapar_concat(wav)}'\n"
            )

    rodar(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lista),
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            str(AUDIO_HZ),
            "-ac",
            str(AUDIO_CHANNELS),
            str(saida_m4a)
        ],
        quiet=True
    )


# =========================================================
# DESENHO
# =========================================================

def rounded_top_rectangle(
    draw,
    box,
    radius,
    fill
):
    x0, y0, x1, y1 = box

    draw.rectangle(
        (x0, y0 + radius, x1, y1),
        fill=fill
    )

    draw.rectangle(
        (x0 + radius, y0, x1 - radius, y1),
        fill=fill
    )

    draw.pieslice(
        (
            x0,
            y0,
            x0 + 2 * radius,
            y0 + 2 * radius
        ),
        180,
        270,
        fill=fill
    )

    draw.pieslice(
        (
            x1 - 2 * radius,
            y0,
            x1,
            y0 + 2 * radius
        ),
        270,
        360,
        fill=fill
    )


def render_frame(
    tema,
    perguntas,
    pergunta_atual,
    fase,
    contador=None
):
    # RGBA para permitir emoji colorido e PNG transparente
    img = Image.new(
        "RGBA",
        (W, H),
        ROSA_FUNDO + (255,)
    )

    draw = ImageDraw.Draw(img)

    # Fundo rosa superior
    draw.rectangle(
        (0, 0, W, 170),
        fill=ROSA_FUNDO
    )

    # Folha branca
    rounded_top_rectangle(
        draw,
        (30, 145, W - 30, H),
        48,
        PAPEL
    )

    # Cabeçalho
    kicker = "JUHQUIZ • DESAFIO VISUAL"

    kb = draw.textbbox(
        (0, 0),
        kicker,
        font=F_KICKER
    )

    kw = kb[2] - kb[0]
    kx = (W - kw) // 2

    draw.rounded_rectangle(
        (
            kx - 18,
            182,
            kx + kw + 18,
            224
        ),
        radius=21,
        fill=LILAS_CLARO
    )

    draw.text(
        (kx, 190),
        kicker,
        font=F_KICKER,
        fill=LILAS
    )

    tema_txt = str(tema).upper()

    tb = draw.textbbox(
        (0, 0),
        tema_txt,
        font=F_TITULO
    )

    tw = tb[2] - tb[0]

    draw.text(
        (
            (W - tw) // 2,
            238
        ),
        tema_txt,
        font=F_TITULO,
        fill=ROSA
    )

    draw.rounded_rectangle(
        (
            250,
            306,
            W - 250,
            312
        ),
        radius=3,
        fill=(52, 49, 58)
    )

    # Contagem
    if (
        fase == "contagem"
        and contador is not None
    ):
        cx, cy = W - 110, 79

        draw.ellipse(
            (
                cx - 55,
                cy - 55,
                cx + 55,
                cy + 55
            ),
            fill=(255, 255, 255)
        )

        texto = str(contador)

        bb = draw.textbbox(
            (0, 0),
            texto,
            font=F_CONTADOR
        )

        draw.text(
            (
                cx - (bb[2] - bb[0]) // 2,
                cy - (bb[3] - bb[1]) // 2 - 4
            ),
            texto,
            font=F_CONTADOR,
            fill=ROSA_ESCURO
        )

    start_y = 338
    bloco_h = 302

    # Todas as anteriores já devem continuar marcadas.
    respondidas = set(
        range(pergunta_atual)
    )

    # Durante a própria resposta, marca também a atual.
    if fase == "resposta":
        respondidas.add(
            pergunta_atual
        )

    for i, q in enumerate(perguntas):
        y0 = start_y + i * bloco_h
        y1 = y0 + bloco_h - 8
        atual = i == pergunta_atual
        ja_respondida = i in respondidas

        # Realce suave da pergunta atualmente em jogo
        if atual:
            draw.rounded_rectangle(
                (
                    55,
                    y0 - 6,
                    W - 55,
                    y1
                ),
                radius=26,
                fill=(255, 247, 250)
            )

        # Número
        cx, cy = 94, y0 + 34

        cor_num = (
            ROSA_ESCURO
            if atual
            else (190, 111, 142)
        )

        draw.ellipse(
            (
                cx - 25,
                cy - 25,
                cx + 25,
                cy + 25
            ),
            fill=ROSA_CLARO
        )

        num = str(i + 1)

        nb = draw.textbbox(
            (0, 0),
            num,
            font=F_NUM
        )

        draw.text(
            (
                cx - (nb[2] - nb[0]) // 2,
                cy - (nb[3] - nb[1]) // 2 - 2
            ),
            num,
            font=F_NUM,
            fill=cor_num
        )

        # Pergunta
        qx = 140
        qy = y0 + 7

        linhas = wrap_text_misto(
            draw,
            q["pergunta"],
            F_PERGUNTA,
            675,
            max_lines=2
        )

        # Marca-texto rosa somente na pergunta atual
        if (
            atual
            and fase in (
                "pergunta",
                "contagem",
                "resposta"
            )
        ):
            cursor = qy + 12

            for linha in linhas:
                ww = medir_texto_misto(
                    draw,
                    linha,
                    F_PERGUNTA
                )

                bb = draw.textbbox(
                    (0, 0),
                    "Ag",
                    font=F_PERGUNTA
                )

                hh = bb[3] - bb[1]

                draw.rounded_rectangle(
                    (
                        qx - 7,
                        cursor + hh - 9,
                        qx + ww + 7,
                        cursor + hh + 9
                    ),
                    radius=7,
                    fill=(248, 212, 226)
                )

                cursor += hh + 7

        fim_q = desenhar_linhas_mistas(
            img,
            draw,
            qx,
            qy,
            linhas,
            F_PERGUNTA,
            TEXTO,
            7
        )

        # Ilustração sem círculo e sem caixa
        ilustracao = buscar_ilustracao(
            tema,
            i,
            q
        )

        arte = carregar_ilustracao(
            ilustracao,
            165,
            155
        )

        if arte is not None:
            ax = (
                860
                + (165 - arte.width) // 2
            )

            ay = (
                y0
                + 17
                + (155 - arte.height) // 2
            )

            img.alpha_composite(
                arte,
                (int(ax), int(ay))
            )

        # Alternativas
        op_y = max(
            y0 + 100,
            fim_q + 18
        )

        correta = int(
            q["correta"]
        )

        for j, alt in enumerate(
            q["alternativas"]
        ):
            oy = op_y + j * 51
            box_x = 145

            esta_correta_revelada = (
                ja_respondida
                and j == correta
            )

            if esta_correta_revelada:
                draw.rounded_rectangle(
                    (
                        132,
                        oy - 7,
                        765,
                        oy + 39
                    ),
                    radius=14,
                    fill=VERDE_CLARO
                )

                draw.rounded_rectangle(
                    (
                        box_x,
                        oy,
                        box_x + 30,
                        oy + 30
                    ),
                    radius=7,
                    fill=VERDE
                )

                # check
                draw.line(
                    (
                        box_x + 7,
                        oy + 16,
                        box_x + 13,
                        oy + 23
                    ),
                    fill=(255, 255, 255),
                    width=4
                )

                draw.line(
                    (
                        box_x + 13,
                        oy + 23,
                        box_x + 25,
                        oy + 8
                    ),
                    fill=(255, 255, 255),
                    width=4
                )

                cor_alt = (
                    37,
                    106,
                    58
                )

            else:
                draw.rounded_rectangle(
                    (
                        box_x,
                        oy,
                        box_x + 30,
                        oy + 30
                    ),
                    radius=7,
                    fill=(255, 255, 255),
                    outline=CINZA,
                    width=2
                )

                cor_alt = TEXTO

            # Alternativa aceita emoji
            desenhar_texto_misto(
                img,
                draw,
                box_x + 47,
                oy - 1,
                str(alt),
                F_OPCAO,
                cor_alt
            )

        # Divisória
        if i < len(perguntas) - 1:
            yy = y1 + 2
            x = 95

            while x < W - 95:
                draw.line(
                    (
                        x,
                        yy,
                        min(
                            x + 15,
                            W - 95
                        ),
                        yy
                    ),
                    fill=DIVISORIA,
                    width=2
                )

                x += 27

    return img.convert("RGB")


def render_final(tema):
    img = Image.new(
        "RGBA",
        (W, H),
        ROSA_FUNDO + (255,)
    )

    draw = ImageDraw.Draw(img)

    rounded_top_rectangle(
        draw,
        (
            45,
            300,
            W - 45,
            H
        ),
        56,
        PAPEL
    )

    titulo = "JUHQUIZ"

    bb = draw.textbbox(
        (0, 0),
        titulo,
        font=F_TITULO
    )

    draw.text(
        (
            (W - (bb[2] - bb[0])) // 2,
            490
        ),
        titulo,
        font=F_TITULO,
        fill=ROSA
    )

    cta = "QUANTAS VOCÊ ACERTOU?"

    bb = draw.textbbox(
        (0, 0),
        cta,
        font=F_CTA
    )

    draw.text(
        (
            (W - (bb[2] - bb[0])) // 2,
            760
        ),
        cta,
        font=F_CTA,
        fill=TEXTO
    )

    cta2 = "Comenta sua pontuação 👇"
    largura = medir_texto_misto(
        draw,
        cta2,
        F_CTA2
    )

    desenhar_texto_misto(
        img,
        draw,
        (W - largura) / 2,
        880,
        cta2,
        F_CTA2,
        ROSA_ESCURO
    )

    tema2 = str(tema).upper()

    bb = draw.textbbox(
        (0, 0),
        tema2,
        font=F_KICKER
    )

    tw = bb[2] - bb[0]

    draw.rounded_rectangle(
        (
            (W - tw) // 2 - 24,
            1050,
            (W + tw) // 2 + 24,
            1104
        ),
        radius=27,
        fill=LILAS_CLARO
    )

    draw.text(
        (
            (W - tw) // 2,
            1064
        ),
        tema2,
        font=F_KICKER,
        fill=LILAS
    )

    return img.convert("RGB")


# =========================================================
# MONTAGEM
# =========================================================

def criar_video_slideshow(
    frames_duracoes,
    saida_mp4,
    temp_dir
):
    lista = temp_dir / "frames_concat.txt"

    with lista.open(
        "w",
        encoding="utf-8"
    ) as f:
        for frame, dur in frames_duracoes:
            f.write(
                f"file '{escapar_concat(frame)}'\n"
            )
            f.write(
                f"duration {dur:.6f}\n"
            )

        f.write(
            f"file '{escapar_concat(frames_duracoes[-1][0])}'\n"
        )

    rodar(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lista),
            "-vf",
            f"fps={FPS},format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-movflags",
            "+faststart",
            "-an",
            str(saida_mp4)
        ],
        quiet=True
    )


def juntar_video_audio(
    video_sem_audio,
    audio,
    saida
):
    rodar(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(video_sem_audio),
            "-i",
            str(audio),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(saida)
        ],
        quiet=True
    )


# =========================================================
# VALIDAÇÃO
# =========================================================

def validar():
    if (
        not isinstance(QUIZZES, dict)
        or not QUIZZES
    ):
        raise ValueError(
            "QUIZZES está vazio."
        )

    for tema, perguntas in QUIZZES.items():
        if len(perguntas) != PERGUNTAS_POR_VIDEO:
            raise ValueError(
                f"Tema '{tema}' precisa ter exatamente "
                f"{PERGUNTAS_POR_VIDEO} perguntas."
            )

        for n, q in enumerate(
            perguntas,
            1
        ):
            if (
                "pergunta" not in q
                or "alternativas" not in q
                or "correta" not in q
            ):
                raise ValueError(
                    f"{tema} / pergunta {n}: "
                    "campos obrigatórios ausentes."
                )

            if len(q["alternativas"]) != 3:
                raise ValueError(
                    f"{tema} / pergunta {n}: "
                    "precisa ter 3 alternativas."
                )

            if int(q["correta"]) not in (
                0,
                1,
                2
            ):
                raise ValueError(
                    f"{tema} / pergunta {n}: "
                    "'correta' deve ser 0, 1 ou 2."
                )


# =========================================================
# GERAÇÃO
# =========================================================

async def gerar_um_video(
    video_num,
    total_videos,
    tema,
    perguntas,
    pasta_saida
):
    slug = slugify(tema)

    temp = (
        Path("_temp_ilustrado")
        / f"{video_num:02d}_{slug}"
    )

    if temp.exists():
        shutil.rmtree(temp)

    temp.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        f"\n🎬 {video_num:02d}/{total_videos:02d} — {tema}",
        flush=True
    )

    frames_duracoes = []
    audios = []

    beep_normal = temp / "beep_normal.wav"
    beep_final = temp / "beep_final.wav"

    criar_beep_wav(
        beep_normal,
        950
    )

    criar_beep_wav(
        beep_final,
        1250
    )

    for i, q in enumerate(perguntas):
        print(
            f"   📝 Pergunta {i + 1}/5",
            flush=True
        )

        # Pergunta
        q_mp3 = temp / f"q_{i + 1:02d}.mp3"
        q_wav = temp / f"q_{i + 1:02d}.wav"

        await tts_mp3(
            q["pergunta"],
            q_mp3
        )

        mp3_para_wav(
            q_mp3,
            q_wav
        )

        dq = duracao_audio(
            q_wav
        )

        # Resposta correta
        resposta = q["alternativas"][
            int(q["correta"])
        ]

        a_mp3 = temp / f"a_{i + 1:02d}.mp3"
        a_wav0 = temp / f"a_{i + 1:02d}_raw.wav"
        a_wav = temp / f"a_{i + 1:02d}.wav"

        await tts_mp3(
            resposta,
            a_mp3
        )

        mp3_para_wav(
            a_mp3,
            a_wav0
        )

        adicionar_pausa_wav(
            a_wav0,
            a_wav,
            PAUSA_DEPOIS_RESPOSTA
        )

        da = duracao_audio(
            a_wav
        )

        # Leitura da pergunta.
        # As respostas anteriores continuam marcadas.
        f_q = temp / f"frame_{i + 1:02d}_q.png"

        render_frame(
            tema,
            perguntas,
            i,
            "pergunta"
        ).save(
            f_q,
            quality=95
        )

        frames_duracoes.append(
            (f_q, dq)
        )

        audios.append(
            q_wav
        )

        # 3, 2, 1
        for numero in range(
            TEMPO_ESCOLHA,
            0,
            -1
        ):
            f_c = (
                temp
                / f"frame_{i + 1:02d}_c{numero}.png"
            )

            render_frame(
                tema,
                perguntas,
                i,
                "contagem",
                numero
            ).save(
                f_c,
                quality=95
            )

            frames_duracoes.append(
                (f_c, 1.0)
            )

            audios.append(
                beep_final
                if numero == 1
                else beep_normal
            )

        # Resposta correta fica marcada durante
        # toda a fala + pausa.
        f_a = (
            temp
            / f"frame_{i + 1:02d}_a.png"
        )

        render_frame(
            tema,
            perguntas,
            i,
            "resposta"
        ).save(
            f_a,
            quality=95
        )

        frames_duracoes.append(
            (f_a, da)
        )

        audios.append(
            a_wav
        )

    # Final
    final_png = (
        temp
        / "frame_final.png"
    )

    render_final(
        tema
    ).save(
        final_png,
        quality=95
    )

    frames_duracoes.append(
        (
            final_png,
            DURACAO_FINAL
        )
    )

    final_wav = (
        temp
        / "final_silencio.wav"
    )

    criar_silencio_wav(
        final_wav,
        DURACAO_FINAL
    )

    audios.append(
        final_wav
    )

    video_sem_audio = (
        temp
        / "video_sem_audio.mp4"
    )

    audio_final = (
        temp
        / "audio_final.m4a"
    )

    print(
        "   🎞️ Montando vídeo...",
        flush=True
    )

    criar_video_slideshow(
        frames_duracoes,
        video_sem_audio,
        temp
    )

    print(
        "   🔊 Montando áudio...",
        flush=True
    )

    concatenar_audios(
        audios,
        audio_final,
        temp
    )

    saida = (
        pasta_saida
        / f"{video_num:02d}_{slug}.mp4"
    )

    juntar_video_audio(
        video_sem_audio,
        audio_final,
        saida
    )

    print(
        f"   ✅ {saida}",
        flush=True
    )

    shutil.rmtree(
        temp,
        ignore_errors=True
    )


async def main():
    validar()

    temas = list(
        QUIZZES.keys()
    )

    if QUANTIDADE_VIDEOS is not None:
        temas = temas[
            :QUANTIDADE_VIDEOS
        ]

    from datetime import date

    pasta_saida = (
        PASTA_SAIDA
        / date.today().isoformat()
    )

    pasta_saida.mkdir(
        parents=True,
        exist_ok=True
    )

    total_videos = len(temas)

    print(
        "🎀 JuhQuiz — Folha Rosa Ilustrada",
        flush=True
    )

    print(
        f"📚 Temas: {total_videos}",
        flush=True
    )

    print(
        "🖼️ Imagens: caminho do campo 'ilustracao' "
        "ou assets/imagens/<tema>/01.png",
        flush=True
    )

    print(
        "😀 Emojis: ativados",
        flush=True
    )

    print(
        "✅ Respostas anteriores permanecem marcadas",
        flush=True
    )

    for idx, tema in enumerate(
        temas,
        1
    ):
        await gerar_um_video(
            idx,
            total_videos,
            tema,
            QUIZZES[tema],
            pasta_saida
        )

    print(
        "\n🎉 TODOS OS VÍDEOS FORAM GERADOS!",
        flush=True
    )

    print(
        f"📁 {pasta_saida}",
        flush=True
    )


if __name__ == "__main__":
    asyncio.run(main())
