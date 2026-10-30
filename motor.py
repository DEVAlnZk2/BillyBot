"""
motor.py - Regras das conversas (nenhuma linha de Discord aqui).

Separar as regras do Discord permite testar a lógica sozinha e, no futuro,
encaixar a leitura de ficha e o TTS sem mexer nos botões.
"""

from collections import Counter

RESULTADO = "@resultado"


def aplicar_variaveis(texto, conversa, nome_jogador):
    """Troca {jogador} e as {variaveis} da conversa pelos valores reais."""
    texto = texto.replace("{jogador}", nome_jogador)
    for chave, valor in conversa.get("variaveis", {}).items():
        texto = texto.replace("{" + chave + "}", str(valor))
    return texto


class Sessao:
    """Estado de UMA conversa em andamento (nó atual, pontos, opções já usadas)."""

    def __init__(self, conversa):
        self.conversa = conversa
        self.no_atual = conversa["inicio"]
        self.pontos = Counter()   # pontos por abordagem (pacifica, normal, ...)
        self.usadas = set()       # (nó, índice) das opções "uma_vez" já escolhidas
        self.reacao = None        # narração curta que abre o próximo nó
        self.encerrada = False
        self.caminho = [self.no_atual]

    @property
    def no(self):
        return self.conversa["nos"][self.no_atual]

    def opcoes_visiveis(self):
        """Opções que devem aparecer como botão: lista de (índice, opção)."""
        visiveis = []
        for indice, opcao in enumerate(self.no.get("opcoes", [])):
            if opcao.get("uma_vez") and (self.no_atual, indice) in self.usadas:
                continue
            visiveis.append((indice, opcao))
        return visiveis

    def escolher(self, indice):
        """Aplica a opção clicada. Retorna True se a conversa continua."""
        opcao = self.no["opcoes"][indice]

        if opcao.get("abordagem"):
            self.pontos[opcao["abordagem"]] += 1
        if opcao.get("uma_vez"):
            self.usadas.add((self.no_atual, indice))
        self.reacao = opcao.get("reacao")

        proximo = opcao["proximo"]
        if proximo == RESULTADO:
            proximo = self.resultado()

        if proximo is None:  # o jogador escolheu encerrar
            self.encerrada = True
            return False

        self.no_atual = proximo
        self.caminho.append(proximo)

        if not self.opcoes_visiveis():  # nó final (sem botões)
            self.encerrada = True
            return False
        return True

    def resultado(self):
        """Decide o nó final pela maior pontuação; empate no topo usa 'empate'."""
        cfg = self.conversa["pontuacao"]
        placar = {cat: self.pontos.get(cat, 0) for cat in cfg["destinos"]}
        maior = max(placar.values())
        lideres = [cat for cat, pontos in placar.items() if pontos == maior]
        escolhido = lideres[0] if len(lideres) == 1 else cfg["empate"]
        return cfg["destinos"][escolhido]

    def resumo(self):
        """Texto curto para o mestre saber como a conversa terminou."""
        linhas = [f"Caminho: {' > '.join(self.caminho)}"]
        cfg = self.conversa.get("pontuacao")
        if cfg:
            placar = " | ".join(
                f"{cat} {self.pontos.get(cat, 0)}" for cat in cfg["destinos"]
            )
            linhas.append(f"Placar: {placar}")
        return "\n".join(linhas)
