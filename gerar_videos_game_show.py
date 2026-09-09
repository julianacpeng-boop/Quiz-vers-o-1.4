# -*- coding: utf-8 -*-
"""
JUH QUIZ — GAME SHOW BASE

Arquivo-base necessário para:
    gerar_videos_game_show_ilustrado.py

Ele usa o banco de perguntas de:
    perguntas.py

IMPORTANTE:
- Não precisa colocar as perguntas dentro deste arquivo.
- O número de vídeos é definido automaticamente pela quantidade de temas em perguntas.py.
- O arquivo ilustrado substitui o render_frame deste módulo em tempo de execução,
  acrescentando imagens, emojis e mantendo a resposta marcada.
"""

import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from perguntas import QUIZZES


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PERGUNTAS_POR_VIDEO = 5
TEMPO_ESCOLHA = 3

VOZ = "pt-BR-AntonioNeural"
VELOCIDADE_VOZ = "+10%"

W = 1080
H = 1920
FPS = 30

AUDIO_HZ = 48000
AUDIO_CHANNELS = 2
PAUSA_DEPOIS_RESPOSTA = 0.55

FUSO = ZoneInfo("America/Fortaleza")
DATA_DO_DIA = datetime.now(FUSO).strftime("%Y-%m-%d")

PASTA_RAIZ = Path("output_game_show")
PASTA_TMP = Path("_tmp_juhquiz_game_show")
PASTA_SAIDA = PASTA_RAIZ / DATA_DO_DIA

# Usa automaticamente todos os temas do perguntas.py
QUANTIDADE_VIDEOS = len(QUIZZES)


# ============================================================
# UTILITÁRIOS
# ============================================================

def slug(texto):
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = texto.encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_").lower()
    return texto or "video"


def executar(cmd):
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if p.returncode != 0:
        print(p.stderr[-5000:], flush=True)
        raise RuntimeError("Comando retornou erro.")

    return p


def achar_fonte(*candidatos):
    for caminho in candidatos:
        if caminho and os.path.exists(caminho):
            return caminho
    return None


FONT_BOLD = achar_fonte(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)

FONT_REG = achar_fonte(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
)


def fonte(tamanho, bold=True):
    caminho = FONT_BOLD if bold else FONT_REG

    if caminho:
        return ImageFont.truetype(caminho, int(tamanho))

    return ImageFont.load_default()


def texto_central(draw, y, texto, fnt, fill, x0=0, x1=W):
    bb = draw.textbbox((0, 0), str(texto), font=fnt)
    tw = bb[2] - bb[0]
    x = x0 + ((x1 - x0) - tw) / 2
    draw.text((x, y), str(texto), font=fnt, fill=fill)


def wrap_text(draw, texto, fnt, max_width):
    palavras = str(texto).split()
    linhas = []
    atual = ""

    for palavra in palavras:
        teste = (atual + " " + palavra).strip()
        bb = draw.textbbox((0, 0), teste, font=fnt)

        if (bb[2] - bb[0]) <= max_width:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra

    if atual:
        linhas.append(atual)

    return linhas


def desenhar_multilinha_central(
    draw,
    texto,
    fnt,
    y,
    max_width,
    fill,
    line_gap=10
):
    linhas = wrap_text(draw, texto, fnt, max_width)
    bb = draw.textbbox((0, 0), "Ag", font=fnt)
    line_h = bb[3] - bb[1]
    yy = y

    for linha in linhas:
        texto_central(
            draw,
            yy,
            linha,
            fnt,
            fill,
            100,
            W - 100
        )
        yy += line_h + line_gap

    return yy


# ============================================================
# CORES DO GAME SHOW
# ============================================================

PURPLE = (58, 32, 92)
PINK = (255, 55, 122)
YELLOW = (255, 207, 25)
CORAL = (255, 94, 66)
CREAM = (255, 249, 239)
GREEN = (202, 255, 173)
GREEN_DARK = (19, 175, 113)
TEAL = (18, 188, 162)
LAVENDER = (110, 75, 215)


# ============================================================
# RENDER BASE
# O arquivo ilustrado substitui esta função automaticamente.
# ============================================================

