"""
tts.py - Voz dos NPCs (TTS).

O bot gera o áudio da fala com o edge-tts (vozes neurais da Microsoft, sem
chave de API) e toca no canal de voz com o FFmpeg. Só a "fala" é falada:
narração, reação e itens nunca passam por aqui.

Como o bot usa:
    locutor.abrir()                              # uma conversa começou
    locutor.falar_em_segundo_plano(texto, voz)   # fala (interrompe a anterior)
    locutor.fechar()                             # a conversa terminou

Quando a última conversa termina, o bot espera acabar de falar e sai do canal.
"""

import asyncio
import os
import tempfile

import discord

VOZ_PADRAO = "pt-BR-AntonioNeural"


def _edge_tts():
    """Importa o edge-tts só quando precisa, para o bot rodar sem ele se a voz estiver desligada."""
    try:
        import edge_tts
    except ImportError as erro:
        raise RuntimeError(
            "O pacote edge-tts não está instalado. Rode: pip install -r requirements.txt"
        ) from erro
    return edge_tts


def _apagar(caminho, erro=None):
    """Apaga o áudio temporário. Também é chamado pelo 'after' do discord.py."""
    if erro:
        print(f"[TTS] Erro durante a reprodução: {erro}")
    try:
        os.remove(caminho)
    except OSError:
        pass


async def sintetizar(texto, voz):
    """Gera um arquivo .mp3 temporário com a fala. 'voz' é o bloco "voz" da conversa."""
    edge_tts = _edge_tts()
    descritor, caminho = tempfile.mkstemp(prefix="npc_", suffix=".mp3")
    os.close(descritor)
    try:
        comunicar = edge_tts.Communicate(
            texto,
            voz.get("nome", VOZ_PADRAO),
            rate=voz.get("velocidade", "+0%"),
            pitch=voz.get("tom", "+0Hz"),
        )
        await comunicar.save(caminho)
    except Exception:
        _apagar(caminho)
        raise
    return caminho


async def listar_vozes(idioma="pt-BR"):
    """Vozes disponíveis para o idioma (precisa de internet)."""
    vozes = await _edge_tts().list_voices()
    return [v for v in vozes if v.get("Locale") == idioma]


class Locutor:
    def __init__(self, bot, canal_id, ffmpeg="ffmpeg"):
        self.bot = bot
        self.canal_id = canal_id  # 0 = voz desligada
        self.ffmpeg = ffmpeg
        self.ativas = 0           # conversas com voz em andamento
        self._pendentes = 0       # falas sendo geradas
        self._geracao = 0         # numera as falas: só a mais recente toca
        self._tarefas = set()
        self._tarefa_saida = None
        self._trava_conexao = asyncio.Lock()

    @property
    def ligado(self):
        return self.canal_id != 0

    # ------------------------------------------------------------------
    # Ciclo de vida da conversa
    # ------------------------------------------------------------------
    def abrir(self):
        """Uma conversa com voz começou: o bot deve ficar no canal."""
        self.ativas += 1
        if self._tarefa_saida is not None:
            self._tarefa_saida.cancel()
            self._tarefa_saida = None

    def fechar(self):
        """Uma conversa terminou. Sem conversas ativas, o bot sai do canal."""
        self.ativas = max(0, self.ativas - 1)
        if self.ativas == 0:
            self._tarefa_saida = self._criar_tarefa(self._sair_quando_terminar())

    # ------------------------------------------------------------------
    # Fala
    # ------------------------------------------------------------------
    def falar_em_segundo_plano(self, texto, voz):
        """Gera e toca a fala sem travar o clique do jogador.

        Se chegar uma fala mais nova enquanto a anterior ainda está sendo gerada
        ou tocada, a mais nova vence.
        """
        self._geracao += 1
        minha = self._geracao
        self._pendentes += 1
        self._criar_tarefa(self._falar(texto, voz, minha))

    async def _falar(self, texto, voz, geracao):
        arquivo = None
        try:
            arquivo = await sintetizar(texto, voz)
            if geracao != self._geracao:
                return  # chegou uma fala mais nova durante a geração

            vc = await self._conectar()
            if geracao != self._geracao:
                return  # chegou uma fala mais nova durante a conexão

            if vc.is_playing():
                vc.stop()
            origem = self._criar_origem(arquivo)
            vc.play(origem, after=lambda erro, a=arquivo: _apagar(a, erro))
            arquivo = None  # a partir daqui, quem apaga é o 'after'
        except asyncio.CancelledError:
            raise
        except Exception as erro:
            print(f"[TTS] Não foi possível falar: {type(erro).__name__}: {erro}")
        finally:
            self._pendentes -= 1
            if arquivo:
                _apagar(arquivo)

    def _criar_origem(self, arquivo):
        return discord.FFmpegPCMAudio(arquivo, executable=self.ffmpeg)

    # ------------------------------------------------------------------
    # Canal de voz
    # ------------------------------------------------------------------
    def _voice_client(self):
        canal = self.bot.get_channel(self.canal_id)
        return canal.guild.voice_client if canal is not None else None

    async def _conectar(self):
        async with self._trava_conexao:
            canal = self.bot.get_channel(self.canal_id)
            if not isinstance(canal, discord.VoiceChannel):
                raise RuntimeError(
                    "VOZ_CANAL_ID não é um canal de voz que o bot consiga ver."
                )
            vc = canal.guild.voice_client
            if vc is None:
                vc = await canal.connect()
            elif vc.channel.id != canal.id:
                await vc.move_to(canal)
            return vc

    async def _sair_quando_terminar(self):
        # Espera acabar de gerar e de falar (no máximo 2 minutos)
        for _ in range(240):
            vc = self._voice_client()
            tocando = vc is not None and vc.is_playing()
            if self._pendentes == 0 and not tocando:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(2)  # respiro antes de sair
        if self.ativas == 0:
            vc = self._voice_client()
            if vc is not None:
                await vc.disconnect()

    def _criar_tarefa(self, corrotina):
        tarefa = asyncio.create_task(corrotina)
        self._tarefas.add(tarefa)
        tarefa.add_done_callback(self._tarefas.discard)
        return tarefa
