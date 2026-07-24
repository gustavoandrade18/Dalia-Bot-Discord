"""
iaChatDalia.py — módulo de IA (Ollama) com memória por canal.

Cada canal do Discord (ou a sessão do terminal) tem seu PRÓPRIO histórico de
conversa. Isso evita que mensagens de canais/pessoas diferentes se misturem
no mesmo contexto — que era a causa da Dália se comportar de forma
inconsistente entre o teste direto em Python e o uso no Discord.

Uso como módulo (ex: no bot do Discord):

    from iaChatDalia import (
        perguntar_ollama, corrigir_texto, limpar_historico,
        iniciar_conversa_discord, formatar_com_autor,
    )

    # Uma vez, ao iniciar o chat contínuo num canal:
    resposta_abertura = iniciar_conversa_discord(canal_id)

    # Em cada mensagem seguinte:
    texto = formatar_com_autor("Satugo", "oi Dália")
    resposta = perguntar_ollama(canal_id, texto)

Uso direto (teste no terminal, sem Discord):

    python3 iaChatDalia.py
"""

import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gang-ia"

# IMPORTANTE: não usamos "role": "system" aqui de propósito.
# O Ollama já usa o SYSTEM definido no Modelfile como padrão — mas se a
# gente mandar uma mensagem com role "system" dentro de "messages", ela
# SUBSTITUI o SYSTEM do Modelfile pra aquela chamada (não soma). Isso
# sobrescreveria a personalidade da Dália. Por isso, o aviso de que ela
# está no Discord é mandado como uma mensagem de USUÁRIO de verdade, logo
# quando o chat é iniciado (ver iniciar_conversa_discord), e não como
# system prompt.
AVISO_INICIO_DISCORD = (
    "Você está em um servidor do Discord, conversando com vários usuários "
    "ao mesmo tempo. Gustavo Claman é Satugo, seu criador/pai"
)

# Um histórico por canal/sessão: {chave: [{"role": ..., "content": ...}, ...]}
_historicos = {}

CORRECOES = {
    "0murano0": "Murano",
    "dalia": "Dália",
    "dália": "Dália",
}


def corrigir_texto(texto):
    for errado, certo in CORRECOES.items():
        texto = texto.replace(errado, certo)
        texto = texto.replace(errado.capitalize(), certo)
    return texto


def formatar_com_autor(nome_autor, texto):
    """Prefixa a mensagem com quem falou (ex: 'Satugo falou: oi')."""
    return f"{nome_autor} falou: {texto}"


def _get_historico(chave):
    """Retorna (criando se necessário) o histórico de uma chave (canal_id, etc)."""
    if chave not in _historicos:
        _historicos[chave] = []
    return _historicos[chave]


def limpar_historico(chave):
    """Zera a memória de uma conversa específica (histórico volta vazio)."""
    _historicos[chave] = []


def perguntar_ollama(chave, texto_usuario):
    """
    Envia uma mensagem para o Ollama dentro do histórico da 'chave' dada
    (ex: ctx.channel.id no Discord, ou uma string fixa no modo terminal).
    """
    historico = _get_historico(chave)
    historico.append({"role": "user", "content": texto_usuario})

    try:
        resposta = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "messages": historico,
            "stream": False
        }, timeout=60)
        resposta.raise_for_status()

        dados = resposta.json()
        texto_resposta = dados.get("message", {}).get("content", "").strip()

        if texto_resposta:
            historico.append({"role": "assistant", "content": texto_resposta})

        return texto_resposta or "[ERRO: resposta vazia do Ollama]"

    except requests.exceptions.ConnectionError:
        # Remove a mensagem do usuário que ficou sem resposta, pra não
        # poluir o histórico com uma pergunta órfã.
        historico.pop()
        return "[ERRO: não consegui conectar no Ollama. Verifique se ele está rodando (`ollama serve`).]"
    except Exception as e:
        historico.pop()
        return f"[ERRO: {e}]"


def iniciar_conversa_discord(chave):
    """
    Chamada UMA VEZ, quando o chat contínuo é iniciado num canal (ex: no
    comando '69 chat'). Zera o histórico daquele canal e manda o aviso de
    que a Dália está no Discord como uma mensagem de usuário de verdade —
    ela efetivamente lê e responde a isso, entrando no histórico como uma
    troca real, em vez de um texto colado escondido.

    Retorna a resposta da Dália a esse aviso (o bot pode mostrar ou não).
    """
    limpar_historico(chave)
    return perguntar_ollama(chave, AVISO_INICIO_DISCORD)


# --- Modo terminal (teste manual, sem Discord) ---

def main():
    CHAVE_TERMINAL = "__terminal__"

    print("=== Dália (modo texto) ===")
    print('Digite "sair" para encerrar, "limpar" para zerar a memória.\n')

    while True:
        texto_usuario = input("Você: ").strip()

        if not texto_usuario:
            continue

        if texto_usuario.lower() in ("sair", "exit", "quit"):
            print("Saindo...")
            break

        if texto_usuario.lower() == "limpar":
            limpar_historico(CHAVE_TERMINAL)
            print("[memória da conversa zerada]\n")
            continue

        texto_usuario = corrigir_texto(texto_usuario)
        resposta = perguntar_ollama(CHAVE_TERMINAL, texto_usuario)
        print(f"Dália: {resposta}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSaindo...")