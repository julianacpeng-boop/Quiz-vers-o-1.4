import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
from dados_quiz import QUIZZES

# ============================================================
# JUH QUIZ — VÍDEO COM IMAGEM ESCOLHIDA POR PERGUNTA
#
# Fluxo:
#   1) o vídeo já começa na PRIMEIRA PERGUNTA
#   2) lê SOMENTE a pergunta
#   3) contagem 3, 2, 1
#   4) destaca a resposta correta
#   5) lê SOMENTE a resposta correta
#
# Cada pergunta escolhe:
#   usar_imagens=True  -> mostra 3 imagens
#   usar_imagens=False -> sem imagens
# ============================================================

# ---------------- CONFIGURAÇÃO ----------------
TEMPO_ESCOLHA = 3

# Mesma voz usada no Quiz 1.5
VOZ = "pt-BR-AntonioNeural"
VELOCIDADE_VOZ = "+10%"

W = 1080
H = 1920
FPS = 30

AUDIO_HZ = 48000
AUDIO_CHANNELS = 2

PAUSA_DEPOIS_PERGUNTA = 0.15
PAUSA_DEPOIS_RESPOSTA = 0.55

# Fundo do projeto
FUNDO = Path("assets/fundo_juh_quiz.png")

FUSO = ZoneInfo("America/Fortaleza")
DATA_DO_DIA = datetime.now(FUSO).strftime("%Y-%m-%d")

PASTA_RAIZ = Path("output_juh_quiz")
PASTA_TMP = Path("_tmp_juhquiz")
PASTA_SAIDA = PASTA_RAIZ / DATA_DO_DIA

WHITE = (250, 250, 252)
BLACK = (16, 16, 18)
BLUE = (21, 105, 194)
DARK_BLUE = (10, 52, 140)
PINK = (235, 0, 130)
PINK_LIGHT = (255, 208, 238)
GREEN = (92, 204, 43)
GREEN_DARK = (42, 137, 18)
GRAY = (150, 155, 170)
SOFT_GRAY = (224, 228, 236)
YELLOW = (255, 207, 45)

# ============================================================
# UTILIDADES
# ============================================================

def slug(texto):
    txt = unicodedata.normalize("NFKD", str(texto))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", txt).strip("-").lower()
    return txt or "quiz"


def executar(cmd):
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if p.returncode != 0:
        print(p.stdout)
        print(p.stderr)
        raise RuntimeError("Falha ao executar comando.")
    return p


def fonte(tamanho, bold=False):
    candidatos = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",

        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",

        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
    ]

    for arq in candidatos:
        try:
            return ImageFont.truetype(arq, tamanho)
        except Exception:
            pass

    return ImageFont.load_default()


def wrap_text(draw, texto, fnt, max_width):
    palavras = str(texto).split()

    if not palavras:
        return [""]

    linhas = []
    atual = palavras[0]

    for palavra in palavras[1:]:
        teste = atual + " " + palavra
        bb = draw.textbbox((0, 0), teste, font=fnt)

        if bb[2] - bb[0] <= max_width:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra

    linhas.append(atual)
    return linhas


def draw_centered_text(draw, texto, y, fnt, fill, x0=60, x1=None):
    if x1 is None:
        x1 = W - 60

    bb = draw.textbbox((0, 0), str(texto), font=fnt)
    tw = bb[2] - bb[0]
    x = x0 + ((x1 - x0) - tw) / 2
    draw.text((x, y), str(texto), font=fnt, fill=fill)


def draw_text_in_box(
    draw,
    texto,
    box,
    max_size=58,
    min_size=22,
    fill=BLACK,
    bold=True,
    align="center",
    max_lines=None
):
    x1, y1, x2, y2 = box
    bw = x2 - x1
    bh = y2 - y1

    for size in range(max_size, min_size - 1, -2):
        f = fonte(size, bold)
        linhas = wrap_text(draw, texto, f, bw)

        if max_lines is not None and len(linhas) > max_lines:
            continue

        bb_ag = draw.textbbox((0, 0), "Ag", font=f)
        lh = bb_ag[3] - bb_ag[1]
        total_h = len(linhas) * lh + max(0, len(linhas) - 1) * 8

        if total_h <= bh:
            yy = y1 + (bh - total_h) / 2

            for linha in linhas:
                bb = draw.textbbox((0, 0), linha, font=f)
                tw = bb[2] - bb[0]

                if align == "left":
                    xx = x1
                elif align == "right":
                    xx = x2 - tw
                else:
                    xx = x1 + (bw - tw) / 2

                draw.text((xx, yy), linha, font=f, fill=fill)
                yy += lh + 8

            return

    f = fonte(min_size, bold)
    draw.text((x1, y1), texto, font=f, fill=fill)


