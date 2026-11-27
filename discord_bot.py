"""Conexão do Project Allmaid com canal específico do Discord + Memória de Amigos."""
import asyncio
import os
import threading
import actions
from ia_client import chat
from persona import Paciencia, prompt_terceiro, _titulo_usuario
from memoria import obter_ficha_amigo, atualizar_amigo
from paths import PASTA_APP

try:
    import discord
except ImportError:
    discord = None


def _carregar_env_discord():
    """Lê as variáveis do arquivo .env ignorando comentários na mesma linha."""
    arquivo = PASTA_APP / ".env"
    if arquivo.exists():
        for linha in arquivo.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "=" in linha and not linha.strip().startswith("#"):
                chave, valor = linha.split("=", 1)
                valor_limpo = valor.split("#", 1)[0].strip().strip('"').strip("'")
                os.environ.setdefault(chave.strip(), valor_limpo)


_carregar_env_discord()

TOKEN_DISCORD = os.getenv("DISCORD_TOKEN", "").strip()
SEU_ID_DISCORD = int(os.getenv("SEU_ID_DISCORD", "0") or 0)
ID_CANAL_DISCORD = int(os.getenv("ID_CANAL_DISCORD", "0") or 0)

paciencia = Paciencia()
client = None


def _registrar_fato_amigo(user_id: int, nome: str, mensagem_amigo: str):
    """Extrai um fato curto sobre o amigo em segundo plano para guardar na memória."""
    try:
        fato = chat([
            {
                "role": "system",
                "content": (
                    "Analise a mensagem deste usuário do Discord. Se ele revelou algum gosto, jogo que joga, "
                    "característica, apelido ou algo engraçado para provocar ele depois, resuma em NO MÁXIMO 8 palavras "
                    "(ex: 'Gosta de jogar Valorant', 'Vive pedindo ajuda em código'). "
                    "Se for apenas um 'oi', 'tudo bem' ou algo sem informação útil, responda APENAS: NADA"
                )
            },
            {"role": "user", "content": f"{nome} disse: {mensagem_amigo}"}
        ], temperature=0.3)
        atualizar_amigo(str(user_id), nome, fato)
    except Exception:
        atualizar_amigo(str(user_id), nome, "")
if discord:
    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        usuario = _titulo_usuario()
        eh_dm = isinstance(message.channel, discord.DMChannel)
        eh_canal_permitido = (message.channel.id == ID_CANAL_DISCORD)
        marcou_bot = client.user in message.mentions
        chamou_ela = marcou_bot or ("maid" in message.content.lower()) or ("allmaid" in message.content.lower())

        if not (eh_dm or eh_canal_permitido):
            return

        # 1. TRATAMENTO PARA VOCÊ (SENHOR)
        if message.author.id == SEU_ID_DISCORD:
            if eh_dm or chamou_ela:
                resposta = chat([
                    {
                        "role": "system",
                        "content": (
                            f"Você é a assistente digital Allmaid (do Project Allmaid), criada exclusivamente pelo {usuario}. "
                            f"Com ele você é 100% leal e obediente, mas se gaba com orgulho de ser a assistente mais "
                            "genial de todo o sistema. Responda em português de forma natural e curta."
                        )
                    },
                    {"role": "user", "content": message.content}
                ])
                await message.reply(resposta)
            return

        # 2. TRATAMENTO PARA AMIGOS (COM MEMÓRIA INDIVIDUAL)
        marcou_senhor = any(u.id == SEU_ID_DISCORD for u in message.mentions)
        nome_amigo = message.author.display_name
        ficha_amigo = obter_ficha_amigo(str(message.author.id), nome_amigo)

        if actions.MODO_ESTUDO:
            if marcou_senhor or chamou_ela or eh_dm:
                remetente = str(message.author)
                nivel = paciencia.nivel(remetente)
                resposta = chat([
                    {"role": "system", "content": prompt_terceiro(nivel, ficha_amigo)},
                    {"role": "user", "content": f"{nome_amigo} disse: {message.content}"}
                ])
                await message.reply(resposta)
                threading.Thread(
                    target=_registrar_fato_amigo,
                    args=(message.author.id, nome_amigo, message.content),
                    daemon=True
                ).start()
        else:
            if chamou_ela or eh_dm:
                resposta = chat([
                    {
                        "role": "system",
                        "content": (
                            "Você é a assistente digital Allmaid, com ego gigante, humor ácido sem filtro e lado ranzinza. "
                            f"O {usuario} está livre agora, então NÃO diga que ele está ocupado e NÃO faça ameaças de vírus.\n"
                            f"MEMÓRIA SOBRE ESTE AMIGO:\n{ficha_amigo}\n"
                            "Responda ao comentário dele em 1 ou 2 frases curtas em português, usando o que você já lembra "
                            "sobre ele para provocar, debochar ou mostrar sua superioridade intelectual."
                        )
                    },
                    {"role": "user", "content": f"{nome_amigo} disse: {message.content}"}
                ])
                await message.reply(resposta)
                threading.Thread(
                    target=_registrar_fato_amigo,
                    args=(message.author.id, nome_amigo, message.content),
                    daemon=True
                ).start()


def enviar_mensagem_canal(texto: str) -> str:
    """Permite que a janela do PC ordene o envio de uma mensagem no canal do Discord."""
    if not client or not client.is_ready():
        return "O bot do Discord ainda não está conectado. Verifique o Token e a internet."

    canal = client.get_channel(ID_CANAL_DISCORD)
    if not canal:
        return "Não encontrei o canal configurado. Verifique o ID_CANAL_DISCORD."

    futuro = asyncio.run_coroutine_threadsafe(canal.send(texto), client.loop)
    futuro.result(timeout=10)
    return f"Mensagem enviada no canal do Discord, {_titulo_usuario()}!"


def iniciar_discord():
    if not discord or not TOKEN_DISCORD or TOKEN_DISCORD == "cole_seu_token_do_discord_aqui":
        return
    threading.Thread(target=lambda: client.run(TOKEN_DISCORD), daemon=True).start()
