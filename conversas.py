"""
conversas.py - Banco de conversas (NPCs) do bot Subsolo 57.

Este arquivo só guarda DADOS. Para criar uma nova conversa, copie um bloco
dentro de CONVERSAS e mude os textos. Não é preciso mexer no bot.py.

ESTRUTURA DE UMA CONVERSA

    "comando": {                         # vira o comando !comando no Discord
        "npc": "Nome do NPC",            # título do embed
        "descricao": "Texto da lista",   # aparece em !conversas
        "cor": 0xAABBCC,                 # cor da barra lateral
        "imagem": "https://...",         # (opcional) miniatura do NPC
        "variaveis": {"chave": "valor"}, # (opcional) usadas como {chave} nos textos
        "pontuacao": {...},              # (opcional) ver "ABORDAGENS" abaixo
        "inicio": "carta1",              # nome do primeiro nó
        "nos": { ... },
    }

ESTRUTURA DE UM NÓ (uma "carta" de diálogo)

    "carta1": {
        "narracao": "Descrição da cena (o TTS não vai falar).",   # opcional
        "fala": "O que o NPC diz (só isto será falado no TTS).",  # opcional
        "narracao_final": "Cena depois da fala.",                 # opcional
        "itens": ["Item que o jogador recebe"],                   # opcional
        "opcoes": [
            {
                "texto": "Resposta do jogador (botão, máx. 80 caracteres)",
                "proximo": "outro_no",
                "reacao": "Narração curta que abre o próximo nó.",  # opcional
                "abordagem": "pacifica",   # opcional: soma 1 ponto
                "uma_vez": True,           # opcional: o botão some depois de usado
            },
        ],
    }

REGRAS
- "proximo": None encerra a conversa.
- "proximo": "@resultado" calcula o final pela pontuação (ver abaixo).
- Nó com "opcoes": [] é final: mostra o texto e encerra.
- {jogador} vira o nome do jogador; {chave} vira o valor em "variaveis".
- Cada nó aceita até 25 opções.
- O nome do comando deve ser minúsculo e sem espaços.

ABORDAGENS (final decidido por pontos)

    "pontuacao": {
        "empate": "normal",    # categoria usada se houver empate no topo
        "destinos": {          # categoria -> nó final
            "pacifica": "final_pacifica",
            "normal": "final_normal",
            "agressiva": "final_agressiva",
        },
    }

Cada opção com "abordagem" soma 1 ponto na categoria. Quando uma opção aponta
para "@resultado", vence a categoria com mais pontos; se houver empate no
topo, vale a categoria definida em "empate".
"""

