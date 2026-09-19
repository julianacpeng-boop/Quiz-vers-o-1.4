JUH QUIZ — GERADOR DE VÍDEOS COM IMAGEM POR PERGUNTA
=========================================================

Este projeto segue o fluxo do Quiz 1.5:

1. fala "Quanto você sabe sobre: TEMA?"
2. lê SOMENTE a pergunta
3. contagem 3, 2, 1 com beep
4. destaca a resposta correta
5. lê SOMENTE a resposta correta
6. gera um MP4 por tema

VOZ
---
pt-BR-AntonioNeural
Velocidade: +10%

FUNDO
-----
assets/fundo_juh_quiz.png

ESCOLHA DE IMAGEM POR PERGUNTA
------------------------------

COM 3 IMAGENS:

{
    "pergunta": "Qual órgão bombeia o sangue por todo o corpo?",
    "alternativas": ["Pulmão", "Fígado", "Coração"],
    "correta": 2,
    "usar_imagens": True,
    "imagens": [
        "imagens_perguntas/pulmao.png",
        "imagens_perguntas/figado.png",
        "imagens_perguntas/coracao.png"
    ],
    "rotulos_imagens": ["Pulmão", "Fígado", "Coração"]
}

SEM IMAGEM:

{
    "pergunta": "Qual órgão filtra o sangue e produz a urina?",
    "alternativas": ["Pâncreas", "Rim", "Baço"],
    "correta": 1,
    "usar_imagens": False
}

IMPORTANTE
----------
Quando usar_imagens=True, os 3 arquivos precisam existir na pasta indicada.
Quando usar_imagens=False, não é necessário colocar "imagens".

GITHUB
------
Suba todos os arquivos preservando as pastas.

Depois:
Actions > Gerar Juh Quiz > Run workflow

Os vídeos aparecem no Artifact:
JUH-QUIZ-<número da execução>

SAÍDA
-----
output_juh_quiz/AAAA-MM-DD/*.mp4

TESTE DE LAYOUT SEM GERAR VÍDEO
-------------------------------
python gerar_videos_juh_quiz.py --preview

Isso cria PNGs para você conferir o visual.
