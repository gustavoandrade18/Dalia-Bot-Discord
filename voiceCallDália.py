"""
gravador_voz.py — módulo separado para escutar e salvar o áudio de UM
usuário específico numa chamada de voz do Discord, gravando em .wav.

Não sobe pro Whisper nem faz nada além disso ainda — só resolve a parte
de "escutar o comando e salvar o áudio". A transcrição entra depois, num
outro passo.

INSTALAÇÃO (se ainda não tiver feito):
    pip install discord-ext-voice-recv
    (depende do discord.py já estar instalado com suporte a voz, ou seja,
     com "discord.py[voice]" — que já traz o PyNaCl necessário)

USO (dentro do seu bot_discord.py / botDália.py):

    from discord.ext import voice_recv
    from gravador_voz import GravadorSink, iniciar_escuta, parar_escuta

    # No comando "call", ao conectar:
    await channel.connect(cls=voice_recv.VoiceRecvClient)

    # Num comando novo, tipo "69 escutar":
    caminho = iniciar_escuta(ctx.voice_client, ctx.author.id)

    # Num comando novo, tipo "69 parar_escuta":
    parar_escuta(ctx.voice_client)
"""

import os
import time
import wave

from discord.ext import voice_recv


# Pasta onde as gravações vão ser salvas (criada automaticamente se não existir)
PASTA_GRAVACOES = "gravacoes"

# Parâmetros do áudio que o Discord entrega (não mude sem necessidade)
CANAIS = 2          # Discord manda em estéreo
SAMPLE_WIDTH = 2    # 16 bits = 2 bytes por amostra
FRAME_RATE = 48000  # Discord usa 48kHz


class GravadorSink(voice_recv.AudioSink):
    """
    Sink que escuta o canal de voz inteiro, mas só GRAVA os pacotes de
    áudio que vieram do usuário cujo ID bate com 'usuario_id'. Todo o
    resto (outras pessoas falando ao mesmo tempo) é ignorado.
    """

    def __init__(self, usuario_id, caminho_arquivo):
        super().__init__()
        self.usuario_id = usuario_id
        self.caminho_arquivo = caminho_arquivo

        self._arquivo = wave.open(caminho_arquivo, "wb")
        self._arquivo.setnchannels(CANAIS)
        self._arquivo.setsampwidth(SAMPLE_WIDTH)
        self._arquivo.setframerate(FRAME_RATE)

    def wants_opus(self):
        # False = queremos o áudio já decodificado em PCM (não Opus cru)
        return False

    def write(self, user, data):
        # 'user' pode vir None em alguns pacotes (ex: pacotes de silêncio
        # do protocolo); só gravamos quando sabemos de quem é E é a
        # pessoa certa.
        if user is not None and user.id == self.usuario_id:
            self._arquivo.writeframes(data.pcm)

    def cleanup(self):
        # Chamado automaticamente pelo discord.py quando a escuta para
        # (voice_client.stop_listening()). É aqui que o arquivo é
        # fechado de fato — sem isso, o .wav fica com cabeçalho inválido.
        self._arquivo.close()


def _gerar_caminho_arquivo(usuario_id):
    os.makedirs(PASTA_GRAVACOES, exist_ok=True)
    nome = f"{usuario_id}_{int(time.time())}.wav"
    return os.path.join(PASTA_GRAVACOES, nome)


def iniciar_escuta(voice_client, usuario_id):
    """
    Começa a escutar o canal de voz onde 'voice_client' está conectado,
    gravando SÓ o áudio de 'usuario_id' num novo arquivo .wav.

    Requer que a conexão tenha sido feita com:
        channel.connect(cls=voice_recv.VoiceRecvClient)

    Retorna o caminho do arquivo que está sendo gravado (útil pra
    exibir/logar, ou pra passar pro Whisper depois de parar a escuta).
    """
    caminho = _gerar_caminho_arquivo(usuario_id)
    sink = GravadorSink(usuario_id, caminho)
    voice_client.listen(sink)
    return caminho


def parar_escuta(voice_client):
    """
    Para a escuta ativa no 'voice_client' dado. Isso automaticamente
    fecha o arquivo .wav (via cleanup() do sink).
    """
    if voice_client.is_listening():
        voice_client.stop_listening()