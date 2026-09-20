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

    "Eleições 2026": [
        {
            "pergunta": "Em qual data acontece o primeiro turno das Eleições 2026?",
            "alternativas": [
                "4 de outubro",
                "11 de outubro",
                "25 de outubro"
            ],
            "correta": 0,
            "usar_imagens": False,
        },
        {
            "pergunta": "Quantas escolhas para senador o eleitor fará nas Eleições 2026?",
            "alternativas": [
                "Uma",
                "Duas",
                "Três"
            ],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual destes cargos NÃO está em disputa nas Eleições Gerais de 2026?",
            "alternativas": [
                "Presidente",
                "Governador",
                "Prefeito"
            ],
            "correta": 2,
            "usar_imagens": False,
        },
    ],

    "A Fazenda 18": [
        {
            "pergunta": "Quem apresenta A Fazenda 18?",
            "alternativas": [
                "Ana Hickmann",
                "Ticiane Pinheiro",
                "Adriane Galisteu"
            ],
            "correta": 2,
            "usar_imagens": False,
        },
        {
            "pergunta": "Em qual dia A Fazenda 18 estreou em 2026?",
            "alternativas": [
                "7 de setembro",
                "14 de setembro",
                "21 de setembro"
            ],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Em qual cidade fica a sede de A Fazenda 18?",
            "alternativas": [
                "Itapecerica da Serra",
                "Campinas",
                "Rio de Janeiro"
            ],
            "correta": 0,
            "usar_imagens": False,
        },
    ],

    "Relacionamento": [
        {
            "pergunta": "Qual atitude demonstra melhor uma escuta ativa no relacionamento?",
            "alternativas": [
                "Interromper a pessoa",
                "Ouvir e fazer perguntas",
                "Mudar de assunto"
            ],
            "correta": 1,
            "usar_imagens": False,
        },
        {
            "pergunta": "Em um relacionamento, o consentimento deve ser como?",
            "alternativas": [
                "Presumido",
                "Obrigatório",
                "Livre e contínuo"
            ],
            "correta": 2,
            "usar_imagens": False,
        },
        {
            "pergunta": "Qual atitude ajuda a resolver um mal-entendido entre um casal?",
            "alternativas": [
                "Conversar com clareza",
                "Ignorar para sempre",
                "Espalhar o problema para outras pessoas"
            ],
            "correta": 0,
            "usar_imagens": False,
        },
    ],

}
