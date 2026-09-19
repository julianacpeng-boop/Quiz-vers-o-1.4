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

    "Curiosidades Gerais": [
        {
            "pergunta": "Qual é a capital da Austrália?",
            "alternativas": ["Sydney", "Canberra", "Melbourne"],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual é o maior oceano do planeta?",
            "alternativas": ["Pacífico", "Atlântico", "Índico"],
            "correta": 0,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual planeta é conhecido como Planeta Vermelho?",
            "alternativas": ["Vênus", "Júpiter", "Marte"],
            "correta": 2,
            "usar_imagens": False,
        },
    ],

    "Corpo Humano": [
        {
            "pergunta": "Qual órgão bombeia o sangue por todo o corpo?",
            "alternativas": ["Pulmão", "Coração", "Fígado"],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Quantos ossos tem, em geral, o corpo humano adulto?",
            "alternativas": ["206", "186", "226"],
            "correta": 0,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual gás o corpo humano utiliza na respiração?",
            "alternativas": ["Nitrogênio", "Hélio", "Oxigênio"],
            "correta": 2,
            "usar_imagens": False,
        },
    ],

    "Ciência do Dia a Dia": [
        {
            "pergunta": "A quantos graus Celsius a água congela, em condições comuns?",
            "alternativas": ["0 graus", "10 graus", "20 graus"],
            "correta": 0,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual mudança de estado ocorre quando um líquido passa para o estado gasoso?",
            "alternativas": ["Fusão", "Vaporização", "Solidificação"],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Ao nível do mar, aproximadamente a quantos graus Celsius a água ferve?",
            "alternativas": ["50 graus", "80 graus", "100 graus"],
            "correta": 2,
            "usar_imagens": False,
        },
    ],

}