def render_frame(tema, pergunta, numero, estado, timer=None):
    img = Image.new("RGB", (W, H), CORAL)
    draw = ImageDraw.Draw(img)

    limite_topo = int(H * 0.31)
    draw.rectangle([0, 0, W, limite_topo], fill=YELLOW)
    draw.rectangle([0, limite_topo, W, H], fill=CORAL)

    # Raios decorativos
    import math

    cx, cy = W // 2, 170
    raio = 730

    for i in range(0, 360, 24):
        a1 = math.radians(i)
        a2 = math.radians(i + 10)

        pts = [
            (cx, cy),
            (
                cx + raio * math.cos(a1),
                cy + raio * math.sin(a1)
            ),
            (
                cx + raio * math.cos(a2),
                cy + raio * math.sin(a2)
            ),
        ]

        draw.polygon(pts, fill=(255, 221, 78))

    # Logo
    logo_box = [280, 60, 800, 180]
    shadow = [
        logo_box[0] + 16,
        logo_box[1] + 18,
        logo_box[2] + 16,
        logo_box[3] + 18
    ]

    draw.rounded_rectangle(
        shadow,
        radius=32,
        fill=PINK
    )

    draw.rounded_rectangle(
        logo_box,
        radius=32,
        fill=PURPLE,
        outline=(255, 255, 255),
        width=12
    )

    texto_central(
        draw,
        86,
        "JUH QUIZ",
        fonte(54, True),
        (255, 255, 255)
    )

    # Número
    draw.rounded_rectangle(
        [875, 62, 1018, 132],
        radius=22,
        fill=(255, 255, 255)
    )

    texto_central(
        draw,
        78,
        f"{numero}/5",
        fonte(34, True),
        PURPLE,
        875,
        1018
    )

    # Tema
    tema_txt = f"TEMA: {tema.upper()}"
    tema_font = fonte(27, True)

    bb = draw.textbbox((0, 0), tema_txt, font=tema_font)
    tw = bb[2] - bb[0]

    tema_x0 = (W - tw) / 2 - 28
    tema_x1 = (W + tw) / 2 + 28

    draw.rounded_rectangle(
        [tema_x0, 210, tema_x1, 272],
        radius=30,
        fill=CREAM,
        outline=PURPLE,
        width=4
    )

    texto_central(
        draw,
        226,
        tema_txt,
        tema_font,
        PURPLE
    )

    # Card
    card = [55, 340, W - 55, 1570]
    shadow_card = [
        card[0] + 20,
        card[1] + 22,
        card[2] + 20,
        card[3] + 22
    ]

    draw.rounded_rectangle(
        shadow_card,
        radius=50,
        fill=(120, 62, 88)
    )

    draw.rounded_rectangle(
        card,
        radius=50,
        fill=CREAM,
        outline=PURPLE,
        width=10
    )

    # Chamada
    chamada = "DESAFIO RELÂMPAGO"
    f_chamada = fonte(27, True)

    bb = draw.textbbox(
        (0, 0),
        chamada,
        font=f_chamada
    )
    cw = bb[2] - bb[0]

    draw.rounded_rectangle(
        [
            W / 2 - cw / 2 - 34,
            390,
            W / 2 + cw / 2 + 34,
            456
        ],
        radius=32,
        fill=PINK
    )

    texto_central(
        draw,
        408,
        chamada,
        f_chamada,
        (255, 255, 255)
    )

    # Pergunta
    f_q = fonte(54, True)

    y_after = desenhar_multilinha_central(
        draw,
        pergunta["pergunta"],
        f_q,
        505,
        800,
        (38, 32, 63),
        line_gap=10
    )

    # Cronômetro
    timer_y = max(740, y_after + 30)

    timer_box = [
        W / 2 - 72,
        timer_y,
        W / 2 + 72,
        timer_y + 118
    ]

    draw.rounded_rectangle(
        [
            timer_box[0] + 10,
            timer_box[1] + 10,
            timer_box[2] + 10,
            timer_box[3] + 10
        ],
        radius=28,
        fill=PURPLE
    )

    draw.rounded_rectangle(
        timer_box,
        radius=28,
        fill=YELLOW,
        outline=PURPLE,
        width=7
    )

    if estado == "reading":
        timer_txt = "..."
        feedback = "OUÇA A PERGUNTA"
    elif estado == "countdown":
        timer_txt = str(timer)
        feedback = "AGORA RESPONDA!"
    else:
        timer_txt = "✓"
        feedback = "ACERTOU?"

    texto_central(
        draw,
        timer_y + 24,
        timer_txt,
        fonte(55, True),
        PURPLE,
        timer_box[0],
        timer_box[2]
    )

    # Alternativas
    alt_top = timer_y + 155

    letras = ["A", "B", "C"]
    label_colors = [LAVENDER, PINK, TEAL]

    for j, alt in enumerate(pergunta["alternativas"]):
        yy = alt_top + j * 130
        correta = j == int(pergunta["correta"])

        if estado == "answer" and correta:
            bg = GREEN
            label_bg = GREEN_DARK
            texto_cor = (38, 32, 63)

        elif estado == "answer" and not correta:
            bg = (238, 232, 226)
            label_bg = (170, 160, 168)
            texto_cor = (130, 125, 128)

        else:
            bg = (255, 255, 255)
            label_bg = label_colors[j]
            texto_cor = (38, 32, 63)

        box = [
            145,
            yy,
            W - 145,
            yy + 100
        ]

        shadow_alt = [
            box[0] + 8,
            box[1] + 10,
            box[2] + 8,
            box[3] + 10
        ]

        draw.rounded_rectangle(
            shadow_alt,
            radius=26,
            fill=PURPLE
        )

        draw.rounded_rectangle(
            box,
            radius=26,
            fill=bg,
            outline=PURPLE,
            width=6
        )

        label = [
            170,
            yy + 16,
            250,
            yy + 84
        ]

        draw.rounded_rectangle(
            label,
            radius=18,
            fill=label_bg
        )

        letra_txt = (
            "✓"
            if estado == "answer" and correta
            else letras[j]
        )

        texto_central(
            draw,
            yy + 29,
            letra_txt,
            fonte(38, True),
            (255, 255, 255),
            label[0],
            label[2]
        )

        f_alt = fonte(
            37 if len(str(alt)) <= 25 else 31,
            True
        )

        draw.text(
            (285, yy + 28),
            str(alt),
            font=f_alt,
            fill=texto_cor
        )

    texto_central(
        draw,
        1450,
        feedback,
        fonte(32, True),
        PINK
    )

    # Rodapé
    texto_central(
        draw,
        H - 115,
        "QUANTAS VOCÊ CONSEGUE ACERTAR?",
        fonte(34, True),
        (255, 255, 255)
    )

    texto_central(
        draw,
        H - 70,
        "@juhquiz",
        fonte(26, True),
        (255, 240, 235)
    )

    return img


