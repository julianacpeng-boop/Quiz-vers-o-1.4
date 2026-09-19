# ============================================================
# EDITE SOMENTE ESTA ÁREA
# ============================================================
#
# correta: 0=A, 1=B, 2=C
#
# Cada pergunta escolhe:
#   "usar_imagens": True   -> mostra 3 imagens
#   "usar_imagens": False  -> não mostra imagens e aumenta a pergunta
#
# Quando usar_imagens=True, coloque exatamente 3 caminhos em "imagens".
# Os rótulos das imagens são opcionais.
# ============================================================

QUIZZES = {
    "Corpo Humano": [
        {
            "pergunta": "Qual órgão bombeia o sangue por todo o corpo?",
            "alternativas": ["Pulmão", "Fígado", "Coração"],
            "correta": 2,
            "usar_imagens": True,
            "imagens": [
                "imagens_perguntas/pulmao.png",
                "imagens_perguntas/figado.png",
                "imagens_perguntas/coracao.png",
            ],
            "rotulos_imagens": ["Pulmão", "Fígado", "Coração"],
        },
        {
            "pergunta": "Qual órgão filtra o sangue e produz a urina?",
            "alternativas": ["Pâncreas", "Rim", "Baço"],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual parte do corpo protege o cérebro?",
            "alternativas": ["Costela", "Crânio", "Pulmão"],
            "correta": 1,
            "usar_imagens": True,
            "imagens": [
                "imagens_perguntas/costela.png",
                "imagens_perguntas/cranio.png",
                "imagens_perguntas/pulmao.png",
            ],
            "rotulos_imagens": ["Costela", "Crânio", "Pulmão"],
        },
    ],
}
