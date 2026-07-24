"""
bot_discord.py — bot da Dália, com chat contínuo por canal.

CONFIGURAÇÃO DO TOKEN:
    Nunca deixe o token colado direto no código (ainda mais se for
    compartilhar o arquivo ou subir num Git). Defina a variável de
    ambiente antes de rodar:

        # Linux/Mac
        export DISCORD_BOT_TOKEN="seu_token_aqui"
        python3 bot_discord.py

        # Windows (PowerShell)
        $env:DISCORD_BOT_TOKEN="seu_token_aqui"
        python bot_discord.py

INSTALAÇÃO:
    pip install discord.py requests --break-system-packages
"""

import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from discord.ext import voice_recv
load_dotenv()  # lê o arquivo .env e carrega as variáveis nele

from iaChatDália import (
    corrigir_texto,
    perguntar_ollama,
    limpar_historico,
    iniciar_conversa_discord,
    formatar_com_autor,
)
from discord.ext import voice_recv

# --- Configuração do bot ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="69 ", intents=intents)

adms = 335637521486708736

# Canais com o chat contínuo ativo no momento
canais_em_chat = set()
canais_ocupados = set()  # canais que estão esperando resposta da Dália agora

@bot.event
async def on_ready():
    print(f"Tudo pronto! Logado como {bot.user}")
    print(f"Estou participando de {len(bot.guilds)} servidores:")
    for guild in bot.guilds:
        print(f" - {guild.name} (ID: {guild.id})")

#Para testar conexão
@bot.command(name="ping", help="Testa se o bot está respondendo.")
async def ping(ctx):
    await ctx.send("Estou online e funcionando.")

# sobre a Dália
@bot.command(name="sobre", help="Informações sobre a Dália.")
async def sobre(ctx):
    await ctx.send(
        "Eu sou a Dália, um bot com IA integrada que está sendo desenvolvido "
        "pelo Gustavo Claman."
    )

# lista de comandos
@bot.command(name="comandos", help="Mostra esta lista de comandos.")
async def listar_comandos(ctx):
    linhas = []
    for cmd in bot.commands:
        descricao = cmd.help if cmd.help else "Sem descrição"
        linhas.append(f"69 {cmd.name:<10} -> {descricao}")

    texto_formatado = "```text\n" + "\n".join(linhas) + "\n```"
    await ctx.send(texto_formatado)

# modo chat
@bot.command(name="chat", help="Inicia o modo de chat contínuo com a Dália.")
async def chat(ctx):
    if ctx.channel.id in canais_em_chat:
        await ctx.send(
            "⚠️ O chat contínuo já está ativo neste canal! Basta mandar a sua "
            "mensagem ou digitar `69 sair` para encerrar."
        )
    else:
        canais_em_chat.add(ctx.channel.id)

        # Manda uma mensagem de verdade avisando a Dália que ela está no
        # Discord — ela lê e responde a isso normalmente, entrando pro
        # histórico do canal como uma troca real (não um texto escondido).
        await ctx.send(
            "💬 **Chat iniciado com a Dália!** Agora você só precisa digitar "
            "a sua mensagem para conversar. Para encerrar, digite `69 sair`."
        )
        async with ctx.typing():
            resposta_abertura = iniciar_conversa_discord(ctx.channel.id)

        if resposta_abertura:
            await ctx.send(resposta_abertura)

# sair do modo chat
@bot.command(name="sair", help="Encerra o chat contínuo com a Dália.")
async def sair(ctx):
    if ctx.channel.id in canais_em_chat:
        canais_em_chat.remove(ctx.channel.id)
        limpar_historico(ctx.channel.id)  # zera a memória ao encerrar o chat
        await ctx.send("🛑 **Chat encerrado.** Voltei ao modo normal de comandos!")
    else:
        await ctx.send("⚠️ Não há nenhum chat ativo neste canal.")

@bot.command(name="call", help="Entra na chamada com o usuario.")
async def call(ctx):
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect(cls=voice_recv.VoiceRecvClient)
        await ctx.send(f"Conectado com sucesso ao canal **{channel.name}**!")

    else:
        await ctx.send(f"Você precisa entrar em um canal primeiro!")

@bot.command(name="descall", help="Sai da chamada do usuario.")
async def descall(ctx):
    channel = ctx.author.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        await ctx.send(f"Desconectando")
    else:
        await ctx.send(f"Foda-se?")

@bot.command(name="enviar", help="Enviar mensagens em um canal.")
async def enviar(ctx, canal_id: int, *, texto: str):
    if ctx.author.id != adms:
        await ctx.send("Só administradores podem usar esse comando")
        return
    canal = bot.get_channel(canal_id)
    if canal:
        await canal.send(texto)
        await ctx.send("Mensagem enviada com sucesso!")
    else:
        await ctx.send("Canal não encontrado")

# Lê mensagens que não são comandos (usado no modo chat)
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        if ctx.channel.id in canais_em_chat:

            # Já tem uma resposta sendo processada nesse canal? Bloqueia.
            if ctx.channel.id in canais_ocupados:
                await ctx.send("⏳ Ainda estou respondendo... espera um pouco!")
                return

            mensagem_usuario = ctx.message.content[len(bot.command_prefix):].strip()
            if not mensagem_usuario:
                return

            canais_ocupados.add(ctx.channel.id)
            try:
                mensagem_tratada = corrigir_texto(
                    formatar_com_autor(ctx.author.name, mensagem_usuario)
                )

                async with ctx.typing():
                    resposta = perguntar_ollama(ctx.channel.id, mensagem_tratada)

                if len(resposta) > 2000:
                    for i in range(0, len(resposta), 2000):
                        await ctx.send(resposta[i:i + 2000])
                else:
                    await ctx.send(resposta)
            finally:
                canais_ocupados.discard(ctx.channel.id)  # libera o canal, dando erro ou não
            return

    raise error


if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit(
            "ERRO: variável de ambiente DISCORD_BOT_TOKEN não definida.\n"
            "Veja as instruções no topo deste arquivo."
        )
    bot.run(token)