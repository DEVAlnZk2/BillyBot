"""
conversas.py - Banco de conversas (NPCs) do bot Subsolo 57.

Este arquivo só guarda DADOS. Para criar uma nova conversa, basta copiar um
bloco dentro de CONVERSAS e mudar os textos. Não é preciso mexer no bot.py.

Estrutura de uma conversa:

    "comando": {                       # vira o comando !comando no Discord
        "npc": "Nome do NPC",          # título do embed
        "descricao": "Texto da lista", # aparece em !conversas
        "cor": 0xAABBCC,               # cor da barra lateral do embed
        "imagem": "https://...",       # (opcional) miniatura do NPC
        "inicio": "inicio",            # nome do primeiro nó
        "nos": {
            "inicio": {
                "fala": "O que o NPC diz. Use {jogador} para o nome do jogador.",
                "opcoes": [
                    {"texto": "O que o jogador pode responder", "proximo": "outro_no"},
                    {"texto": "Encerrar a conversa", "proximo": None},
                ],
            },
        },
    }

Regras:
- "proximo": None encerra a conversa.
- Um nó SEM opções (lista vazia) é um nó final: mostra a fala e encerra.
- Cada nó aceita até 25 opções; cada texto de opção, até 80 caracteres.
- O nome do comando deve ser minúsculo e sem espaços.
"""

