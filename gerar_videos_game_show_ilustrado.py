# -*- coding: utf-8 -*-
"""
JUH QUIZ GAME SHOW — complemento ilustrado

Este arquivo NÃO substitui o banco de perguntas existente.
Ele importa o seu gerar_videos_game_show.py atual, acrescenta:

1) ilustração pequena ao lado da pergunta;
2) suporte visual a emojis usando Noto Color Emoji;
3) emoji não é narrado pelo Edge TTS;
4) a resposta correta continua marcada durante TODA a narração
   da resposta + pausa, e só some quando entra a próxima pergunta.

COMO USAR
---------
Mantenha no repositório:
    gerar_videos_game_show.py

Adicione também este arquivo:
    gerar_videos_game_show_ilustrado.py

E faça o workflow rodar:
    python -u gerar_videos_game_show_ilustrado.py

IMAGENS
-------
Opção A — caminho explícito no dicionário:

{
    "pergunta": "Qual é a característica mais marcante da girafa? 🦒",
    "alternativas": ["Orelhas grandes", "Cauda comprida", "Pescoço longo"],
    "correta": 2,
    "ilustracao": "assets/imagens/animais/03_girafa.png"
}

Opção B — automática, sem adicionar "ilustracao":
para o tema "Animais", a pergunta 3 pode usar:

    assets/imagens/animais/03_girafa.png

O código procura qualquer arquivo começando por:
    03_

Formatos aceitos:
    PNG, WEBP, JPG, JPEG
"""

import os
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import gerar_videos_game_show as base


# ============================================================
# CONFIGURAÇÕES
# ============================================================

PASTA_IMAGENS = Path("assets/imagens")

# Mantém a resposta marcada um pouco mais após terminar a fala.
# O frame continua sendo o frame VERDE da resposta.
base.PAUSA_DEPOIS_RESPOSTA = max(float(base.PAUSA_DEPOIS_RESPOSTA), 0.90)

# Fonte de emoji instalada pelo workflow.
EMOJI_FONT_PATH = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

try:
    EMOJI_FONT_109 = (
        ImageFont.truetype(EMOJI_FONT_PATH, 109)
        if os.path.exists(EMOJI_FONT_PATH)
        else None
    )
except Exception:
    EMOJI_FONT_109 = None

CACHE_ARTES = {}
CACHE_EMOJIS = {}


# ============================================================
# EMOJI
# ============================================================

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
    """
    Separa texto normal e clusters simples de emoji.
    Suporta VS16, tons de pele, ZWJ, bandeiras e keycaps.
    """
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

            # Segundo regional indicator para bandeiras.
            if (
                0x1F1E6 <= ord(ch) <= 0x1F1FF
                and i < len(texto)
                and 0x1F1E6 <= ord(texto[i]) <= 0x1F1FF
            ):
                cluster += texto[i]
                i += 1

            # VS16 / tons / keycap / sequências ZWJ.
            while i < len(texto):
                cp = ord(texto[i])

                if cp in (0xFE0E, 0xFE0F, 0x20E3) or 0x1F3FB <= cp <= 0x1F3FF:
                    cluster += texto[i]
                    i += 1
                    continue

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


def remover_emojis_para_tts(texto):
    """
    Remove emojis antes da narração.
    Assim o Edge TTS não tenta dizer 'rosto sorridente', 'coração' etc.
    """
    partes = []
    for tipo, trecho in separar_segmentos_emoji(texto):
        if tipo == "texto":
            partes.append(trecho)

    limpo = re.sub(r"\s+", " ", "".join(partes)).strip()

    # Se a resposta for SOMENTE emoji, usa o original para não gerar TTS vazio.
    return limpo if limpo else str(texto).strip()


# Substitui a limpeza do TTS do arquivo original.
base.limpar_tts = remover_emojis_para_tts


