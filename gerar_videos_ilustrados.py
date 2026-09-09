import asyncio
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

from perguntas import QUIZZES

# =========================================================
# CONFIGURAÇÕES
# =========================================================
VOZ = "pt-BR-AntonioNeural"
VELOCIDADE_VOZ = "+10%"

PERGUNTAS_POR_VIDEO = 5
TEMPO_ESCOLHA = 3
PAUSA_DEPOIS_RESPOSTA = 0.55
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

# Usa TODOS os temas existentes em perguntas.py
QUANTIDADE_VIDEOS = None

# =========================================================
# FONTES
# =========================================================
def fonte(caminhos, tamanho):
    for caminho in caminhos:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default()

FONT_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
]
FONT_REG = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
]

F_TITULO = fonte(FONT_BOLD, 49)
F_KICKER = fonte(FONT_BOLD, 22)
F_PERGUNTA = fonte(FONT_BOLD, 34)
F_OPCAO = fonte(FONT_BOLD, 28)
F_NUM = fonte(FONT_BOLD, 24)
F_CONTADOR = fonte(FONT_BOLD, 70)
F_CTA = fonte(FONT_BOLD, 50)
F_CTA2 = fonte(FONT_BOLD, 31)

# =========================================================
# UTILITÁRIOS
# =========================================================
def slugify(texto):
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", "-", texto)
    return texto.strip("-")

def rodar(cmd, quiet=False):
    if not quiet:
        print(" ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True)

def duracao_audio(caminho):
    p = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(caminho)
        ],
        capture_output=True, text=True, check=True
    )
    return max(0.10, float(p.stdout.strip()))

def caminho_abs(p):
    return str(Path(p).resolve()).replace("\\", "/")

def escapar_concat(p):
    return caminho_abs(p).replace("'", "'\\''")

def wrap_text(draw, texto, font, max_width, max_lines=3):
    palavras = texto.split()
    linhas = []
    atual = ""
    for palavra in palavras:
        teste = palavra if not atual else atual + " " + palavra
        bbox = draw.textbbox((0, 0), teste, font=font)
        if bbox[2] - bbox[0] <= max_width:
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
        while draw.textbbox((0, 0), ultima + "…", font=font)[2] > max_width and len(ultima) > 3:
            ultima = ultima[:-1]
        linhas[-1] = ultima.rstrip() + "…"
    return linhas

def desenhar_texto_linhas(draw, x, y, linhas, font, fill, espacamento=8):
    cursor = y
    alturas = []
    for linha in linhas:
        bbox = draw.textbbox((0, 0), linha, font=font)
        h = bbox[3] - bbox[1]
        alturas.append(h)
        draw.text((x, cursor), linha, font=font, fill=fill)
        cursor += h + espacamento
    return cursor, alturas

def buscar_ilustracao(tema, indice, pergunta):
    # 1) Se a pergunta tiver "ilustracao", usa esse caminho.
    manual = pergunta.get("ilustracao")
    if manual:
        p = Path(manual)
        if p.exists():
            return p

    # 2) Senão, procura automaticamente:
    # assets/imagens/slug-do-tema/01.png, 02.png...
    pasta = PASTA_ASSETS / slugify(tema)
    base = f"{indice + 1:02d}"
    for ext in (".png", ".webp", ".jpg", ".jpeg"):
        p = pasta / f"{base}{ext}"
        if p.exists():
            return p
    return None

_cache_img = {}
def carregar_ilustracao(caminho, max_w=165, max_h=165):
    if caminho is None:
        return None
    chave = (str(caminho), max_w, max_h)
    if chave in _cache_img:
        return _cache_img[chave].copy()
    try:
        img = Image.open(caminho).convert("RGBA")
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        _cache_img[chave] = img.copy()
        return img
    except Exception as e:
        print(f"⚠️ Não consegui abrir {caminho}: {e}", flush=True)
        return None