def fundo_base():
    if not FUNDO.exists():
        raise FileNotFoundError(
            f"Fundo não encontrado: {FUNDO}. "
            "Envie assets/fundo_juh_quiz.png ao GitHub."
        )

    img = Image.open(FUNDO).convert("RGB")
    resampling = getattr(Image, "Resampling", Image)

    return ImageOps.fit(
        img,
        (W, H),
        method=resampling.LANCZOS,
        centering=(0.5, 0.5)
    )


def imagem_arredondada(path, size, radius=28):
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(
            f"Imagem da pergunta não encontrada: {p}"
        )

    foto = Image.open(p).convert("RGB")
    resampling = getattr(Image, "Resampling", Image)

    foto = ImageOps.fit(
        foto,
        size,
        method=resampling.LANCZOS
    )

    mask = Image.new("L", size, 0)
    md = ImageDraw.Draw(mask)

    md.rounded_rectangle(
        [0, 0, size[0] - 1, size[1] - 1],
        radius=radius,
        fill=255
    )

    foto.putalpha(mask)
    return foto


def validar_pergunta(pergunta):
    if "pergunta" not in pergunta:
        raise ValueError(
            "Pergunta sem campo 'pergunta'."
        )

    if len(pergunta.get("alternativas", [])) != 3:
        raise ValueError(
            f'A pergunta "{pergunta["pergunta"]}" precisa ter 3 alternativas.'
        )

    correta = int(pergunta.get("correta", -1))

    if correta not in (0, 1, 2):
        raise ValueError(
            f'A pergunta "{pergunta["pergunta"]}" precisa de correta 0, 1 ou 2.'
        )

    if pergunta.get("usar_imagens", False):
        imagens = pergunta.get("imagens", [])

        if len(imagens) != 3:
            raise ValueError(
                f'A pergunta "{pergunta["pergunta"]}" está com '
                "usar_imagens=True e precisa ter exatamente 3 imagens."
            )

        for caminho in imagens:
            if not Path(caminho).exists():
                raise FileNotFoundError(
                    f'Imagem ausente na pergunta '
                    f'"{pergunta["pergunta"]}": {caminho}'
                )


# ============================================================
# DESENHO
# ============================================================

def desenhar_tema(draw, tema):
    """
    Tema pequeno e fixo acima da pergunta.
    Não cobre o logo do fundo.
    """
    box = [285, 285, 795, 352]

    draw.rounded_rectangle(
        [box[0] + 4, box[1] + 5, box[2] + 4, box[3] + 5],
        radius=30,
        fill=(215, 166, 28)
    )

    draw.rounded_rectangle(
        box,
        radius=30,
        fill=YELLOW
    )

    draw_text_in_box(
        draw,
        tema.upper(),
        [box[0] + 18, box[1] + 4, box[2] - 18, box[3] - 4],
        max_size=28,
        min_size=17,
        fill=DARK_BLUE,
        bold=True,
        max_lines=1
    )


def desenhar_badge_pergunta(draw, numero, total):
    """
    Contador 1/3, 2/3, 3/3 no canto direito.
    """
    box = [840, 285, 1015, 352]

    draw.rounded_rectangle(
        [box[0] + 4, box[1] + 5, box[2] + 4, box[3] + 5],
        radius=28,
        fill=(215, 166, 28)
    )

    draw.rounded_rectangle(
        box,
        radius=28,
        fill=YELLOW
    )

    draw_text_in_box(
        draw,
        f"{numero}/{total}",
        [box[0], box[1], box[2], box[3]],
        max_size=30,
        min_size=22,
        fill=DARK_BLUE,
        bold=True
    )


