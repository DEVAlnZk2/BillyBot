"""
bot.py - Subsolo 57: Bot de NPCs para Discord (sem IA).

Cada conversa cadastrada em conversas.py vira um comando (ex.: !deuzebio).
O mestre digita o comando no canal de comandos e o bot publica a conversa
no canal do RPG. Os jogadores respondem clicando em botões, como numa roda
de diálogo de RPG. As regras da conversa ficam em motor.py.
"""

import os
import shutil
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import find_dotenv, load_dotenv

from conversas import CONVERSAS, validar_conversas
from motor import Sessao, aplicar_variaveis
from tts import Locutor, listar_vozes

# ----------------------------------------------------------------------
# PASSO 1 - Configuração
# ----------------------------------------------------------------------
CAMINHO_ENV = find_dotenv()
load_dotenv(CAMINHO_ENV, override=True)  # o .env tem prioridade sobre variáveis do sistema
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CANAL_COMANDOS_ID = int(os.getenv("CANAL_COMANDOS_ID", "0") or 0)  # onde o mestre digita
CANAL_RPG_ID = int(os.getenv("CANAL_RPG_ID", "0") or 0)            # onde o bot responde
VOZ_CANAL_ID = int(os.getenv("VOZ_CANAL_ID", "0") or 0)  # canal de voz do TTS (0 = desligado)
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg") or "ffmpeg"
TEMPO_LIMITE = 300  # segundos sem clicar até a conversa encerrar sozinha
PASTA_IMAGENS = Path(__file__).parent / "imagens"  # fotos de perfil dos NPCs
EXTENSOES_IMAGEM = (".png", ".jpg", ".jpeg", ".webp", ".gif")

intents = discord.Intents.default()
intents.message_content = True  # necessário para ler comandos com "!"
bot = commands.Bot(command_prefix="!", intents=intents)
locutor = Locutor(bot, VOZ_CANAL_ID, FFMPEG_PATH)


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
def localizar_avatar(chave, conversa):
    """Acha a foto de perfil do NPC. Retorna (arquivo_local, url); ambos podem ser None.

    Ordem de busca:
      1. campo "avatar" da conversa: um link (https://...) ou um caminho de arquivo;
      2. arquivo imagens/<comando>.png (ou .jpg, .jpeg, .webp, .gif).
    """
    avatar = conversa.get("avatar")
    if avatar and avatar.startswith(("http://", "https://")):
        return None, avatar
    if avatar:
        caminho = Path(__file__).parent / avatar
        return (caminho, None) if caminho.is_file() else (None, None)
    for extensao in EXTENSOES_IMAGEM:
        caminho = PASTA_IMAGENS / f"{chave}{extensao}"
        if caminho.is_file():
            return caminho, None
    return None, None


def nome_do(jogador):
    """Nome usado no lugar de {jogador}. Sem jogador marcado, vira 'viajante'."""
    return jogador.display_name if jogador else "viajante"