# =========================================================
# ÁUDIO
# =========================================================
async def tts_mp3(texto, saida):
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)

    ultimo_erro = None
    for tentativa in range(1, 4):
        try:
            communicate = edge_tts.Communicate(
                text=texto,
                voice=VOZ,
                rate=VELOCIDADE_VOZ
            )
            await communicate.save(str(saida))
            return
        except Exception as e:
            ultimo_erro = e
            print(f"⚠️ TTS tentativa {tentativa}/3: {e}", flush=True)
            await asyncio.sleep(2 * tentativa)
    raise RuntimeError(f"Falha no TTS: {ultimo_erro}")

def mp3_para_wav(mp3, wav):
    rodar([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(mp3),
        "-ar", str(AUDIO_HZ),
        "-ac", str(AUDIO_CHANNELS),
        "-c:a", "pcm_s16le",
        str(wav)
    ], quiet=True)

def criar_beep_wav(caminho, frequencia=950):
    rodar([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"sine=frequency={frequencia}:duration=0.14",
        "-af", "volume=0.55,apad=pad_dur=1",
        "-t", "1.0",
        "-ar", str(AUDIO_HZ),
        "-ac", str(AUDIO_CHANNELS),
        "-c:a", "pcm_s16le",
        str(caminho)
    ], quiet=True)

def criar_silencio_wav(caminho, duracao):
    rodar([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"anullsrc=r={AUDIO_HZ}:cl=mono",
        "-t", f"{duracao:.3f}",
        "-c:a", "pcm_s16le",
        str(caminho)
    ], quiet=True)

def adicionar_pausa_wav(entrada, saida, pausa):
    rodar([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(entrada),
        "-af", f"apad=pad_dur={pausa}",
        "-ar", str(AUDIO_HZ),
        "-ac", str(AUDIO_CHANNELS),
        "-c:a", "pcm_s16le",
        str(saida)
    ], quiet=True)

def concatenar_audios(wavs, saida_m4a, temp_dir):
    lista = temp_dir / "audio_concat.txt"
    with lista.open("w", encoding="utf-8") as f:
        for wav in wavs:
            f.write(f"file '{escapar_concat(wav)}'\n")

    rodar([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(lista),
        "-c:a", "aac",
        "-b:a", "160k",
        "-ar", str(AUDIO_HZ),
        "-ac", str(AUDIO_CHANNELS),
        str(saida_m4a)
    ], quiet=True)

# =========================================================
# DESENHO
# =========================================================
def rounded_top_rectangle(draw, box, radius, fill):
    x0, y0, x1, y1 = box
    draw.rectangle((x0, y0 + radius, x1, y1), fill=fill)
    draw.rectangle((x0 + radius, y0, x1 - radius, y1), fill=fill)
    draw.pieslice((x0, y0, x0 + 2 * radius, y0 + 2 * radius), 180, 270, fill=fill)
    draw.pieslice((x1 - 2 * radius, y0, x1, y0 + 2 * radius), 270, 360, fill=fill)

