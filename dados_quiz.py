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

    "Português": [
        {
            "pergunta": "Qual destas palavras está escrita corretamente?",
            "alternativas": ["Exceção", "Excessão", "Ecessão"],
            "correta": 0,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual é o plural correto da palavra cidadão?",
            "alternativas": ["Cidadões", "Cidadãos", "Cidadães"],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual destas palavras é um verbo?",
            "alternativas": ["Bonito", "Escola", "Correr"],
            "correta": 2,
            "usar_imagens": False,
        },
    ],

    "Matemática": [
        {
            "pergunta": "Quanto é 15 vezes 4?",
            "alternativas": ["60", "45", "75"],
            "correta": 0,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual é a metade de 250?",
            "alternativas": ["100", "125", "150"],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Quanto é 100 menos 25 vezes 2?",
            "alternativas": ["150", "75", "50"],
            "correta": 2,
            "usar_imagens": False,
        },
    ],

    "Histórias Bíblicas": [
        {
            "pergunta": "Quem construiu uma arca antes do grande dilúvio?",
            "alternativas": ["Moisés", "Noé", "Abraão"],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Quem derrotou Golias usando uma funda?",
            "alternativas": ["Davi", "Salomão", "Sansão"],
            "correta": 0,
            "usar_imagens": False,
        },
        {
            "pergunta": "Quem foi lançado na cova dos leões?",
            "alternativas": ["José", "Jonas", "Daniel"],
            "correta": 2,
            "usar_imagens": False,
        },
    ],

}
