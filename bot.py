"""
bot.py - Subsolo 57: Bot de NPCs para Discord (sem IA).

Cada conversa cadastrada em conversas.py vira um comando (ex.: !deuzebio).
O mestre digita o comando no canal de comandos e o bot publica a conversa
no canal do RPG. Os jogadores respondem clicando em botões, como numa roda
de diálogo de RPG. As regras da conversa ficam em motor.py.
"""

import os

import discord
from discord.ext import commands
from dotenv import find_dotenv, load_dotenv

from conversas import CONVERSAS, validar_conversas
from motor import Sessao, aplicar_variaveis

# ----------------------------------------------------------------------
# PASSO 1 - Configuração
# ----------------------------------------------------------------------
CAMINHO_ENV = find_dotenv()
load_dotenv(CAMINHO_ENV, override=True)  # o .env tem prioridade sobre variáveis do sistema
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CANAL_COMANDOS_ID = int(os.getenv("CANAL_COMANDOS_ID", "0") or 0)  # onde o mestre digita
CANAL_RPG_ID = int(os.getenv("CANAL_RPG_ID", "0") or 0)            # onde o bot responde
TEMPO_LIMITE = 300  # segundos sem clicar até a conversa encerrar sozinha

intents = discord.Intents.default()
intents.message_content = True  # necessário para ler comandos com "!"
bot = commands.Bot(command_prefix="!", intents=intents)


# ----------------------------------------------------------------------
# PASSO 2 - Restrição ao canal de comandos do mestre
# ----------------------------------------------------------------------
@bot.check
async def somente_canal_de_comandos(ctx):
    """Se CANAL_COMANDOS_ID for 0, o bot funciona em qualquer canal."""
    return CANAL_COMANDOS_ID == 0 or ctx.channel.id == CANAL_COMANDOS_ID


# ----------------------------------------------------------------------
# PASSO 3 - Monta o embed (a "caixa de fala" do NPC)
# ----------------------------------------------------------------------
def nome_do(jogador):
    """Nome usado no lugar de {jogador}. Sem jogador marcado, vira 'viajante'."""
    return jogador.display_name if jogador else "viajante"


def montar_embed(conversa, no, jogador, reacao=None, encerrada=False):
    def v(texto):
        return aplicar_variaveis(texto, conversa, nome_do(jogador))

    partes = []

    # Narração (em itálico): a reação à resposta anterior + a cena do nó.
    # O TTS futuro NÃO vai ler esta parte.
    narracao = " ".join(t for t in (reacao, no.get("narracao")) if t)
    if narracao:
        partes.append(f"*{v(narracao)}*")

    # Fala do NPC: é só isto que o TTS futuro vai ler.
    if no.get("fala"):
        partes.append(v(no["fala"]))

    if no.get("narracao_final"):
        partes.append(f"*{v(no['narracao_final'])}*")

    embed = discord.Embed(
        title=conversa["npc"],
        description="\n\n".join(partes) or "...",
        color=conversa.get("cor", 0x808080),
    )
    if conversa.get("imagem"):
        embed.set_thumbnail(url=conversa["imagem"])

    if no.get("itens"):
        embed.add_field(
            name="Itens obtidos",
            value="\n".join(f"• {v(item)}" for item in no["itens"]),
            inline=False,
        )

    rodape = f"Conversa com {jogador.display_name}" if jogador else "Conversa aberta a todos"
    if encerrada:
        rodape += " • Conversa encerrada"
    embed.set_footer(text=rodape)
    return embed


# ----------------------------------------------------------------------
# PASSO 4 - Botões de resposta e controle da conversa
# ----------------------------------------------------------------------
class BotaoOpcao(discord.ui.Button):
    def __init__(self, texto, indice, posicao):
        super().__init__(
            label=texto[:80],
            style=discord.ButtonStyle.secondary,
            row=posicao // 5,  # até 5 botões por linha
        )
        self.indice = indice  # posição da opção dentro do nó

    async def callback(self, interaction: discord.Interaction):
        await self.view.escolher(interaction, self.indice)