def desenhar_card_pergunta_sem_imagens(
    img,
    pergunta,
    numero,
    total,
    estado,
    timer
):
    draw = ImageDraw.Draw(img)

    desenhar_tema(draw, tema_atual_global)
    desenhar_badge_pergunta(draw, numero, total)

    # Card branco da pergunta
    card = [30, 385, W - 30, 745]

    sombra = Image.new(
        "RGBA",
        (W, H),
        (0, 0, 0, 0)
    )

    sd = ImageDraw.Draw(sombra)

    sd.rounded_rectangle(
        [
            card[0] + 7,
            card[1] + 9,
            card[2] + 7,
            card[3] + 9
        ],
        radius=55,
        fill=(0, 0, 0, 32)
    )

    sombra = sombra.filter(
        ImageFilter.GaussianBlur(10)
    )

    img = Image.alpha_composite(
        img.convert("RGBA"),
        sombra
    ).convert("RGB")

    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        card,
        radius=55,
        fill=WHITE
    )

    draw_text_in_box(
        draw,
        f'{numero}. {pergunta["pergunta"]}',
        [78, 425, W - 78, 700],
        max_size=68,
        min_size=34,
        fill=BLACK,
        bold=True,
        max_lines=4
    )

    timer_y = 790
    alt_top = 970

    return img, timer_y, alt_top


def desenhar_card_pergunta_com_imagens(
    img,
    pergunta,
    numero,
    total,
    estado,
    timer
):
    draw = ImageDraw.Draw(img)

    desenhar_tema(draw, tema_atual_global)
    desenhar_badge_pergunta(draw, numero, total)

    card = [25, 380, W - 25, 1065]

    sombra = Image.new(
        "RGBA",
        (W, H),
        (0, 0, 0, 0)
    )

    sd = ImageDraw.Draw(sombra)

    sd.rounded_rectangle(
        [
            card[0] + 7,
            card[1] + 9,
            card[2] + 7,
            card[3] + 9
        ],
        radius=55,
        fill=(0, 0, 0, 30)
    )

    sombra = sombra.filter(
        ImageFilter.GaussianBlur(10)
    )

    img = Image.alpha_composite(
        img.convert("RGBA"),
        sombra
    ).convert("RGB")

    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle(
        card,
        radius=55,
        fill=WHITE
    )

    draw_text_in_box(
        draw,
        f'{numero}. {pergunta["pergunta"]}',
        [65, 410, W - 65, 595],
        max_size=60,
        min_size=30,
        fill=BLACK,
        bold=True,
        max_lines=4
    )

    imagens = pergunta["imagens"]

    rotulos = pergunta.get(
        "rotulos_imagens",
        ["", "", ""]
    )

    if len(rotulos) != 3:
        rotulos = ["", "", ""]

    box_w = 305
    box_h = 385
    gap = 20

    total_w = box_w * 3 + gap * 2
    x0 = (W - total_w) // 2
    y0 = 625

    for i in range(3):
        x = x0 + i * (box_w + gap)

        foto = imagem_arredondada(
            imagens[i],
            (box_w, box_h),
            radius=30
        )

        img.paste(
            foto,
            (x, y0),
            foto
        )

        draw = ImageDraw.Draw(img)

        if rotulos[i]:
            label_y = y0 + box_h - 58

            draw.rounded_rectangle(
                [
                    x + 14,
                    label_y,
                    x + box_w - 14,
                    y0 + box_h - 12
                ],
                radius=18,
                fill=(35, 35, 42)
            )

            draw_text_in_box(
                draw,
                rotulos[i],
                [
                    x + 22,
                    label_y + 2,
                    x + box_w - 22,
                    y0 + box_h - 13
                ],
                max_size=25,
                min_size=15,
                fill=WHITE,
                bold=True
            )

    timer_y = 1090
    alt_top = 1240

    return img, timer_y, alt_top


def desenhar_timer(draw, estado, timer, timer_y):
    if estado == "reading":
        txt = "..."
        legenda = "OUÇA A PERGUNTA"

    elif estado == "countdown":
        txt = str(timer)
        legenda = "RESPONDA AGORA"

    else:
        txt = "✓"
        legenda = "RESPOSTA CORRETA"

    d = 105
    x0 = W // 2 - d // 2
    x1 = x0 + d

    draw.ellipse(
        [
            x0 - 5,
            timer_y - 5,
            x1 + 5,
            timer_y + d + 5
        ],
        fill=WHITE
    )

    draw.ellipse(
        [
            x0,
            timer_y,
            x1,
            timer_y + d
        ],
        fill=DARK_BLUE
    )

    draw_text_in_box(
        draw,
        txt,
        [
            x0,
            timer_y,
            x1,
            timer_y + d
        ],
        max_size=48,
        min_size=30,
        fill=WHITE,
        bold=True
    )

    draw_centered_text(
        draw,
        legenda,
        timer_y + d + 18,
        fonte(24, True),
        WHITE
    )