import re

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
                "narracao": "O homem ergue os olhos, cansado, e ajeita a mochila nas costas.",
                "fala": (
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
                "narracao": "Uma figura coberta de poeira surge entre os escombros, mantendo a distância.",
                "fala": "Calma, {jogador}. Eu não mordo. O que faz sozinho por aqui?",
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
                "narracao": "Ele levanta as mãos, recuando devagar.",
                "fala": "Tá bom, tá bom. Só tentei ser educado. Boa sorte aí.",
                "opcoes": [],  # nó final
            },
            "despedida": {
                "fala": "Boa sorte, {jogador}. Que as mutações passem longe do seu caminho.",
                "opcoes": [],  # nó final
            },
        },
    },
    # ------------------------------------------------------------------
    # CONVERSA 3: Deuzébio Barbosa (velho caído no portão do Subsolo 57)
    #
    # 5 cartas. Cada resposta soma 1 ponto em uma abordagem (pacifica,
    # normal ou agressiva) SEM que isso apareça escrito para o jogador.
    # Na carta 3 existe a opção "???" (diálogo secreto, uma tentativa).
    # ------------------------------------------------------------------
    "deuzebio": {
        "npc": "Deuzébio Barbosa",
        "descricao": "Encontrar o velho Deuzébio Barbosa, caído no portão do Subsolo 57.",
        "cor": 0xB5B09A,
        "variaveis": {"codigo_cofre": "5730"},  # troque pelo código real do cofre
        "pontuacao": {
            "empate": "normal",
            "destinos": {
                "pacifica": "final_pacifica",
                "normal": "final_normal",
                "agressiva": "final_agressiva",
            },
        },
        "inicio": "carta1",
        "nos": {
            # ---------------------------- CARTA 1
            "carta1": {
                "narracao": (
                    "No chão frio junto ao portão do Subsolo 57, um velho jaz de lado. "
                    "O jaleco branco, coberto de poeira, pende em seu corpo magro, e a "
                    "barba longa se espalha pelo peito. Ao notar sua presença, ele "
                    "tenta erguer a cabeça, sem forças."
                ),
                "fala": (
                    "Então uma delas falhou... Alguém finalmente acordou lá dentro. "
                    "Quem é você, guri?"
                ),
                "opcoes": [
                    {
                        "texto": "Calma, vovô. Não vou te machucar. Você está bem?",
                        "proximo": "carta2",
                        "abordagem": "pacifica",
                        "reacao": "Os olhos cansados do velho se suavizam por um instante.",
                    },
                    {
                        "texto": "Acabei de acordar e não entendo nada. Quem é você?",
                        "proximo": "carta2",
                        "abordagem": "normal",
                        "reacao": "O velho assente devagar, sem tirar os olhos de você.",
                    },
                    {
                        "texto": "Cala a boca, velho. Aqui quem pergunta sou eu.",
                        "proximo": "carta2",
                        "abordagem": "agressiva",
                        "reacao": "O velho solta uma risada seca e debochada.",
                    },
                ],
            },
            # ---------------------------- CARTA 2
            "carta2": {
                "narracao": (
                    "A tosse vem forte, e ele leva a mão trêmula ao pescoço, onde a "
                    "pele está escura e inchada."
                ),
                "fala": (
                    "Não perca tempo comigo. Uma barata do tamanho de um cachorro me "
                    "pegou no corredor. A coisa brilhava no escuro... Remédio pra isso "
                    "não existe, eu mesmo já tentei de tudo."
                ),
                "opcoes": [
                    {
                        "texto": "Então é questão de tempo. Fala logo o que sabe.",
                        "proximo": "carta3",
                        "abordagem": "agressiva",
                        "reacao": "O velho aperta o jaleco com os dedos magros.",
                    },
                    {
                        "texto": "Sinto muito. Ninguém merece morrer assim, sozinho.",
                        "proximo": "carta3",
                        "abordagem": "pacifica",
                        "reacao": "O velho desvia o olhar por um momento, em silêncio.",
                    },
                    {
                        "texto": "Isso explica o seu estado. Há quanto tempo está aqui?",
                        "proximo": "carta3",
                        "abordagem": "normal",
                        "reacao": "Ele solta um suspiro longo.",
                    },
                ],
            },
            # ---------------------------- CARTA 3 (com a opção secreta "???")
            "carta3": {
                "narracao": (
                    "Ele apoia a cabeça no chão e encara o teto, como se contasse as "
                    "luzes apagadas."
                ),
                "fala": (
                    "Vivi mais tempo neste buraco do que qualquer um de vocês. Conheço "
                    "cada corredor, cada porta, cada câmara... Diga, o que você quer de mim?"
                ),
                "opcoes": [
                    {
                        "texto": "Respostas. Onde estamos e o que aconteceu com o mundo?",
                        "proximo": "carta4",
                        "abordagem": "normal",
                        "reacao": "Ele estuda seu rosto por um longo tempo.",
                    },
                    {
                        "texto": "Tudo o que você tiver. Passa pra cá.",
                        "proximo": "carta4",
                        "abordagem": "agressiva",
                        "reacao": "O velho cerra o maxilar, sem forças para reagir.",
                    },
                    {
                        "texto": "Só quero ajudar. Posso ficar aqui com você.",
                        "proximo": "carta4",
                        "abordagem": "pacifica",
                        "reacao": "Ele quase sorri, surpreso.",
                    },
                    {
                        "texto": "???",
                        "proximo": "codigo",
                        "uma_vez": True,  # só uma tentativa de dizer o código
                    },
                ],
            },
            # ---------------------------- DIÁLOGO SECRETO: escolher o código
            "codigo": {
                "narracao": (
                    "O velho o encara em silêncio, como se esperasse ouvir uma "
                    "palavra específica."
                ),
                "opcoes": [
                    {"texto": "Dizer: Éden", "proximo": "codigo_errado"},
                    {"texto": "Dizer: Paraíso", "proximo": "segredo_1"},
                    {"texto": "Dizer: Aurora", "proximo": "codigo_errado"},
                ],
            },
            "codigo_errado": {
                "narracao": (
                    "O velho espera um instante e então balança a cabeça, sem saber "
                    "se desapontado ou aliviado."
                ),
                "fala": "Não sei do que está falando, guri. Deve ser a poeira nos seus ouvidos.",
                "opcoes": [
                    {"texto": "Continuar a conversa.", "proximo": "carta3"},
                ],
            },
            "segredo_1": {
                "narracao": (
                    "Quando a palavra deixa sua boca, o velho paralisa. Os olhos, antes "
                    "turvos, se arregalam. Ele tenta se erguer, mas só consegue virar o "
                    "rosto para você. A barba treme."
                ),
                "fala": (
                    "Essa palavra... Onde você ouviu essa palavra? Ninguém deveria "
                    "saber disso. Ninguém... Você sabe de onde ela vem, não sabe?"
                ),
                "opcoes": [
                    # Única opção: confrontar o velho
                    {
                        "texto": "Foi você quem nos prendeu naquelas câmaras. Quero a verdade.",
                        "proximo": "segredo_2",
                    },
                ],
            },
            "segredo_2": {
                "narracao": (
                    "O velho fica em silêncio por muito tempo, e algo se quebra em seu "
                    "rosto cansado. Quando fala, a voz é um fio."
                ),
                "fala": (
                    "Fui eu... Eu coordenava as pesquisas de criogenia. Paraíso foi o "
                    "nome que dei a tudo isso. Disse que vocês seriam cobaias, a próxima "
                    "etapa da evolução humana. Era mentira. Eu só queria vocês presos "
                    "naquele gelo, e quando o alarme tocou, esqueci de vocês como se "
                    "esquece uma porta trancada. Tentei fugir, e uma barata me alcançou "
                    "no corredor. Talvez seja o que mereço. Eu não devia ter feito isso "
                    "com vocês, guri. Não peço perdão. Pegue a chave do meu escritório, "
                    "no fim do corredor leste. Atrás do quadro com o mapa velho tem um "
                    "cofre escondido: o código é {codigo_cofre}. Há um pouco de dinheiro "
                    "de antes da guerra e uma pistola. Comece a sua jornada com algo na mão."
                ),
                "narracao_final": (
                    "Com esforço, ele estende uma chave de latão e a coloca na sua mão. "
                    "Depois fecha os olhos, e o peito sobe e desce cada vez mais devagar."
                ),
                "itens": [
                    "Chave do escritório de Deuzébio",
                    "Código do cofre escondido: {codigo_cofre}",
                ],
                "opcoes": [],  # nó final
            },
            # ---------------------------- CARTA 4
            "carta4": {
                "narracao": (
                    "A respiração do velho fica curta. Ao longe, um estalo metálico "
                    "ecoa pelos corredores, e ele estremece."
                ),
                "fala": (
                    "Ouviu isso? Eles ainda andam por aí... Lá fora é pior, guri. "
                    "Quando eu me for, este portão fica entregue a quem aparecer. E "
                    "você vai sair por ele. Acha que está pronto?"
                ),
                "opcoes": [
                    {
                        "texto": "Talvez não. Mas se você me ensinar, eu aprendo.",
                        "proximo": "carta5",
                        "abordagem": "pacifica",
                        "reacao": "O velho solta o ar devagar, quase em paz.",
                    },
                    {
                        "texto": "Eu me viro. Quem se preocupa com os outros morre primeiro.",
                        "proximo": "carta5",
                        "abordagem": "agressiva",
                        "reacao": "Ele balança a cabeça, desapontado.",
                    },
                    {
                        "texto": "Não estou, mas não tenho escolha. Vou descobrir sozinho.",
                        "proximo": "carta5",
                        "abordagem": "normal",
                        "reacao": "Ele concorda com um leve movimento de cabeça.",
                    },
                ],
            },
            # ---------------------------- CARTA 5 (decide o final)
            "carta5": {
                "narracao": (
                    "O velho fecha os olhos por alguns segundos. Quando volta a abri-los, "
                    "parece ter tomado uma decisão."
                ),
                "fala": (
                    "Estou cansado, guri. Resta pouco de mim, e você é a última pessoa "
                    "que vou ver. Então me diga: o que vai fazer comigo?"
                ),
                "opcoes": [
                    {
                        "texto": "Vou revistar seus bolsos. Você não vai precisar de nada disso.",
                        "proximo": "@resultado",
                        "abordagem": "agressiva",
                    },
                    {
                        "texto": "Nada. Só preciso seguir meu caminho. O que você sabe que me ajudaria?",
                        "proximo": "@resultado",
                        "abordagem": "normal",
                    },
                    {
                        "texto": "Não vou te matar. Descanse, eu fico aqui com você.",
                        "proximo": "@resultado",
                        "abordagem": "pacifica",
                    },
                ],
            },
            # ---------------------------- FINAIS
            "final_pacifica": {
                "narracao": (
                    "O velho tira de dentro do jaleco uma chave de latão presa a um "
                    "cordão e a entrega sem resistência, com um sorriso fraco."
                ),
                "fala": (
                    "Obrigado por não me deixar morrer como um cachorro, guri. Esta é a "
                    "chave do meu escritório, no fim do corredor leste. Lá dentro estão "
                    "os pip-boys: aparelhos de pulso que parecem brinquedo velho, mas "
                    "não são. Eles medem a radiação do ar, acompanham a sua saúde e "
                    "guardam mapas e o que você carrega. Lá em cima, a radiação e as "
                    "doenças matam sem avisar, e é o aparelho que avisa antes de ser "
                    "tarde. Sem um deles, ninguém dura uma semana. Leve um para cada um "
                    "que acordar."
                ),
                "narracao_final": "Ele fecha os olhos, e sua respiração se aquieta num sono tranquilo.",
                "itens": ["Chave do escritório de Deuzébio"],
                "opcoes": [],  # nó final
            },
            "final_normal": {
                "narracao": "O velho resmunga e tenta se apoiar no cotovelo, sem conseguir.",
                "fala": (
                    "Vocês, jovens... acordam num mundo de cabeça para baixo e já saem "
                    "exigindo respostas de quem mal consegue respirar. Mas deixa pra "
                    "lá. Dormiram sem saber por quê, e nem isso foi justo com vocês. "
                    "Pega. É a chave do meu escritório, no fim do corredor leste. Leve "
                    "o que achar útil. E guarde isto: lá em cima, a fome mata mais que "
                    "as mutações, e a confiança mata mais que a fome."
                ),
                "narracao_final": (
                    "Ele joga a chave perto da sua mão, vira o rosto para o teto e não "
                    "diz mais nada."
                ),
                "itens": ["Chave do escritório de Deuzébio"],
                "opcoes": [],  # nó final
            },
            "final_agressiva": {
                "narracao": (
                    "O velho o encara com um desprezo cansado, o peito subindo e "
                    "descendo com dificuldade."
                ),
                "fala": (
                    "É assim que vocês começam... Já vi gente como você antes. Faça o "
                    "que quiser com este corpo velho, guri, mas lembre-se: toda ação "
                    "tem consequência. Tudo o que você faz lá fora volta pra você. Às "
                    "vezes demora, às vezes não, mas volta. Lembre-se disso quando as "
                    "sombras lá em cima começarem a cobrar."
                ),
                "narracao_final": (
                    "Os olhos do velho se fecham e o peito para de se mover. Você "
                    "revista o jaleco imundo e encontra, no bolso interno, uma chave "
                    "pequena e desgastada, sem etiqueta. Não há mais ninguém para dizer "
                    "a que porta ela pertence."
                ),
                "itens": ["Uma chave pequena e desgastada (sem identificação)"],
                "opcoes": [],  # nó final
            },
        },
    },
}