def render_final(tema):
    img = Image.new("RGB", (W, H), CORAL)
    draw = ImageDraw.Draw(img)

    limite_topo = int(H * 0.31)

    draw.rectangle(
        [0, 0, W, limite_topo],
        fill=YELLOW
    )

    draw.rectangle(
        [0, limite_topo, W, H],
        fill=CORAL
    )

    draw.rounded_rectangle(
        [280, 60, 800, 180],
        radius=32,
        fill=PURPLE,
        outline=(255, 255, 255),
        width=12
    )

    texto_central(
        draw,
        86,
        "JUH QUIZ",
        fonte(54, True),
        (255, 255, 255)
    )

    tema_txt = f"TEMA: {tema.upper()}"

    texto_central(
        draw,
        240,
        tema_txt,
        fonte(32, True),
        PURPLE
    )

    card = [80, 390, W - 80, 1490]

    draw.rounded_rectangle(
        [
            card[0] + 20,
            card[1] + 22,
            card[2] + 20,
            card[3] + 22
        ],
        radius=50,
        fill=(120, 62, 88)
    )

    draw.rounded_rectangle(
        card,
        radius=50,
        fill=CREAM,
        outline=PURPLE,
        width=10
    )

    texto_central(
        draw,
        520,
        "FIM DO DESAFIO!",
        fonte(56, True),
        PINK
    )

    texto_central(
        draw,
        650,
        "QUANTAS VOCÊ ACERTOU?",
        fonte(48, True),
        PURPLE
    )

    placares = [
        "5/5 = GÊNIO",
        "4/5 = MUITO BOM",
        "3/5 = QUASE LÁ",
    ]

    y = 800

    for txt in placares:
        draw.rounded_rectangle(
            [230, y, W - 230, y + 110],
            radius=28,
            fill=(255, 255, 255),
            outline=PURPLE,
            width=5
        )

        texto_central(
            draw,
            y + 30,
            txt,
            fonte(34, True),
            PURPLE
        )

        y += 145

    texto_central(
        draw,
        1280,
        "COMENTA SUA PONTUAÇÃO",
        fonte(38, True),
        PINK
    )

    texto_central(
        draw,
        H - 110,
        "@juhquiz",
        fonte(28, True),
        (255, 255, 255)
    )

    return img


