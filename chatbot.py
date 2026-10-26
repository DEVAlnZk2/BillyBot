import os
import discord
import openai
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuração dos Intents (necessário message_content para ler o chat)
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Configuração da API da OpenAI
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------------------------------------
# Dicionário de Parâmetros / Fichas dos Personagens (Lore)
# -------------------------------------------------------------
PERSONAGENS = {
    "thromir": {
        "nome": "Thromir Machadoforte",
        "raca": "Anão das Montanhas",
        "classe": "Ferreiro / Guerreiro",
        "personalidade": "Rabugento, desconfiado com estranhos, orgulhoso do seu trabalho de forja.",
        "tom_de_voz": "Rude, direto, usa gírias rústicas e termos mineiros/de forja."
    },
    "elena": {
        "nome": "Elena da Luz Sombria",
        "raca": "Humana",
        "classe": "Maga Arcanista",
        "personalidade": "Calma, altamente intelectual, misteriosa e ligeiramente debochada.",
        "tom_de_voz": "Formal, místico e poético."
    }
}

# Escolha qual NPC vai responder neste canal/instância
# (Você pode mudar isso dinamicamente depois com um comando do bot)
NPC_ATUAL = "thromir"

def criar_prompt_sistema(npc_key):
    """Gera as instruções de sistema com base na ficha do NPC."""
    npc = PERSONAGENS.get(npc_key, PERSONAGENS["thromir"])
    
    return {
        "role": "system",
        "content": (
            f"Você é {npc['nome']}, um personagem de RPG de mesa de fantasia medieval. "
            f"Raça/Classe: {npc['raca']} - {npc['classe']}. "
            f"Personalidade: {npc['personalidade']}. "
            f"Tom de voz: {npc['tom_de_voz']}. "
            f"Responda sempre em primeira pessoa, mantendo-se totalmente no personagem, "
            f"de forma imersiva e sem quebrar a quarta parede."
        )
    }

async def buscar_historico_canal(canal, limit=10):
    messages_list = []
    async for message in canal.history(limit=limit, oldest_first=True):
        # Evita pegar mensagens vazias do próprio bot
        messages_list.append(
            {
                "role": "user" if message.author.id != bot.user.id else "assistant",
                "content": message.content
            }
        )
    
    # Insere a ficha do personagem no começo do histórico como instrução de sistema
    system_prompt = criar_prompt_sistema(NPC_ATUAL)
    messages_list.insert(0, system_prompt)
    
    return messages_list

def ask_gpt(mensagens):
    # Usando a sintaxe atualizada da biblioteca da OpenAI
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=mensagens,
        temperature=0.9,
        max_tokens=1000
    )
    return response.choices[0].message.content

@bot.event
async def on_ready():
    print(f"O pai tá on, que é o {bot.user.name}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Processa comandos caso existam antes de responder no on_message
    await bot.process_commands(message)

    # Se a mensagem começar com o prefixo ou se quiser que ele responda em todo chat:
    # Aqui ele vai responder a qualquer mensagem no canal onde o bot tiver acesso
    async with message.channel.typing():
        mensagens = await buscar_historico_canal(message.channel)
        resposta = ask_gpt(mensagens)

        await message.reply(resposta)

bot.run(DISCORD_BOT_TOKEN)
