import base64
import os

import discord
import discord.ext.tasks
import dotenv
import google.auth.transport.requests
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f"We have logged in as {client.user}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if "Sup You Bum Ass <:canit:1221156920623370250>" in message.content:
        await message.channel.send("Hello How Are You")


client.run(os.getenv("bot_token"))