# ============================================================
# ÁUDIO / FFMPEG
# ============================================================

def limpar_tts(texto):
    return re.sub(
        r"\s+",
        " ",
        str(texto)
    ).strip()


def tts_salvar(texto, caminho):
    caminho = str(caminho)

    if os.path.exists(caminho):
        os.remove(caminho)

    texto_tts = limpar_tts(texto)

    if not texto_tts:
        raise ValueError("Texto vazio para narração.")

    p = subprocess.run(
        [
            "edge-tts",
            "--voice", VOZ,
            "--rate", VELOCIDADE_VOZ,
            "--text", texto_tts,
            "--write-media", caminho
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if p.returncode != 0:
        print(p.stderr, flush=True)
        raise RuntimeError(
            "Falha ao gerar voz com Edge TTS."
        )

    if (
        not os.path.exists(caminho)
        or os.path.getsize(caminho) < 500
    ):
        raise RuntimeError(
            f"Áudio não foi criado: {caminho}"
        )


def duracao_audio(caminho):
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(caminho)
    ]

    return float(
        subprocess.check_output(
            cmd,
            text=True
        ).strip()
    )


def criar_beep(caminho, frequencia=950):
    caminho = str(caminho)

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency={frequencia}:duration=0.14",
        "-af",
        "volume=0.55,apad=pad_dur=1",
        "-t",
        "1.0",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-ar",
        str(AUDIO_HZ),
        "-ac",
        str(AUDIO_CHANNELS),
        caminho
    ]

    executar(cmd)


def criar_clipe_imagem(
    img_path,
    duracao,
    saida,
    audio=None
):
    img_path = str(img_path)
    saida = str(saida)
    duracao = float(duracao)

    if audio:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-i",
            str(audio),
            "-t",
            f"{duracao:.3f}",
            "-vf",
            f"scale={W}:{H},fps={FPS},format=yuv420p",
            "-af",
            f"aresample={AUDIO_HZ}:async=1:first_pts=0,apad",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            str(AUDIO_HZ),
            "-ac",
            str(AUDIO_CHANNELS),
            "-video_track_timescale",
            "90000",
            "-avoid_negative_ts",
            "make_zero",
            "-movflags",
            "+faststart",
            saida
        ]

    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            img_path,
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_HZ}",
            "-t",
            f"{duracao:.3f}",
            "-vf",
            f"scale={W}:{H},fps={FPS},format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-ar",
            str(AUDIO_HZ),
            "-ac",
            str(AUDIO_CHANNELS),
            "-shortest",
            "-video_track_timescale",
            "90000",
            "-avoid_negative_ts",
            "make_zero",
            "-movflags",
            "+faststart",
            saida
        ]

    executar(cmd)


