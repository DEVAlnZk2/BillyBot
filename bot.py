"""
bot.py - Subsolo 57: Bot de NPCs para Discord (sem IA).

Cada conversa cadastrada em conversas.py vira um comando (ex.: !stefano).
O jogador conversa clicando em botões, como numa roda de diálogo de RPG.
"""

import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from conversas import CONVERSAS, validar_conversas

# ----------------------------------------------------------------------
# PASSO 1 - Configuração
# ----------------------------------------------------------------------
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CANAL_COMANDOS_ID = int(os.getenv("CANAL_COMANDOS_ID", "0") or 0)

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
def montar_embed(conversa, no, jogador, encerrada=False):
    texto = no["fala"].replace("{jogador}", jogador.display_name)
    embed = discord.Embed(
        title=conversa["npc"],
        description=texto,
        color=conversa.get("cor", 0x808080),
    )
    if conversa.get("imagem"):
        embed.set_thumbnail(url=conversa["imagem"])

    rodape = f"Conversa com {jogador.display_name}"
    if encerrada:
        rodape += " • Conversa encerrada"
    embed.set_footer(text=rodape)
    return embed


# ----------------------------------------------------------------------
# PASSO 4 - Botões de resposta e controle da conversa
# ----------------------------------------------------------------------
class BotaoOpcao(discord.ui.Button):
    def __init__(self, texto, proximo, indice):
        super().__init__(
            label=texto[:80],
            style=discord.ButtonStyle.secondary,
            row=indice // 5,  # até 5 botões por linha
        )
        self.proximo = proximo

    async def callback(self, interaction: discord.Interaction):
        await self.view.avancar(interaction, self.proximo)


class DialogoView(discord.ui.View):
    def __init__(self, conversa, jogador, no_atual):
        super().__init__(timeout=300)  # 5 minutos sem clicar encerra a conversa
        self.conversa = conversa
        self.jogador = jogador
        self.no_atual = no_atual
        self.mensagem = None
        self._montar_botoes()

    def _montar_botoes(self):
        self.clear_items()
        opcoes = self.conversa["nos"][self.no_atual].get("opcoes", [])
        for i, opcao in enumerate(opcoes):
            self.add_item(BotaoOpcao(opcao["texto"], opcao["proximo"], i))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Só o jogador que iniciou a conversa pode clicar nos botões."""
        if interaction.user.id != self.jogador.id:
            await interaction.response.send_message(
                "Essa conversa não é sua. Use o comando para iniciar a sua.",
                ephemeral=True,
            )
            return False
        return True

    async def _finalizar(self, interaction):
        no = self.conversa["nos"][self.no_atual]
        embed = montar_embed(self.conversa, no, self.jogador, encerrada=True)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    async def avancar(self, interaction: discord.Interaction, proximo):
        # "proximo" None = jogador escolheu encerrar
        if proximo is None:
            await self._finalizar(interaction)
            return

        self.no_atual = proximo
        no = self.conversa["nos"][proximo]

        # Nó sem opções = nó final
        if not no.get("opcoes"):
            await self._finalizar(interaction)
            return

        self._montar_botoes()
        embed = montar_embed(self.conversa, no, self.jogador)
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        if self.mensagem is None:
            return
        no = self.conversa["nos"][self.no_atual]
        embed = montar_embed(self.conversa, no, self.jogador, encerrada=True)
        try:
            await self.mensagem.edit(embed=embed, view=None)
        except discord.HTTPException:
            pass


# ----------------------------------------------------------------------
# PASSO 5 - Comandos: um por conversa cadastrada
# ----------------------------------------------------------------------
async def iniciar_conversa(ctx, chave):
    conversa = CONVERSAS[chave]
    no_inicial = conversa["inicio"]
    view = DialogoView(conversa, ctx.author, no_inicial)
    embed = montar_embed(conversa, conversa["nos"][no_inicial], ctx.author)
    view.mensagem = await ctx.send(embed=embed, view=view)


def registrar_comando(chave):
    # Função separada para cada comando guardar o seu próprio "chave"
    @bot.command(name=chave, help=CONVERSAS[chave]["descricao"])
    async def comando(ctx):
        await iniciar_conversa(ctx, chave)


for _chave in CONVERSAS:
    registrar_comando(_chave)


@bot.command(name="conversas", help="Lista as conversas disponíveis.")
async def listar_conversas(ctx):
    linhas = [f"`!{chave}` - {c['descricao']}" for chave, c in CONVERSAS.items()]
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

    bot.run(TOKEN)