def desenhar_alternativas(
    draw,
    pergunta,
    estado,
    alt_top
):
    """
    Opções inspiradas no modelo desejado:
    - barra branca limpa
    - bastante arredondada
    - círculo rosa A/B/C
    - sombra leve
    - sem borda preta pesada
    """
    alternativas = pergunta["alternativas"]
    correta_idx = int(pergunta["correta"])

    opt_h = 118
    gap = 25
    x = 62
    w = W - 124

    letras = ["A", "B", "C"]

    for i, alt in enumerate(alternativas):
        y = alt_top + i * (opt_h + gap)
        correta = i == correta_idx

        if estado == "answer" and correta:
            fill = (233, 255, 220)
            outline = (119, 219, 72)
            letter_fill = GREEN
            text_fill = GREEN_DARK
            circle_outline = (214, 255, 198)

        elif estado == "answer" and not correta:
            fill = (248, 248, 250)
            outline = (236, 236, 240)
            letter_fill = (188, 190, 198)
            text_fill = (125, 128, 138)
            circle_outline = (229, 230, 234)

        else:
            fill = WHITE
            outline = (242, 242, 246)
            letter_fill = PINK
            text_fill = BLACK
            circle_outline = PINK_LIGHT

        # Sombra MUITO suave
        draw.rounded_rectangle(
            [
                x + 3,
                y + 7,
                x + w + 3,
                y + opt_h + 7
            ],
            radius=999,
            fill=SOFT_GRAY
        )

        # Barra branca
        draw.rounded_rectangle(
            [
                x,
                y,
                x + w,
                y + opt_h
            ],
            radius=999,
            fill=fill,
            outline=outline,
            width=2
        )

        # Círculo A/B/C
        d = opt_h

        draw.ellipse(
            [
                x,
                y,
                x + d,
                y + d
            ],
            fill=letter_fill,
            outline=circle_outline,
            width=5
        )

        letra = (
            "✓"
            if estado == "answer" and correta
            else letras[i]
        )

        draw_text_in_box(
            draw,
            letra,
            [
                x,
                y,
                x + d,
                y + d
            ],
            max_size=56,
            min_size=30,
            fill=WHITE,
            bold=True
        )

        draw_text_in_box(
            draw,
            alt,
            [
                x + d + 36,
                y + 8,
                x + w - 38,
                y + opt_h - 8
            ],
            max_size=48,
            min_size=22,
            fill=text_fill,
            bold=True,
            align="left",
            max_lines=2
        )


# variável usada pelas funções de desenho
tema_atual_global = ""


def render_frame(
    tema,
    pergunta,
    numero,
    total,
    estado,
    timer=None
):
    global tema_atual_global
    tema_atual_global = tema

    validar_pergunta(pergunta)

    img = fundo_base()

    if pergunta.get("usar_imagens", False):
        img, timer_y, alt_top = (
            desenhar_card_pergunta_com_imagens(
                img,
                pergunta,
                numero,
                total,
                estado,
                timer
            )
        )

    else:
        img, timer_y, alt_top = (
            desenhar_card_pergunta_sem_imagens(
                img,
                pergunta,
                numero,
                total,
                estado,
                timer
            )
        )

    draw = ImageDraw.Draw(img)

    desenhar_timer(
        draw,
        estado,
        timer,
        timer_y
    )

    desenhar_alternativas(
        draw,
        pergunta,
        estado,
        alt_top
    )

    return img


