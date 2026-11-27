"""Ponto de entrada: Auto-instalação -> Texto do Senhor -> API -> Ações/Pesquisa Web + Discord -> Tela."""
import subprocess
import sys

# Garante que as bibliotecas sejam instaladas no mesmo Python que abriu o programa
for pacote, modulo in [("discord.py", "discord"), ("ddgs", "ddgs")]:
    try:
        __import__(modulo)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pacote])

import json
import traceback
from datetime import datetime

import actions
import discord_bot
from ia_client import Conversa, IAErro
from paths import PASTA_APP
from persona import prompt_mestre, _titulo_usuario
from ui import MaidWindow

# Carrega as ações disponíveis + tudo o que ela já aprendeu em pesquisas anteriores
prompt_inicial = prompt_mestre(actions.catalogo()) + actions.carregar_memoria()
conversa = Conversa(prompt_inicial)


def recepcao(ui) -> None:
    """Saudação automática assim que a janela da Allmaid abre."""
    usuario = _titulo_usuario()
    hora = datetime.now().hour
    if 5 <= hora < 12:
        saudacao = f"Bom dia, {usuario}. Sistemas inicializados. Vamos começar os estudos ou o trabalho?"
    elif 12 <= hora < 18:
        saudacao = f"Boa tarde, {usuario}. Estou online e aguardando suas ordens."
    else:
        saudacao = f"Boa noite, {usuario}. Já estou ativa para organizar suas tarefas ou bloquear distrações."
    ui.expressao("feliz")
    ui.say(saudacao)


def processar(texto: str, ui) -> None:  # roda em thread: a janela não trava
    usuario = _titulo_usuario()
    ui.expressao("pensando")
    ui.status("pensando…")
    try:
        bruto = conversa.perguntar(texto, json_mode=True)
    except IAErro as e:
        ui.say(str(e))
        ui.expressao("neutra")
        ui.status("")
        return

    try:
        dados = json.loads(bruto)
    except json.JSONDecodeError:
        dados = {"fala": bruto, "acao": "nenhuma", "args": {}}

    acao = dados.get("acao", "nenhuma")

    # Se ela decidiu pesquisar na internet, busca os dados primeiro e depois formula a resposta
    if acao == "pesquisar_web":
        ui.status("pesquisando na web…")
        resultado_web = actions.executar(acao, dados.get("args", {}), ui.confirm)
        ui.status("aprendendo e formulando resposta…")
        try:
            bruto_final = conversa.perguntar(
                f"[SISTEMA - RESULTADO DA PESQUISA]: {resultado_web}\nAgora responda ao {usuario} usando essa informação de forma natural, sem rodar outra ação.",
                json_mode=True
            )
            dados_final = json.loads(bruto_final)
            ui.say(dados_final.get("fala", resultado_web))
        except Exception:
            ui.say(resultado_web)
        ui.expressao("feliz")
        ui.status("")
        return

    ui.say(dados.get("fala", ""))
    ui.expressao("feliz")

    if acao != "nenhuma":
        ui.status(f"executando: {acao}")
        resultado = actions.executar(acao, dados.get("args", {}), ui.confirm)
        ui.say(f"⚙️ {resultado}")
    ui.status("")


if __name__ == "__main__":
    try:
        discord_bot.iniciar_discord()
        app = MaidWindow(processar)
        app.after(400, lambda: recepcao(app))
        app.mainloop()
    except Exception:
        log = PASTA_APP / "erro.log"          # no .exe não há console: o erro vai para este arquivo
        log.write_text(traceback.format_exc(), encoding="utf-8")
        from tkinter import messagebox
        messagebox.showerror("Project Allmaid", f"Ocorreu um erro. Detalhes em:\n{log}")
        raise
