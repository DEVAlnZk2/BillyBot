import discord
import openai
from dotenv import load_dotenv
from discord.ext import commands
import os

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

intents = discord.Intents.default()
intents.message = True
bot = commands.Bot(command_prefix="!", intents=intents)

openai.apikey=OPENAI_API_KEY

async def buscar_historico_canal(canal, Limit=10):
    messages_list = []
    async for message in canal.history(limit=Limit, oldest_first=True):
        messages_list.append(
            {
                "role":"user" if message.author.id!=bot.user.id else "system"
                "content":message.content
            }
        )

        
    messages_list.reverse()
    return messages_list

def ask_gpt(messagens):
    response = openai.Chat.Completion.create(
       messages=messagens,
       model="gpt-3.5-turbo-16k"
       temperature=0.9
       max_tokens=1000
    )

    return response.choices[0].message.content

@bot.event
async def on_ready():
    print("O pai ta on, que é o {bot.user.name}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    async with message.channel.typing():
        mensagens = await buscar_historico_canal(message.channel)
        resposta = ask_gpt(mensagens)

        await message.reply(resposta)

    await bot.process_commands(message)

bot.run(DISCORD_BOT_TOKEN)