def montar_embed(conversa, no, jogador, reacao=None, encerrada=False, avatar_url=None):
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
        title=None if avatar_url else conversa["npc"],
        description="\n\n".join(partes) or "...",
        color=conversa.get("cor", 0x808080),
    )
    if avatar_url:
        # Foto de perfil redonda ao lado do nome, como num chat
        embed.set_author(name=conversa["npc"], icon_url=avatar_url)
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
    def __init__(self, conversa, jogador, canal_mestre=None, avatar_url=None):
        super().__init__(timeout=TEMPO_LIMITE)
        self.avatar_url = avatar_url
        self.voz = conversa.get("voz")  # None = este NPC não fala
        self.voz_aberta = False
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

    # ---- voz (TTS): só a "fala" é falada, nunca a narração ----
    def _usa_voz(self):
        return bool(self.voz) and locutor.ligado

    def _texto_falado(self):
        no = self.sessao.no
        texto = no.get("fala_tts") or no.get("fala") or ""
        return aplicar_variaveis(
            texto, self.conversa, nome_do(self.jogador), para_voz=True
        ).strip()

    async def abrir_voz(self):
        """Chamado quando a conversa é publicada: entra no canal e fala a 1ª carta."""
        if not self._usa_voz():
            return
        self.voz_aberta = True
        locutor.abrir()
        self._falar_agora()

    def _falar_agora(self):
        texto = self._texto_falado()
        if self.voz_aberta and texto:
            locutor.falar_em_segundo_plano(texto, self.voz)

    def _fechar_voz(self):
        if self.voz_aberta:
            self.voz_aberta = False
            locutor.fechar()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Com jogador marcado, só ele clica. Sem marcar, qualquer um pode."""
        if self.jogador and interaction.user.id != self.jogador.id:
            await interaction.response.send_message(
                "Essa conversa não é sua.", ephemeral=True
            )
            return False
        return True

    async def escolher(self, interaction: discord.Interaction, indice):
        passos_antes = len(self.sessao.caminho)
        continua = self.sessao.escolher(indice)
        embed = montar_embed(
            self.conversa,
            self.sessao.no,
            self.jogador,
            reacao=self.sessao.reacao,
            encerrada=not continua,
            avatar_url=self.avatar_url,
        )
        if continua:
            self._montar_botoes()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=None)

        # Só fala se mudou de carta (clicar em "Encerrar" não repete a fala)
        if len(self.sessao.caminho) > passos_antes:
            self._falar_agora()

        if not continua:
            await self._avisar_mestre("terminou")
            self._fechar_voz()
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
        embed = montar_embed(
            self.conversa, self.sessao.no, self.jogador,
            encerrada=True, avatar_url=self.avatar_url,
        )
        try:
            await self.mensagem.edit(embed=embed, view=None)
        except discord.HTTPException:
            pass
        await self._avisar_mestre("expirou por falta de resposta")
        self._fechar_voz()


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

    # Foto de perfil: arquivo local vai anexado à mensagem; link vai direto no embed
    arquivo, avatar_url = localizar_avatar(chave, conversa)
    extras = {}
    if arquivo:
        nome_anexo = f"avatar{arquivo.suffix.lower()}"
        extras["file"] = discord.File(arquivo, filename=nome_anexo)
        avatar_url = f"attachment://{nome_anexo}"

    view = DialogoView(conversa, jogador, canal_mestre, avatar_url)
    embed = montar_embed(conversa, view.sessao.no, jogador, avatar_url=avatar_url)
    try:
        view.mensagem = await canal.send(embed=embed, view=view, **extras)
    except discord.Forbidden:
        await ctx.send("O bot não tem permissão para escrever no canal do RPG.")
        return

    await view.abrir_voz()

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


@bot.command(name="vozes", help="Lista as vozes TTS em português do Brasil.")
async def comando_vozes(ctx):
    try:
        vozes = await listar_vozes("pt-BR")
    except Exception as erro:
        await ctx.send(f"Não consegui listar as vozes: {erro}")
        return
    linhas = [f"`{v['ShortName']}` ({v['Gender']})" for v in vozes]
    await ctx.send(
        "Vozes disponíveis. Use o nome em `\"voz\": {\"nome\": ...}`:\n" + "\n".join(linhas)
    )


@bot.command(
    name="testarvoz",
    help="Testa a voz de um NPC no canal de voz. Uso: !testarvoz <comando>",
)
async def testar_voz(ctx, chave: str = None):
    if not locutor.ligado:
        await ctx.send("A voz está desligada. Defina VOZ_CANAL_ID no .env.")
        return
    conversa = CONVERSAS.get((chave or "").lower())
    if conversa is None or not conversa.get("voz"):
        await ctx.send("Use: `!testarvoz <comando>`. O NPC precisa ter o campo `voz`.")
        return
    no = conversa["nos"][conversa["inicio"]]
    texto = aplicar_variaveis(
        no.get("fala_tts") or no.get("fala") or "", conversa, "viajante", para_voz=True
    ).strip()
    if not texto:
        await ctx.send("A primeira carta desse NPC não tem fala para testar.")
        return
    locutor.abrir()
    locutor.falar_em_segundo_plano(texto, conversa["voz"])
    locutor.fechar()  # o bot sai do canal depois de falar
    await ctx.send(f"Falando a primeira fala de **{conversa['npc']}** no canal de voz.")


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

    com_foto, sem_foto = [], []
    for _chave, _conversa in CONVERSAS.items():
        arquivo, url = localizar_avatar(_chave, _conversa)
        (com_foto if (arquivo or url) else sem_foto).append(_chave)
        if _conversa.get("avatar") and not (arquivo or url):
            print(f"Aviso: o avatar '{_conversa['avatar']}' de '{_chave}' não foi encontrado.")
    print("NPCs com foto:", ", ".join(com_foto) or "nenhum")
    if sem_foto:
        print("NPCs sem foto (coloque imagens/<comando>.png):", ", ".join(sem_foto))

    if locutor.ligado:
        if shutil.which(FFMPEG_PATH) is None and not Path(FFMPEG_PATH).is_file():
            print(f"Aviso: FFmpeg não encontrado ('{FFMPEG_PATH}'). A voz não vai funcionar.")
        falantes = [chave for chave, conv in CONVERSAS.items() if conv.get("voz")]
        print("Voz TTS ligada. NPCs com voz:", ", ".join(falantes) or "nenhum")
    else:
        print("Voz TTS desligada (defina VOZ_CANAL_ID no .env para ligar).")

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
