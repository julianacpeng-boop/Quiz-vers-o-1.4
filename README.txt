JUHQUIZ ILUSTRADO — COMO USAR NO GITHUB

ARQUIVOS:
- gerar_videos_ilustrados.py
- perguntas.py
- requirements.txt
- .github/workflows/gerar-videos-ilustrados.yml
- assets/imagens/

1. PERGUNTAS
Cole o seu dicionário completo de 45 temas em perguntas.py.
O script gera 1 vídeo para cada tema encontrado no dicionário.

2. IMAGENS
Você NÃO precisa editar as 225 perguntas para colocar caminhos.

O script liga automaticamente:
pergunta 1 -> 01.png
pergunta 2 -> 02.png
pergunta 3 -> 03.png
pergunta 4 -> 04.png
pergunta 5 -> 05.png

Exemplo para o tema "Corpo Humano":

assets/
  imagens/
    corpo-humano/
      01.png
      02.png
      03.png
      04.png
      05.png

Exemplo para "Animais da Fazenda":

assets/
  imagens/
    animais-da-fazenda/
      01.png
      02.png
      03.png
      04.png
      05.png

Pode usar PNG, WEBP, JPG ou JPEG.
PNG transparente fica mais bonito.

3. COMO O VÍDEO FUNCIONA
- 1080x1920
- fundo rosa
- folha branca
- 5 perguntas na mesma folha
- pequena ilustração à direita de cada pergunta
- alternativas não são narradas
- voz lê somente a pergunta
- contagem 3, 2, 1 com beep
- revela a correta
- voz lê somente o texto da resposta correta
- tela final de pontuação

4. RODAR
GitHub > Actions > Gerar videos JuhQuiz Ilustrado > Run workflow

5. RESULTADO
O ZIP com os MP4 fica em Artifacts por 7 dias.