def juntar_clipes(
    lista,
    saida,
    concat_path
):
    concat_path = Path(concat_path).resolve()
    saida = Path(saida).resolve()

    concat_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    saida.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        concat_path,
        "w",
        encoding="utf-8"
    ) as f:

        for p in lista:
            p_abs = Path(p).resolve()

            if not p_abs.exists():
                raise FileNotFoundError(
                    f"Segmento não encontrado: {p_abs}"
                )

            caminho_ffmpeg = str(
                p_abs
            ).replace(
                "'",
                "'\\''"
            )

            f.write(
                "file '" + caminho_ffmpeg + "'\n"
            )

    cmd = [
        "ffmpeg",
        "-y",
        "-fflags",
        "+genpts",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "160k",
        "-ar",
        str(AUDIO_HZ),
        "-ac",
        str(AUDIO_CHANNELS),
        "-af",
        f"aresample={AUDIO_HZ}:async=1:first_pts=0",
        "-avoid_negative_ts",
        "make_zero",
        "-movflags",
        "+faststart",
        str(saida)
    ]

    executar(cmd)


# ============================================================
# VALIDAÇÃO
# ============================================================

def validar():
    if not isinstance(QUIZZES, dict):
        raise ValueError(
            "QUIZZES precisa ser um dicionário."
        )

    if not QUIZZES:
        raise ValueError(
            "Nenhum tema foi encontrado em perguntas.py."
        )

    for tema, perguntas in QUIZZES.items():

        if len(perguntas) != PERGUNTAS_POR_VIDEO:
            raise ValueError(
                f"Tema '{tema}' precisa ter exatamente "
                f"{PERGUNTAS_POR_VIDEO} perguntas."
            )

        for numero, q in enumerate(
            perguntas,
            start=1
        ):
            if "pergunta" not in q:
                raise ValueError(
                    f"{tema} / pergunta {numero}: "
                    "campo 'pergunta' ausente."
                )

            if "alternativas" not in q:
                raise ValueError(
                    f"{tema} / pergunta {numero}: "
                    "campo 'alternativas' ausente."
                )

            if "correta" not in q:
                raise ValueError(
                    f"{tema} / pergunta {numero}: "
                    "campo 'correta' ausente."
                )

            if len(q["alternativas"]) != 3:
                raise ValueError(
                    f"{tema} / pergunta {numero}: "
                    "precisa ter 3 alternativas."
                )

            if int(q["correta"]) not in (0, 1, 2):
                raise ValueError(
                    f"{tema} / pergunta {numero}: "
                    "'correta' deve ser 0, 1 ou 2."
                )


# ============================================================
# GERAÇÃO
# ============================================================