def renderizar_emoji(cluster, tamanho):
    if EMOJI_FONT_109 is None:
        return None

    chave = (cluster, int(tamanho))
    if chave in CACHE_EMOJIS:
        return CACHE_EMOJIS[chave].copy()

    # NotoColorEmoji do Ubuntu trabalha no strike 109 px.
    temp = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    d = ImageDraw.Draw(temp)

    try:
        d.text(
            (5, 5),
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
    nova_largura = max(1, int(temp.width * escala))

    temp = temp.resize(
        (nova_largura, alvo),
        Image.Resampling.LANCZOS
    )

    CACHE_EMOJIS[chave] = temp.copy()
    return temp


def medir_texto_misto(draw, texto, fnt):
    tamanho = int(getattr(fnt, "size", 32))
    largura = 0

    for tipo, trecho in separar_segmentos_emoji(texto):
        if tipo == "texto":
            if trecho:
                bb = draw.textbbox((0, 0), trecho, font=fnt)
                largura += bb[2] - bb[0]
        else:
            em = renderizar_emoji(trecho, tamanho)
            if em is not None:
                largura += em.width + max(2, tamanho // 12)
            else:
                bb = draw.textbbox((0, 0), trecho, font=fnt)
                largura += bb[2] - bb[0]

    return largura


def desenhar_texto_misto(img, draw, xy, texto, fnt, fill):
    x, y = xy
    tamanho = int(getattr(fnt, "size", 32))

    for tipo, trecho in separar_segmentos_emoji(texto):
        if tipo == "texto":
            if trecho:
                draw.text((x, y), trecho, font=fnt, fill=fill)
                bb = draw.textbbox((0, 0), trecho, font=fnt)
                x += bb[2] - bb[0]
        else:
            em = renderizar_emoji(trecho, tamanho)
            if em is not None:
                # Ajuste vertical para ficar alinhado ao texto.
                yy = int(y - max(0, (em.height - tamanho) * 0.10))
                img.alpha_composite(em, (int(x), yy))
                x += em.width + max(2, tamanho // 12)
            else:
                draw.text((x, y), trecho, font=fnt, fill=fill)
                bb = draw.textbbox((0, 0), trecho, font=fnt)
                x += bb[2] - bb[0]

    return x


def texto_central_misto(img, draw, y, texto, fnt, fill, x0=0, x1=None):
    if x1 is None:
        x1 = base.W

    largura = medir_texto_misto(draw, texto, fnt)
    x = x0 + ((x1 - x0) - largura) / 2
    desenhar_texto_misto(img, draw, (x, y), texto, fnt, fill)


def wrap_text_misto(draw, texto, fnt, max_width):
    palavras = str(texto).split()
    linhas = []
    atual = ""

    for palavra in palavras:
        teste = (atual + " " + palavra).strip()

        if medir_texto_misto(draw, teste, fnt) <= max_width:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra

    if atual:
        linhas.append(atual)

    return linhas


def multilinha_central_mista(
    img,
    draw,
    texto,
    fnt,
    y,
    max_width,
    fill,
    x0,
    x1,
    line_gap=10
):
    linhas = wrap_text_misto(draw, texto, fnt, max_width)

    bb = draw.textbbox((0, 0), "Ag", font=fnt)
    line_h = bb[3] - bb[1]

    yy = y
    for linha in linhas:
        texto_central_misto(
            img, draw, yy, linha, fnt, fill, x0=x0, x1=x1
        )
        yy += line_h + line_gap

    return yy


# ============================================================
# IMAGENS
# ============================================================

def localizar_ilustracao(tema, pergunta, numero):
    # 1) caminho explícito no próprio dicionário
    informado = pergunta.get("ilustracao")

    if informado:
        p = Path(informado)
        if p.exists():
            return p

        print(
            f"⚠️ Ilustração informada não encontrada: {p}",
            flush=True
        )

    # 2) busca automática por tema + número
    # Ex.: tema "Corpo Humano"
    # assets/imagens/corpo_humano/03_pulmoes.png
    pasta = PASTA_IMAGENS / base.slug(tema)

    if not pasta.exists():
        return None

    prefixo = f"{int(numero):02d}"

    padroes = [
        f"{prefixo}_*.png",
        f"{prefixo}_*.webp",
        f"{prefixo}_*.jpg",
        f"{prefixo}_*.jpeg",
        f"{prefixo}.png",
        f"{prefixo}.webp",
        f"{prefixo}.jpg",
        f"{prefixo}.jpeg",
    ]

    for padrao in padroes:
        encontrados = sorted(pasta.glob(padrao))
        if encontrados:
            return encontrados[0]

    return None


def carregar_ilustracao(caminho, max_w=205, max_h=190):
    if caminho is None:
        return None

    chave = (str(caminho), int(max_w), int(max_h))

    if chave in CACHE_ARTES:
        return CACHE_ARTES[chave].copy()

    try:
        arte = Image.open(caminho).convert("RGBA")
        arte.thumbnail(
            (int(max_w), int(max_h)),
            Image.Resampling.LANCZOS
        )

        CACHE_ARTES[chave] = arte.copy()
        return arte
    except Exception as exc:
        print(
            f"⚠️ Não consegui abrir a imagem {caminho}: {exc}",
            flush=True
        )
        return None


def colar_ilustracao(img, caminho, box):
    arte = carregar_ilustracao(
        caminho,
        max_w=box[2] - box[0],
        max_h=box[3] - box[1]
    )

    if arte is None:
        return False

    x = box[0] + ((box[2] - box[0]) - arte.width) // 2
    y = box[1] + ((box[3] - box[1]) - arte.height) // 2

    img.alpha_composite(arte, (int(x), int(y)))
    return True


# ============================================================
# NOVO RENDER DO GAME SHOW
# ============================================================

def render_frame_ilustrado(tema, pergunta, numero, estado, timer=None):
    W = base.W
    H = base.H

    PURPLE = base.PURPLE
    PINK = base.PINK
    YELLOW = base.YELLOW
    CORAL = base.CORAL
    CREAM = base.CREAM
    GREEN = base.GREEN
    GREEN_DARK = base.GREEN_DARK
    TEAL = base.TEAL
    LAVENDER = base.LAVENDER

    img = Image.new("RGBA", (W, H), CORAL + (255,))
    draw = ImageDraw.Draw(img)

    # Fundo
    limite_topo = int(H * 0.31)
    draw.rectangle([0, 0, W, limite_topo], fill=YELLOW)
    draw.rectangle([0, limite_topo, W, H], fill=CORAL)

    # Raios
    import math
    cx, cy = W // 2, 170
    raio = 730

    for i in range(0, 360, 24):
        a1 = math.radians(i)
        a2 = math.radians(i + 10)
        pts = [
            (cx, cy),
            (cx + raio * math.cos(a1), cy + raio * math.sin(a1)),
            (cx + raio * math.cos(a2), cy + raio * math.sin(a2)),
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
    draw.rounded_rectangle(shadow, radius=32, fill=PINK)
    draw.rounded_rectangle(
        logo_box,
        radius=32,
        fill=PURPLE,
        outline=(255, 255, 255),
        width=12
    )
    texto_central_misto(
        img, draw, 86,
        "JUH QUIZ",
        base.fonte(54, True),
        (255, 255, 255)
    )

    # Número
    draw.rounded_rectangle(
        [875, 62, 1018, 132],
        radius=22,
        fill=(255, 255, 255)
    )
    texto_central_misto(
        img, draw, 78,
        f"{numero}/5",
        base.fonte(34, True),
        PURPLE,
        875, 1018
    )

    # Tema
    tema_txt = f"TEMA: {tema.upper()}"
    tema_font = base.fonte(27, True)
    tema_w = medir_texto_misto(draw, tema_txt, tema_font)

    tema_x0 = (W - tema_w) / 2 - 28
    tema_x1 = (W + tema_w) / 2 + 28

    draw.rounded_rectangle(
        [tema_x0, 210, tema_x1, 272],
        radius=30,
        fill=CREAM,
        outline=PURPLE,
        width=4
    )
    texto_central_misto(
        img, draw, 226,
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
    f_chamada = base.fonte(27, True)
    chamada_w = medir_texto_misto(draw, chamada, f_chamada)

    draw.rounded_rectangle(
        [
            W / 2 - chamada_w / 2 - 34,
            390,
            W / 2 + chamada_w / 2 + 34,
            456
        ],
        radius=32,
        fill=PINK
    )
    texto_central_misto(
        img, draw, 408,
        chamada,
        f_chamada,
        (255, 255, 255)
    )

    # --------------------------------------------------------
    # ILUSTRAÇÃO + PERGUNTA
    # --------------------------------------------------------
    caminho_img = localizar_ilustracao(
        tema,
        pergunta,
        numero
    )

    tem_img = caminho_img is not None

    if tem_img:
        # Pergunta fica centralizada no lado esquerdo.
        q_x0 = 100
        q_x1 = 745
        q_max = 590

        colar_ilustracao(
            img,
            caminho_img,
            [770, 495, 985, 700]
        )
    else:
        q_x0 = 100
        q_x1 = W - 100
        q_max = 800

    f_q = base.fonte(49 if tem_img else 54, True)

    y_after = multilinha_central_mista(
        img=img,
        draw=draw,
        texto=pergunta["pergunta"],
        fnt=f_q,
        y=505,
        max_width=q_max,
        fill=(38, 32, 63),
        x0=q_x0,
        x1=q_x1,
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

    texto_central_misto(
        img, draw,
        timer_y + 24,
        timer_txt,
        base.fonte(55, True),
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

        # IMPORTANTE:
        # quando estado == "answer", a correta fica marcada
        # durante toda a narração da resposta + pausa.
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

        box = [145, yy, W - 145, yy + 100]
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

        label = [170, yy + 16, 250, yy + 84]
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

        texto_central_misto(
            img, draw,
            yy + 29,
            letra_txt,
            base.fonte(38, True),
            (255, 255, 255),
            label[0],
            label[2]
        )

        alt_txt = str(alt)
        # Tamanho baseado também no comprimento.
        if len(alt_txt) <= 25:
            f_alt = base.fonte(37, True)
        elif len(alt_txt) <= 38:
            f_alt = base.fonte(31, True)
        else:
            f_alt = base.fonte(27, True)

        desenhar_texto_misto(
            img,
            draw,
            (285, yy + 28),
            alt_txt,
            f_alt,
            texto_cor
        )

    texto_central_misto(
        img, draw,
        1450,
        feedback,
        base.fonte(32, True),
        PINK
    )

    # Rodapé
    texto_central_misto(
        img, draw,
        H - 115,
        "QUANTAS VOCÊ CONSEGUE ACERTAR?",
        base.fonte(34, True),
        (255, 255, 255)
    )
    texto_central_misto(
        img, draw,
        H - 70,
        "@juhquiz",
        base.fonte(26, True),
        (255, 240, 235)
    )

    # O código original espera RGB.
    return img.convert("RGB")


# Injeta o novo render no gerador atual.
base.render_frame = render_frame_ilustrado


if __name__ == "__main__":
    print("🖼️ Modo ilustrado ativado", flush=True)
    print("😀 Suporte a emoji ativado", flush=True)
    print(
        "✅ Resposta correta permanece marcada durante a leitura",
        flush=True
    )
    base.main()