def render_frame(tema, perguntas, pergunta_atual, fase, contador=None):
    img = Image.new("RGB", (W, H), ROSA_FUNDO)
    draw = ImageDraw.Draw(img)

    # Fundo rosa superior
    draw.rectangle((0, 0, W, 170), fill=ROSA_FUNDO)

    # Papel
    rounded_top_rectangle(draw, (30, 145, W - 30, H), 48, PAPEL)

    # Kicker
    kicker = "JUHQUIZ • DESAFIO VISUAL"
    kb = draw.textbbox((0, 0), kicker, font=F_KICKER)
    kw = kb[2] - kb[0]
    kx = (W - kw) // 2
    draw.rounded_rectangle((kx - 18, 182, kx + kw + 18, 224), radius=21, fill=LILAS_CLARO)
    draw.text((kx, 190), kicker, font=F_KICKER, fill=LILAS)

    # Tema
    tb = draw.textbbox((0, 0), tema.upper(), font=F_TITULO)
    tw = tb[2] - tb[0]
    draw.text(((W - tw) // 2, 238), tema.upper(), font=F_TITULO, fill=ROSA)
    draw.rounded_rectangle((250, 306, W - 250, 312), radius=3, fill=(52, 49, 58))

    # Contador na área rosa
    if fase == "contagem" and contador is not None:
        cx, cy = W - 110, 79
        draw.ellipse((cx - 55, cy - 55, cx + 55, cy + 55), fill=(255, 255, 255))
        texto = str(contador)
        bb = draw.textbbox((0, 0), texto, font=F_CONTADOR)
        draw.text((cx - (bb[2]-bb[0])//2, cy - (bb[3]-bb[1])//2 - 4),
                  texto, font=F_CONTADOR, fill=ROSA_ESCURO)

    # Blocos de perguntas
    start_y = 338
    bloco_h = 302

    for i, q in enumerate(perguntas):
        y0 = start_y + i * bloco_h
        y1 = y0 + bloco_h - 8
        atual = (i == pergunta_atual)

        # realce suave somente da pergunta atual
        if atual:
            fill = (255, 247, 250)
            draw.rounded_rectangle((55, y0 - 6, W - 55, y1), radius=26, fill=fill)

        # Número
        cx, cy = 94, y0 + 34
        cor_num = ROSA_ESCURO if atual else (190, 111, 142)
        draw.ellipse((cx - 25, cy - 25, cx + 25, cy + 25), fill=ROSA_CLARO)
        num = str(i + 1)
        nb = draw.textbbox((0, 0), num, font=F_NUM)
        draw.text((cx - (nb[2]-nb[0])//2, cy - (nb[3]-nb[1])//2 - 2),
                  num, font=F_NUM, fill=cor_num)

        # Pergunta
        qx = 140
        qy = y0 + 7
        linhas = wrap_text(draw, q["pergunta"], F_PERGUNTA, 675, max_lines=2)

        # marca-texto suave atrás do texto atual
        if atual and fase in ("pergunta", "contagem", "resposta"):
            cursor = qy + 12
            for linha in linhas:
                bb = draw.textbbox((0, 0), linha, font=F_PERGUNTA)
                ww = bb[2] - bb[0]
                hh = bb[3] - bb[1]
                draw.rounded_rectangle(
                    (qx - 7, cursor + hh - 9, qx + ww + 7, cursor + hh + 9),
                    radius=7, fill=(248, 212, 226)
                )
                cursor += hh + 7

        fim_q, _ = desenhar_texto_linhas(draw, qx, qy, linhas, F_PERGUNTA, TEXTO, 7)

        # Ilustração pequena à direita, SEM círculo/fundo
        ilustracao = buscar_ilustracao(tema, i, q)
        arte = carregar_ilustracao(ilustracao, 165, 155)
        if arte is not None:
            ax = 860 + (165 - arte.width) // 2
            ay = y0 + 17 + (155 - arte.height) // 2
            img.paste(arte, (ax, ay), arte)

        # Alternativas
        op_y = max(y0 + 100, fim_q + 18)
        correta = int(q["correta"])
        for j, alt in enumerate(q["alternativas"]):
            oy = op_y + j * 51
            box_x = 145

            if atual and fase == "resposta" and j == correta:
                draw.rounded_rectangle((132, oy - 7, 765, oy + 39), radius=14, fill=VERDE_CLARO)
                draw.rounded_rectangle((box_x, oy, box_x + 30, oy + 30), radius=7, fill=VERDE)
                # check
                draw.line((box_x + 7, oy + 16, box_x + 13, oy + 23), fill=(255,255,255), width=4)
                draw.line((box_x + 13, oy + 23, box_x + 25, oy + 8), fill=(255,255,255), width=4)
                cor_alt = (37, 106, 58)
            else:
                draw.rounded_rectangle((box_x, oy, box_x + 30, oy + 30), radius=7,
                                       fill=(255,255,255), outline=CINZA, width=2)
                cor_alt = TEXTO

            draw.text((box_x + 47, oy - 1), alt, font=F_OPCAO, fill=cor_alt)

        # divisória
        if i < len(perguntas) - 1:
            yy = y1 + 2
            x = 95
            while x < W - 95:
                draw.line((x, yy, min(x + 15, W - 95), yy), fill=DIVISORIA, width=2)
                x += 27

    return img

def render_final(tema):
    img = Image.new("RGB", (W, H), ROSA_FUNDO)
    draw = ImageDraw.Draw(img)
    rounded_top_rectangle(draw, (45, 300, W - 45, H), 56, PAPEL)

    titulo = "JUHQUIZ"
    bb = draw.textbbox((0, 0), titulo, font=F_TITULO)
    draw.text(((W - (bb[2]-bb[0]))//2, 490), titulo, font=F_TITULO, fill=ROSA)

    cta = "QUANTAS VOCÊ ACERTOU?"
    bb = draw.textbbox((0, 0), cta, font=F_CTA)
    draw.text(((W - (bb[2]-bb[0]))//2, 760), cta, font=F_CTA, fill=TEXTO)

    cta2 = "Comenta sua pontuação 👇"
    bb = draw.textbbox((0, 0), cta2, font=F_CTA2)
    draw.text(((W - (bb[2]-bb[0]))//2, 880), cta2, font=F_CTA2, fill=ROSA_ESCURO)

    tema2 = tema.upper()
    bb = draw.textbbox((0, 0), tema2, font=F_KICKER)
    draw.rounded_rectangle(
        ((W-(bb[2]-bb[0]))//2 - 24, 1050,
         (W+(bb[2]-bb[0]))//2 + 24, 1104),
        radius=27, fill=LILAS_CLARO
    )
    draw.text(((W-(bb[2]-bb[0]))//2, 1064), tema2, font=F_KICKER, fill=LILAS)
    return img

# =========================================================
# MONTAGEM DE VÍDEO
# =========================================================
def criar_video_slideshow(frames_duracoes, saida_mp4, temp_dir):
    lista = temp_dir / "frames_concat.txt"
    with lista.open("w", encoding="utf-8") as f:
        for frame, dur in frames_duracoes:
            f.write(f"file '{escapar_concat(frame)}'\n")
            f.write(f"duration {dur:.6f}\n")
        # o concat demuxer precisa repetir o último frame
        f.write(f"file '{escapar_concat(frames_duracoes[-1][0])}'\n")

    rodar([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(lista),
        "-vf", f"fps={FPS},format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-movflags", "+faststart",
        "-an",
        str(saida_mp4)
    ], quiet=True)

def juntar_video_audio(video_sem_audio, audio, saida):
    rodar([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_sem_audio),
        "-i", str(audio),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "160k",
        "-shortest",
        "-movflags", "+faststart",
        str(saida)
    ], quiet=True)

# =========================================================
# VALIDAÇÃO
# =========================================================
def validar():
    if not isinstance(QUIZZES, dict) or not QUIZZES:
        raise ValueError("QUIZZES está vazio.")

    for tema, perguntas in QUIZZES.items():
        if len(perguntas) != PERGUNTAS_POR_VIDEO:
            raise ValueError(
                f"Tema '{tema}' precisa ter exatamente {PERGUNTAS_POR_VIDEO} perguntas."
            )
        for n, q in enumerate(perguntas, 1):
            if "pergunta" not in q or "alternativas" not in q or "correta" not in q:
                raise ValueError(f"{tema} / pergunta {n}: campos obrigatórios ausentes.")
            if len(q["alternativas"]) != 3:
                raise ValueError(f"{tema} / pergunta {n}: precisa ter 3 alternativas.")
            if int(q["correta"]) not in (0, 1, 2):
                raise ValueError(f"{tema} / pergunta {n}: 'correta' deve ser 0, 1 ou 2.")

# =========================================================
# GERAÇÃO
# =========================================================
async def gerar_um_video(video_num, tema, perguntas, pasta_saida):
    slug = slugify(tema)
    temp = Path("_temp_ilustrado") / f"{video_num:02d}_{slug}"
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True, exist_ok=True)

    print(f"\n🎬 {video_num:02d} — {tema}", flush=True)

    frames_duracoes = []
    audios = []

    # Beeps reutilizados dentro deste vídeo
    beep_normal = temp / "beep_normal.wav"
    beep_final = temp / "beep_final.wav"
    criar_beep_wav(beep_normal, 950)
    criar_beep_wav(beep_final, 1250)

    for i, q in enumerate(perguntas):
        print(f"   📝 Pergunta {i+1}/5", flush=True)

        # TTS da pergunta
        q_mp3 = temp / f"q_{i+1:02d}.mp3"
        q_wav = temp / f"q_{i+1:02d}.wav"
        await tts_mp3(q["pergunta"], q_mp3)
        mp3_para_wav(q_mp3, q_wav)
        dq = duracao_audio(q_wav)

        # TTS SOMENTE da resposta correta
        resposta = q["alternativas"][int(q["correta"])]
        a_mp3 = temp / f"a_{i+1:02d}.mp3"
        a_wav0 = temp / f"a_{i+1:02d}_raw.wav"
        a_wav = temp / f"a_{i+1:02d}.wav"
        await tts_mp3(resposta, a_mp3)
        mp3_para_wav(a_mp3, a_wav0)
        adicionar_pausa_wav(a_wav0, a_wav, PAUSA_DEPOIS_RESPOSTA)
        da = duracao_audio(a_wav)

        # Frame: leitura da pergunta
        f_q = temp / f"frame_{i+1:02d}_q.png"
        render_frame(tema, perguntas, i, "pergunta").save(f_q, quality=95)
        frames_duracoes.append((f_q, dq))
        audios.append(q_wav)

        # Contagem 3,2,1
        for numero in (3, 2, 1):
            f_c = temp / f"frame_{i+1:02d}_c{numero}.png"
            render_frame(tema, perguntas, i, "contagem", numero).save(f_c, quality=95)
            frames_duracoes.append((f_c, 1.0))
            audios.append(beep_final if numero == 1 else beep_normal)

        # Frame: resposta correta revelada
        f_a = temp / f"frame_{i+1:02d}_a.png"
        render_frame(tema, perguntas, i, "resposta").save(f_a, quality=95)
        frames_duracoes.append((f_a, da))
        audios.append(a_wav)

    # Tela final
    final_png = temp / "frame_final.png"
    render_final(tema).save(final_png, quality=95)
    frames_duracoes.append((final_png, DURACAO_FINAL))

    final_wav = temp / "final_silencio.wav"
    criar_silencio_wav(final_wav, DURACAO_FINAL)
    audios.append(final_wav)

    # Monta 1 vídeo e 1 áudio por tema (mais rápido que encodar cada fase)
    video_sem_audio = temp / "video_sem_audio.mp4"
    audio_final = temp / "audio_final.m4a"

    print("   🎞️ Montando vídeo...", flush=True)
    criar_video_slideshow(frames_duracoes, video_sem_audio, temp)

    print("   🔊 Montando áudio...", flush=True)
    concatenar_audios(audios, audio_final, temp)

    saida = pasta_saida / f"{video_num:02d}_{slug}.mp4"
    juntar_video_audio(video_sem_audio, audio_final, saida)

    print(f"   ✅ {saida}", flush=True)
    shutil.rmtree(temp, ignore_errors=True)

async def main():
    validar()

    temas = list(QUIZZES.keys())
    if QUANTIDADE_VIDEOS is not None:
        temas = temas[:QUANTIDADE_VIDEOS]

    from datetime import date
    pasta_saida = PASTA_SAIDA / date.today().isoformat()
    pasta_saida.mkdir(parents=True, exist_ok=True)

    print(f"🎀 JuhQuiz Ilustrado", flush=True)
    print(f"📚 Temas: {len(temas)}", flush=True)
    print(f"🖼️ Imagens: assets/imagens/<tema>/01.png ... 05.png", flush=True)

    for idx, tema in enumerate(temas, 1):
        await gerar_um_video(idx, tema, QUIZZES[tema], pasta_saida)

    print("\n🎉 TODOS OS VÍDEOS FORAM GERADOS!", flush=True)
    print(f"📁 {pasta_saida}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