def render_final(tema, total):
    img = fundo_base()
    draw = ImageDraw.Draw(img)

    card = [
        110,
        660,
        W - 110,
        1230
    ]

    draw.rounded_rectangle(
        card,
        radius=58,
        fill=WHITE
    )

    draw_text_in_box(
        draw,
        "FIM DO DESAFIO!",
        [
            170,
            725,
            W - 170,
            850
        ],
        max_size=62,
        min_size=36,
        fill=PINK,
        bold=True
    )

    draw_text_in_box(
        draw,
        tema.upper(),
        [
            160,
            865,
            W - 160,
            1010
        ],
        max_size=52,
        min_size=30,
        fill=DARK_BLUE,
        bold=True,
        max_lines=2
    )

    draw_text_in_box(
        draw,
        "QUANTAS VOCÊ ACERTOU?",
        [
            160,
            1030,
            W - 160,
            1120
        ],
        max_size=38,
        min_size=26,
        fill=BLACK,
        bold=True
    )

    draw_text_in_box(
        draw,
        f"{total}/{total}?",
        [
            250,
            1120,
            W - 250,
            1205
        ],
        max_size=58,
        min_size=34,
        fill=PINK,
        bold=True
    )

    return img


# ============================================================
# ÁUDIO
# ============================================================

def limpar_tts(texto):
    return re.sub(
        r"\s+",
        " ",
        str(texto)
    ).strip()


def tts_salvar(texto, caminho):
    caminho = Path(caminho)

    if caminho.exists():
        caminho.unlink()

    executar([
        "edge-tts",
        "--voice", VOZ,
        "--rate", VELOCIDADE_VOZ,
        "--text", limpar_tts(texto),
        "--write-media", str(caminho),
    ])

    if (
        not caminho.exists()
        or caminho.stat().st_size < 500
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
    executar([
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
        str(caminho)
    ])


def criar_clipe_imagem(
    img_path,
    duracao,
    saida,
    audio=None
):
    duracao = float(duracao)

    if audio:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(img_path),
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
            "-shortest",
            "-movflags",
            "+faststart",
            str(saida)
        ]

    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(img_path),
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
            "-movflags",
            "+faststart",
            str(saida)
        ]

    executar(cmd)


def concatenar_clipes(clipes, saida):
    lista = PASTA_TMP / "concat.txt"

    lista.write_text(
        "\n".join(
            f"file '{Path(c).resolve().as_posix()}'"
            for c in clipes
        ),
        encoding="utf-8"
    )

    executar([
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(lista),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(saida)
    ])


# ============================================================
# GERAÇÃO
# ============================================================

def salvar_frame(img, nome):
    caminho = PASTA_TMP / nome
    img.save(caminho, quality=95)
    return caminho