PADRAO_VARIAVEL = re.compile(r"\{(\w+)\}")


def _textos_do_no(no):
    """Gera (campo, texto) de tudo o que o jogador pode ler em um nó."""
    for campo in ("narracao", "fala", "narracao_final"):
        if no.get(campo):
            yield campo, no[campo]
    for item in no.get("itens", []):
        yield "itens", item
    for opcao in no.get("opcoes", []):
        yield "opcao", opcao["texto"]
        if opcao.get("reacao"):
            yield "reacao", opcao["reacao"]


def validar_conversas():
    """Procura erros comuns ao editar CONVERSAS. Retorna uma lista de mensagens."""
    erros = []
    for chave, conversa in CONVERSAS.items():
        if chave != chave.lower() or " " in chave:
            erros.append(f"[{chave}] o nome do comando deve ser minúsculo e sem espaços.")

        nos = conversa.get("nos", {})
        pontuacao = conversa.get("pontuacao")
        variaveis = set(conversa.get("variaveis", {})) | {"jogador"}

        if conversa.get("inicio") not in nos:
            erros.append(f"[{chave}] o nó inicial '{conversa.get('inicio')}' não existe.")

        if pontuacao:
            destinos = pontuacao.get("destinos", {})
            if pontuacao.get("empate") not in destinos:
                erros.append(f"[{chave}] 'empate' precisa ser uma das categorias de 'destinos'.")
            for categoria, destino in destinos.items():
                if destino not in nos:
                    erros.append(f"[{chave}] o destino '{destino}' ({categoria}) não existe.")

        for nome_no, no in nos.items():
            local = f"[{chave}/{nome_no}]"
            opcoes = no.get("opcoes", [])

            if not no.get("fala") and not no.get("narracao"):
                erros.append(f"{local} o nó não tem 'fala' nem 'narracao'.")
            if len(opcoes) > 25:
                erros.append(f"{local} mais de 25 opções.")

            for campo, texto in _textos_do_no(no):
                for variavel in PADRAO_VARIAVEL.findall(texto):
                    if variavel not in variaveis:
                        erros.append(f"{local} usa {{{variavel}}} em '{campo}', mas ela não existe.")

            for opcao in opcoes:
                if len(opcao["texto"]) > 80:
                    erros.append(f"{local} opção com mais de 80 caracteres.")

                proximo = opcao["proximo"]
                if proximo == "@resultado":
                    if not pontuacao:
                        erros.append(f"{local} usa '@resultado', mas a conversa não tem 'pontuacao'.")
                elif proximo is not None and proximo not in nos:
                    erros.append(f"{local} aponta para o nó '{proximo}', que não existe.")

                abordagem = opcao.get("abordagem")
                if abordagem and (not pontuacao or abordagem not in pontuacao["destinos"]):
                    erros.append(f"{local} usa a abordagem '{abordagem}', que não está em 'pontuacao'.")
    return erros