def main():
    validar()

    if PASTA_TMP.exists():
        shutil.rmtree(PASTA_TMP)

    PASTA_TMP.mkdir(
        parents=True,
        exist_ok=True
    )

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    total_videos = len(QUIZZES)

    print(
        f"📅 Pasta do dia: {PASTA_SAIDA}",
        flush=True
    )

    print(
        f"🎬 Gerando {total_videos} vídeos × "
        f"{PERGUNTAS_POR_VIDEO} perguntas",
        flush=True
    )

    print(
        f"🎙️ Voz: {VOZ} | "
        f"velocidade: {VELOCIDADE_VOZ}",
        flush=True
    )

    print(
        f"⏱️ Contagem: {TEMPO_ESCOLHA} segundos",
        flush=True
    )

    beep_normal = PASTA_TMP / "beep_950.m4a"
    beep_final = PASTA_TMP / "beep_1250.m4a"

    criar_beep(
        beep_normal,
        950
    )

    criar_beep(
        beep_final,
        1250
    )

    videos_gerados = []

    for video_num, (
        tema,
        perguntas_tema
    ) in enumerate(
        QUIZZES.items(),
        start=1
    ):

        print(
            "\n" + "=" * 72,
            flush=True
        )

        print(
            f"🎬 {video_num:02d}/{total_videos:02d} — {tema}",
            flush=True
        )

        print(
            "=" * 72,
            flush=True
        )

        pasta_video = (
            PASTA_TMP
            / f"video_{video_num:02d}_{slug(tema)}"
        )

        pasta_video.mkdir(
            parents=True,
            exist_ok=True
        )

        segmentos = []

        for idx, pergunta in enumerate(
            perguntas_tema
        ):
            numero = idx + 1

            print(
                f" • {numero}/5 — "
                f"{pergunta['pergunta']}",
                flush=True
            )

            pasta_q = (
                pasta_video
                / f"q{numero:02d}"
            )

            pasta_q.mkdir(
                parents=True,
                exist_ok=True
            )

            # ------------------------------------------------
            # 1) NARRA SOMENTE A PERGUNTA
            # ------------------------------------------------

            audio_q = (
                pasta_q
                / "pergunta.mp3"
            )

            tts_salvar(
                pergunta["pergunta"],
                audio_q
            )

            dur_q = (
                duracao_audio(audio_q)
                + 0.15
            )

            frame_q = (
                pasta_q
                / "01_pergunta.png"
            )

            render_frame(
                tema=tema,
                pergunta=pergunta,
                numero=numero,
                estado="reading"
            ).save(frame_q)

            clip_q = (
                pasta_q
                / "01_pergunta.mp4"
            )

            criar_clipe_imagem(
                frame_q,
                dur_q,
                clip_q,
                audio=audio_q
            )

            segmentos.append(
                clip_q
            )

            # ------------------------------------------------
            # 2) CONTAGEM 3, 2, 1
            # ------------------------------------------------

            for segundos in range(
                TEMPO_ESCOLHA,
                0,
                -1
            ):
                frame_timer = (
                    pasta_q
                    / f"timer_{segundos}.png"
                )

                render_frame(
                    tema=tema,
                    pergunta=pergunta,
                    numero=numero,
                    estado="countdown",
                    timer=segundos
                ).save(
                    frame_timer
                )

                clip_timer = (
                    pasta_q
                    / f"timer_{segundos}.mp4"
                )

                som = (
                    beep_final
                    if segundos == 1
                    else beep_normal
                )

                criar_clipe_imagem(
                    frame_timer,
                    1.0,
                    clip_timer,
                    audio=som
                )

                segmentos.append(
                    clip_timer
                )

            # ------------------------------------------------
            # 3) REVELA E NARRA SOMENTE A RESPOSTA CERTA
            # ------------------------------------------------

            correta = int(
                pergunta["correta"]
            )

            texto_resposta = (
                pergunta["alternativas"][correta]
            )

            audio_resp = (
                pasta_q
                / "resposta.mp3"
            )

            tts_salvar(
                texto_resposta,
                audio_resp
            )

            # IMPORTANTE:
            # o frame da resposta permanece em tela durante
            # TODA a voz + a pausa.
            dur_resp = (
                duracao_audio(audio_resp)
                + PAUSA_DEPOIS_RESPOSTA
            )

            frame_resp = (
                pasta_q
                / "03_resposta.png"
            )

            render_frame(
                tema=tema,
                pergunta=pergunta,
                numero=numero,
                estado="answer"
            ).save(
                frame_resp
            )

            clip_resp = (
                pasta_q
                / "03_resposta.mp4"
            )

            criar_clipe_imagem(
                frame_resp,
                dur_resp,
                clip_resp,
                audio=audio_resp
            )

            segmentos.append(
                clip_resp
            )

        # ----------------------------------------------------
        # TELA FINAL
        # ----------------------------------------------------

        frame_final = (
            pasta_video
            / "final.png"
        )

        render_final(
            tema
        ).save(
            frame_final
        )

        clip_final = (
            pasta_video
            / "final.mp4"
        )

        criar_clipe_imagem(
            frame_final,
            2.0,
            clip_final
        )

        segmentos.append(
            clip_final
        )

        nome_saida = (
            f"{video_num:02d}_"
            f"{slug(tema)}_"
            f"{DATA_DO_DIA}.mp4"
        )

        saida_video = (
            PASTA_SAIDA
            / nome_saida
        )

        juntar_clipes(
            segmentos,
            saida_video,
            pasta_video / "concat.txt"
        )

        videos_gerados.append(
            saida_video
        )

        print(
            f"✅ Vídeo {video_num}/{total_videos} "
            f"gerado: {saida_video}",
            flush=True
        )

    print(
        "\n✅ FINALIZADO",
        flush=True
    )

    print(
        f"📁 {PASTA_SAIDA}",
        flush=True
    )

    for p in videos_gerados:
        print(
            " -",
            p,
            flush=True
        )


if __name__ == "__main__":
    main()