def gerar_video_tema(
    tema,
    perguntas,
    indice_tema,
    total_temas
):
    total = len(perguntas)

    if total == 0:
        return None

    print(
        f"\n🎬 {indice_tema:02d}/{total_temas:02d} — {tema}"
    )

    for p in perguntas:
        validar_pergunta(p)

    pasta_tema = (
        PASTA_TMP / slug(tema)
    )

    pasta_tema.mkdir(
        parents=True,
        exist_ok=True
    )

    clipes = []

    # NÃO TEM MAIS INTRO.
    # O VÍDEO COMEÇA DIRETO NA PERGUNTA 1.

    # beep único reaproveitado
    beep = pasta_tema / "beep.m4a"
    criar_beep(beep)

    for idx, pergunta in enumerate(
        perguntas,
        start=1
    ):
        base_idx = idx * 10

        # ----------------------------------------
        # LEITURA DA PERGUNTA
        # ----------------------------------------
        leitura_img = render_frame(
            tema,
            pergunta,
            idx,
            total,
            "reading"
        )

        leitura_png = salvar_frame(
            leitura_img,
            f"{slug(tema)}_{idx:02d}_reading.png"
        )

        q_audio = (
            pasta_tema
            / f"{idx:02d}_pergunta.mp3"
        )

        # lê SOMENTE a pergunta
        tts_salvar(
            pergunta["pergunta"],
            q_audio
        )

        q_dur = (
            duracao_audio(q_audio)
            + PAUSA_DEPOIS_PERGUNTA
        )

        q_clip = (
            pasta_tema
            / f"{base_idx:03d}_reading.mp4"
        )

        criar_clipe_imagem(
            leitura_png,
            q_dur,
            q_clip,
            q_audio
        )

        clipes.append(q_clip)

        # ----------------------------------------
        # CONTAGEM 3, 2, 1
        # ----------------------------------------
        for n in (3, 2, 1):
            count_img = render_frame(
                tema,
                pergunta,
                idx,
                total,
                "countdown",
                timer=n
            )

            count_png = salvar_frame(
                count_img,
                f"{slug(tema)}_{idx:02d}_{n}.png"
            )

            count_clip = (
                pasta_tema
                / f"{base_idx + (4 - n):03d}_count_{n}.mp4"
            )

            criar_clipe_imagem(
                count_png,
                1.0,
                count_clip,
                beep
            )

            clipes.append(count_clip)

        # ----------------------------------------
        # RESPOSTA CORRETA
        # ----------------------------------------
        resp_img = render_frame(
            tema,
            pergunta,
            idx,
            total,
            "answer"
        )

        resp_png = salvar_frame(
            resp_img,
            f"{slug(tema)}_{idx:02d}_answer.png"
        )

        correta = pergunta["alternativas"][
            int(pergunta["correta"])
        ]

        resp_audio = (
            pasta_tema
            / f"{idx:02d}_resposta.mp3"
        )

        # lê SOMENTE a resposta correta
        tts_salvar(
            f"A resposta correta é: {correta}.",
            resp_audio
        )

        resp_dur = (
            duracao_audio(resp_audio)
            + PAUSA_DEPOIS_RESPOSTA
        )

        resp_clip = (
            pasta_tema
            / f"{base_idx + 4:03d}_answer.mp4"
        )

        criar_clipe_imagem(
            resp_png,
            resp_dur,
            resp_clip,
            resp_audio
        )

        clipes.append(resp_clip)

    # --------------------------------------------
    # TELA FINAL
    # --------------------------------------------
    final_img = render_final(
        tema,
        total
    )

    final_png = salvar_frame(
        final_img,
        f"{slug(tema)}_final.png"
    )

    final_audio = (
        pasta_tema
        / "final.mp3"
    )

    tts_salvar(
        "Fim do desafio. Quantas você acertou?",
        final_audio
    )

    final_dur = (
        duracao_audio(final_audio)
        + 0.8
    )

    final_clip = (
        pasta_tema
        / "999_final.mp4"
    )

    criar_clipe_imagem(
        final_png,
        final_dur,
        final_clip,
        final_audio
    )

    clipes.append(final_clip)

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    saida = (
        PASTA_SAIDA
        / f"{indice_tema:02d}_{slug(tema)}.mp4"
    )

    concatenar_clipes(
        clipes,
        saida
    )

    print(f"✅ {saida}")

    return saida


def preview():
    PASTA_TMP.mkdir(
        parents=True,
        exist_ok=True
    )

    tema, perguntas = next(
        iter(QUIZZES.items())
    )

    if not perguntas:
        raise ValueError(
            "QUIZZES está vazio."
        )

    salvos = []

    for p in perguntas:
        validar_pergunta(p)

        img = render_frame(
            tema,
            p,
            numero=perguntas.index(p) + 1,
            total=len(perguntas),
            estado="reading"
        )

        nome = (
            "preview_com_imagem.png"
            if p.get("usar_imagens", False)
            else "preview_sem_imagem.png"
        )

        caminho = Path(nome)
        img.save(caminho)
        salvos.append(caminho)

        if len(
            set(x.name for x in salvos)
        ) >= 2:
            break

    print("PREVIEW criado:")

    for p in salvos:
        print(" -", p)


def main():
    if "--preview" in sys.argv:
        preview()
        return

    if not QUIZZES:
        raise ValueError(
            "QUIZZES está vazio."
        )

    if PASTA_TMP.exists():
        shutil.rmtree(
            PASTA_TMP
        )

    PASTA_TMP.mkdir(
        parents=True,
        exist_ok=True
    )

    PASTA_SAIDA.mkdir(
        parents=True,
        exist_ok=True
    )

    temas = list(
        QUIZZES.items()
    )

    gerados = []

    for i, (
        tema,
        perguntas
    ) in enumerate(
        temas,
        start=1
    ):
        gerado = gerar_video_tema(
            tema,
            perguntas,
            i,
            len(temas)
        )

        if gerado:
            gerados.append(
                gerado
            )

    print(
        f"\n✅ Finalizado. "
        f"{len(gerados)} vídeo(s) gerado(s)."
    )

    for p in gerados:
        print(" -", p)


if __name__ == "__main__":
    main()