class DialogoView(discord.ui.View):
    def __init__(self, conversa, jogador, canal_mestre=None):
        super().__init__(timeout=TEMPO_LIMITE)
        self.conversa = conversa
        self.jogador = jogador            # None = qualquer pessoa pode responder
        self.canal_mestre = canal_mestre  # recebe o relatório ao fim (ou None)
        self.sessao = Sessao(conversa)
        self.mensagem = None
        self._montar_botoes()

    def _montar_botoes(self):
        self.clear_items()
        nome = nome_do(self.jogador)
        for posicao, (indice, opcao) in enumerate(self.sessao.opcoes_visiveis()):
            texto = aplicar_variaveis(opcao["texto"], self.conversa, nome)
            self.add_item(BotaoOpcao(texto, indice, posicao))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Com jogador marcado, só ele clica. Sem marcar, qualquer um pode."""
        if self.jogador and interaction.user.id != self.jogador.id:
            await interaction.response.send_message(
                "Essa conversa não é sua.", ephemeral=True
            )
            return False
        return True

    async def escolher(self, interaction: discord.Interaction, indice):
        continua = self.sessao.escolher(indice)
        embed = montar_embed(
            self.conversa,
            self.sessao.no,
            self.jogador,
            reacao=self.sessao.reacao,
            encerrada=not continua,
        )
        if continua:
            self._montar_botoes()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=None)
            await self._avisar_mestre("terminou")
            self.stop()

    async def _avisar_mestre(self, motivo):
        """Relatório privado no canal de comandos (só se for outro canal)."""
        if self.canal_mestre is None:
            return
        texto = (
            f"Conversa **{self.conversa['npc']}** com **{nome_do(self.jogador)}** "
            f"{motivo}.\n{self.sessao.resumo()}"
        )
        try:
            await self.canal_mestre.send(texto)
        except discord.HTTPException:
            pass

    async def on_timeout(self):
        if self.mensagem is None:
            return
        embed = montar_embed(self.conversa, self.sessao.no, self.jogador, encerrada=True)
        try:
            await self.mensagem.edit(embed=embed, view=None)
        except discord.HTTPException:
            pass
        await self._avisar_mestre("expirou por falta de resposta")


# ----------------------------------------------------------------------
# PASSO 5 - Comandos: um por conversa cadastrada
# ----------------------------------------------------------------------
async def iniciar_conversa(ctx, chave, jogador=None):
    conversa = CONVERSAS[chave]

    # Sem CANAL_RPG_ID, a conversa aparece no mesmo canal do comando.
    canal = bot.get_channel(CANAL_RPG_ID) if CANAL_RPG_ID else ctx.channel
    if canal is None:
        await ctx.send(
            "Não encontrei o canal do RPG. Confira o CANAL_RPG_ID no .env "
            "e se o bot tem acesso a esse canal."
        )
        return

    # O relatório só vai ao mestre se a conversa for publicada em outro canal,
    # senão os jogadores veriam o placar.
    canal_mestre = ctx.channel if canal.id != ctx.channel.id else None

    view = DialogoView(conversa, jogador, canal_mestre)
    embed = montar_embed(conversa, view.sessao.no, jogador)
    try:
        view.mensagem = await canal.send(embed=embed, view=view)
    except discord.Forbidden:
        await ctx.send("O bot não tem permissão para escrever no canal do RPG.")
        return

    if canal_mestre is not None:
        await ctx.send(f"Conversa **{conversa['npc']}** publicada em {canal.mention}.")


def registrar_comando(chave):
    # Função separada para cada comando guardar o seu próprio "chave"
    @bot.command(
        name=chave,
        help=f"{CONVERSAS[chave]['descricao']} Uso: !{chave} [@jogador]",
    )
    async def comando(ctx, jogador: discord.Member = None):
        await iniciar_conversa(ctx, chave, jogador)


for _chave in CONVERSAS:
    registrar_comando(_chave)


@bot.command(name="conversas", help="Lista as conversas disponíveis.")
async def listar_conversas(ctx):
    linhas = [f"`!{chave} [@jogador]` - {c['descricao']}" for chave, c in CONVERSAS.items()]
    embed = discord.Embed(
        title="Conversas disponíveis",
        description="\n".join(linhas),
        color=0x2F3136,
    )
    await ctx.send(embed=embed)


# ----------------------------------------------------------------------
# PASSO 6 - Eventos
# ----------------------------------------------------------------------
@bot.event
async def on_ready():
    print(f"Bot online como {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return  # ignora mensagens que começam com "!" mas não são comandos
    if isinstance(error, commands.CheckFailure):
        canal = bot.get_channel(CANAL_COMANDOS_ID)
        destino = canal.mention if canal else "o canal de comandos"
        await ctx.send(
            f"{ctx.author.mention}, use {destino} para conversar com os NPCs.",
            delete_after=8,
        )
        return
    if isinstance(error, commands.BadArgument):
        await ctx.send(
            "Não encontrei esse jogador. Marque com @ ou deixe sem marcar "
            "para liberar a conversa a todos.",
            delete_after=10,
        )
        return
    raise error


# ----------------------------------------------------------------------
# PASSO 7 - Inicialização (valida as conversas antes de ligar o bot)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    erros = validar_conversas()
    if erros:
        print("Erros encontrados em conversas.py:")
        for erro in erros:
            print(" -", erro)
        raise SystemExit(1)

    if not TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN não encontrado. Confira o arquivo .env")

    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("Token recusado pelo Discord (401).")
        print(f"  .env usado: {CAMINHO_ENV or 'NENHUM ENCONTRADO'}")
        print(f"  tamanho do token: {len(TOKEN)} | pontos: {TOKEN.count('.')}")
        print("  Um token de bot costuma ter ~70 caracteres e 2 pontos.")
        raise SystemExit(
            "Gere um novo em Developer Portal > Bot > Reset Token, cole no "
            ".env sem aspas nem espaços e tente novamente."
        )