CONVERSAS = {
    # ------------------------------------------------------------------
    # CONVERSA 1: Stefano Sero (autor do bilhete do portão 57)
    # ------------------------------------------------------------------
    "stefano": {
        "npc": "Stefano Sero",
        "descricao": "Conversar com Stefano Sero, autor do bilhete do portão 57.",
        "cor": 0xC8761A,
        "inicio": "inicio",
        "nos": {
            "inicio": {
                "fala": (
                    "*O homem ergue os olhos, cansado, e ajeita a mochila nas costas.*\n\n"
                    "Ei, {jogador}... você também veio lá de baixo, não foi? "
                    "Dá pra ver pela poeira nas suas roupas."
                ),
                "opcoes": [
                    {"texto": "Quem é você?", "proximo": "quem_sou"},
                    {"texto": "Quanto tempo se passou?", "proximo": "anos"},
                    {"texto": "Está procurando alguém?", "proximo": "esposa"},
                    {"texto": "Preciso ir.", "proximo": None},
                ],
            },
            "quem_sou": {
                "fala": (
                    "Stefano Sero. Fui eu que deixei o bilhete na porta do terminal "
                    "do portão 57. A câmara de criogenia me jogou pra fora do mesmo "
                    "jeito que fez com você, pelo visto."
                ),
                "opcoes": [
                    {"texto": "Está procurando alguém?", "proximo": "esposa"},
                    {"texto": "Voltar ao início da conversa.", "proximo": "inicio"},
                    {"texto": "Encerrar.", "proximo": None},
                ],
            },
            "anos": {
                "fala": (
                    "Pelo que ouvi dos sobreviventes... cento e vinte e cinco anos. "
                    "Eu também não quis acreditar. O mundo lá em cima não é o que a "
                    "gente imaginava quando entrou naquelas câmaras."
                ),
                "opcoes": [
                    {"texto": "Como é o mundo lá em cima?", "proximo": "mundo"},
                    {"texto": "Voltar ao início da conversa.", "proximo": "inicio"},
                ],
            },
            "mundo": {
                "fala": (
                    "Mutações, {jogador}. Elas acabaram com quem ficou no solo. "
                    "Quem sobreviveu se juntou em clãs: uns tentam reconstruir, "
                    "outros combatem as pragas, e tem facções cobrando pedágio dos "
                    "que sobraram. Cada subsolo tem um número, e o nosso é o 57."
                ),
                "opcoes": [
                    {"texto": "Voltar ao início da conversa.", "proximo": "inicio"},
                    {"texto": "Encerrar.", "proximo": None},
                ],
            },
            "esposa": {
                "fala": (
                    "Minha esposa. Cabelo castanho, bem comprido, camiseta preta e "
                    "jaqueta. Só encontrei a câmara dela aberta... Ouvi dizer que "
                    "alguém assim foi vista perto de uma cidade aqui por perto."
                ),
                "opcoes": [
                    {"texto": "Que cidade?", "proximo": "cidade"},
                    {"texto": "Vou ficar de olho.", "proximo": "promessa"},
                    {"texto": "Voltar ao início da conversa.", "proximo": "inicio"},
                ],
            },
            "cidade": {
                "fala": (
                    "Dizem que está cheia de gente abrigada, mas tem algo errado "
                    "ali. Uma maldição, ou alguém puxando as cordas. Não sei qual "
                    "das duas coisas me assusta mais."
                ),
                "opcoes": [
                    {"texto": "Vou ficar de olho.", "proximo": "promessa"},
                    {"texto": "Voltar ao início da conversa.", "proximo": "inicio"},
                ],
            },
            "promessa": {
                "fala": (
                    "Obrigado, {jogador}. Se encontrar ela, diga que estou vivo e "
                    "que estou atrás dela. Boa sorte lá fora."
                ),
                "opcoes": [],  # nó final
            },
        },
    },
    # ------------------------------------------------------------------
    # CONVERSA 2: Sobrevivente errante
    # ------------------------------------------------------------------
    "sobrevivente": {
        "npc": "Sobrevivente Errante",
        "descricao": "Falar com o sobrevivente que vaga pelas ruínas perto do Subsolo 57.",
        "cor": 0x5B6B4A,
        "inicio": "inicio",
        "nos": {
            "inicio": {
                "fala": (
                    "*Uma figura coberta de poeira surge entre os escombros, "
                    "mantendo a distância.*\n\n"
                    "Calma, {jogador}. Eu não mordo. O que faz sozinho por aqui?"
                ),
                "opcoes": [
                    {"texto": "Preciso de informações sobre a cidade.", "proximo": "cidade"},
                    {"texto": "Procuro uma mulher de cabelo castanho comprido.", "proximo": "mulher"},
                    {"texto": "Não é da sua conta.", "proximo": "grosso"},
                    {"texto": "Ir embora.", "proximo": None},
                ],
            },
            "cidade": {
                "fala": (
                    "Tem gente demais lá dentro e comida de menos. Ouvi dizer que "
                    "algo ali anda mexendo com a cabeça das pessoas. Se eu fosse "
                    "você, chegava com cuidado."
                ),
                "opcoes": [
                    {"texto": "Procuro uma mulher de cabelo castanho comprido.", "proximo": "mulher"},
                    {"texto": "Voltar ao início da conversa.", "proximo": "inicio"},
                ],
            },
            "mulher": {
                "fala": (
                    "Camiseta preta, jaqueta, cabelo comprido? Vi alguém assim "
                    "rondando perto dessa cidadezinha. Não cheguei perto para "
                    "confirmar. Num mundo desses, a gente aprende a não se meter."
                ),
                "opcoes": [
                    {"texto": "Obrigado pela dica.", "proximo": "despedida"},
                    {"texto": "Voltar ao início da conversa.", "proximo": "inicio"},
                ],
            },
            "grosso": {
                "fala": (
                    "*Ele levanta as mãos, recuando devagar.*\n\n"
                    "Tá bom, tá bom. Só tentei ser educado. Boa sorte aí."
                ),
                "opcoes": [],  # nó final
            },
            "despedida": {
                "fala": "Boa sorte, {jogador}. Que as mutações passem longe do seu caminho.",
                "opcoes": [],  # nó final
            },
        },
    },
}


def validar_conversas():
    """Procura erros comuns ao editar CONVERSAS. Retorna uma lista de mensagens."""
    erros = []
    for chave, conversa in CONVERSAS.items():
        if chave != chave.lower() or " " in chave:
            erros.append(f"[{chave}] o nome do comando deve ser minúsculo e sem espaços.")

        nos = conversa.get("nos", {})
        if conversa.get("inicio") not in nos:
            erros.append(f"[{chave}] o nó inicial '{conversa.get('inicio')}' não existe.")

        for nome_no, no in nos.items():
            opcoes = no.get("opcoes", [])
            if len(opcoes) > 25:
                erros.append(f"[{chave}/{nome_no}] mais de 25 opções.")
            for opcao in opcoes:
                if len(opcao["texto"]) > 80:
                    erros.append(f"[{chave}/{nome_no}] opção com mais de 80 caracteres.")
                proximo = opcao["proximo"]
                if proximo is not None and proximo not in nos:
                    erros.append(
                        f"[{chave}/{nome_no}] aponta para o nó '{proximo}', que não existe."
                    )
    return erros
