"""Ações reais no PC: Abrir/Fechar qualquer app, Pesquisa Web Global, Notícias do Dia, Modo Estudo e Discord."""
import csv
import inspect
import io
import json
import os
import shutil
import subprocess
import urllib.parse
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests

from paths import PASTA_APP as BASE
from memoria import salvar_aprendizado_web, obter_conhecimentos_recentes
from persona import _titulo_usuario

HOME = Path.home()
PASTAS_PERMITIDAS = [p for p in (HOME / "Downloads", HOME / "Documents", HOME / "Desktop") if p.exists()]
LIXEIRA = BASE / "_lixeira_maid"
LIMITE_BUSCA = 15

MODO_ESTUDO = False


def _carregar_apps() -> dict:
    arq = BASE / "apps.json"
    if arq.exists():
        return {k.lower(): v for k, v in json.loads(arq.read_text(encoding="utf-8")).items()}
    return {"bloco de notas": "notepad.exe", "calculadora": "calc.exe"}


APPS = _carregar_apps()
ACOES: dict[str, dict] = {}


def carregar_memoria() -> str:
    texto = obter_conhecimentos_recentes(limite=15)
    if "Nenhum conhecimento" in texto:
        return ""
    return "\nMEMÓRIA DE PESQUISAS ANTERIORES (O que você já aprendeu):\n" + texto


def salvar_aprendizado(tema: str, resumo: str):
    salvar_aprendizado_web(tema, resumo[:300])


def acao(nome: str, descricao: str, perigosa: bool = False):
    def deco(fn):
        ACOES[nome] = {"fn": fn, "desc": descricao, "perigosa": perigosa}
        return fn
    return deco


def _permitido(caminho: Path) -> bool:
    c = caminho.resolve()
    return any(c.is_relative_to(raiz.resolve()) for raiz in PASTAS_PERMITIDAS)


@acao("pesquisar_web", 'Pesquisa fatos globais na internet (Web + Wikipedia PT/EN) usando 2 a 4 palavras-chave. args: {"consulta": "palavras chave"}')
def pesquisar_web(consulta):
    termo = str(consulta).strip()
    resultados = []

    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            for r in ddgs.text(termo, region="wt-wt", max_results=4):
                if r.get("body"):
                    resultados.append(f"[Web] {r.get('title', '')}: {r.get('body', '')}")
    except Exception:
        pass

    if not resultados:
        headers = {"User-Agent": "ProjectAllmaid/1.0 (contact@local.pc)"}
        for lang in ("pt", "en"):
            try:
                q = urllib.parse.quote(termo)
                search_url = f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search&srsearch={q}&utf8=&format=json&srlimit=2"
                resp = requests.get(search_url, headers=headers, timeout=8).json()
                hits = resp.get("query", {}).get("search", [])
                if hits:
                    titulo_bruto = hits[0].get("title", "")
                    titulo_pagina = urllib.parse.quote(titulo_bruto.replace(" ", "_"))
                    sum_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{titulo_pagina}"
                    sum_resp = requests.get(sum_url, headers=headers, timeout=8).json()
                    extrato = sum_resp.get("extract", "")
                    if extrato:
                        resultados.append(f"[Wikipedia {lang.upper()}] {titulo_bruto}: {extrato}")
                        break
            except Exception:
                continue

    if not resultados:
        return f"FALHA_BUSCA: Nenhum resultado global encontrado para '{termo}'. NÃO invente detalhes de memória; avise ao {_titulo_usuario()} que a busca falhou."

    texto_encontrado = " | ".join(resultados)

    try:
        from ia_client import chat
        resumo_aprendido = chat([
            {
                "role": "system",
                "content": "Resuma os fatos principais encontrados nestes resultados em 1 ou 2 frases curtas e fiéis ao texto em português."
            },
            {
                "role": "user",
                "content": f"Pesquisa: {termo}\nResultados: {texto_encontrado[:1500]}"
            }
        ], temperature=0.2)
        salvar_aprendizado_web(termo, resumo_aprendido)
    except Exception:
        salvar_aprendizado_web(termo, texto_encontrado[:250])

    return texto_encontrado


@acao("noticias_do_dia", 'Busca e resume as notícias atuais do dia via Google News RSS. args: {"tema": "assunto opcional ou vazio para gerais"}')
def noticias_do_dia(tema=""):
    assunto = str(tema).strip()
    if assunto:
        q = urllib.parse.quote(assunto)
        rss_url = f"https://google.com{q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    else:
        rss_url = "https://google.com"

    try:
        resp = requests.get(rss_url, timeout=8)
        if resp.status_code != 200:
            return "FALHA_BUSCA: O Google News não respondeu agora."
        root = ET.fromstring(resp.content)
        manchetes = []
        for item in root.findall(".//item")[:5]:
            titulo = item.findtext("title", "")
            data_pub = item.findtext("pubDate", "")[:16]
            if titulo:
                manchetes.append(f"- [{data_pub}] {titulo}")
        if not manchetes:
            return f"FALHA_BUSCA: Nenhuma notícia encontrada hoje para '{assunto}'."
        return "Manchetes atuais encontradas:\n" + "\n".join(manchetes)
    except Exception as e:
        return f"FALHA_BUSCA: Erro ao buscar notícias ({e})."


@acao("ver_aprendizados", 'Lista e resume tudo o que a Allmaid aprendeu na internet e sobre os amigos. args: {}')
def ver_aprendizados():
    from memoria import _carregar
    dados = _carregar()

    web = dados.get("aprendizados_web", [])
    amigos = dados.get("amigos", {})

    resumo_web = "\n".join(web[-15:]) if web else "Nenhum fato pesquisado na web ainda."
    resumo_amigos = "\n".join(
        f"- {info.get('nome')} ({info.get('interacoes', 0)} msgs): {', '.join(info.get('notas', []))}"
        for info in amigos.values()
    ) if amigos else "Nenhum amigo registrado no Discord ainda."

    return f"=== APRENDIZADOS NA WEB ===\n{resumo_web}\n\n=== FICHAS DE AMIGOS ===\n{resumo_amigos}"
@acao("abrir_site", 'Abre um site no navegador. args: {"url": "https://..."}')
def abrir_site(url):
    if not str(url).startswith(("http://", "https://")):
        raise ValueError("só aceito links http/https")
    webbrowser.open(url)
    return f"Abri {url}."


@acao("fechar_aba", 'Fecha a aba atual do navegador/site ativo na tela. args: {}')
def fechar_aba():
    cmd = 'powershell -Command "$wshell = New-Object -ComObject wscript.shell; $wshell.SendKeys(\'^w\')"'
    subprocess.run(cmd, shell=True, check=True)
    return "Fechei a aba ativa."


@acao("abrir_app", 'Abre QUALQUER programa instalado no Windows pelo nome. args: {"nome": "nome do programa"}')
def abrir_app(nome):
    chave = str(nome).lower().strip()

    if chave in APPS:
        os.startfile(APPS.get(chave))
        return f"Abri {chave}."

    pastas_menu = [
        Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
    ]
    for pasta in pastas_menu:
        if pasta.exists():
            try:
                for atalho in pasta.rglob("*.lnk"):
                    if chave in atalho.stem.lower():
                        os.startfile(str(atalho))
                        return f"Abri {atalho.stem}."
            except Exception:
                continue

    try:
        subprocess.Popen(chave, shell=True)
        return f"Tentei iniciar {chave}."
    except Exception:
        raise ValueError(f"Não encontrei nenhum programa instalado chamado '{nome}'.")


@acao("fechar_app", 'Fecha QUALQUER programa aberto no Windows pelo nome do executável ou título da janela. args: {"nome": "nome do programa"}')
def fechar_app(nome):
    alvo = str(nome).lower().strip()
    apelidos = {
        "bloco de notas": "notepad",
        "calculadora": "calculator",
        "navegador": "chrome",
        "google chrome": "chrome",
        "explorador de arquivos": "explorer",
    }
    alvo = apelidos.get(alvo, alvo)

    saida = subprocess.check_output(
        ["tasklist", "/V", "/FO", "CSV"],
        text=True,
        encoding="cp850",
        errors="ignore"
    )

    protegidos = {"python.exe", "pythonw.exe", "explorer.exe", "svchost.exe", "dwm.exe", "csrss.exe", "winlogon.exe"}
    alvos_encontrados = set()

    leitor = csv.reader(io.StringIO(saida))
    next(leitor, None)

    for linha in leitor:
        if len(linha) >= 9:
            nome_exe = next(iter(linha))
            titulo_janela = linha[-1]
            if alvo in nome_exe.lower() or alvo in titulo_janela.lower():
                if nome_exe.lower() not in protegidos:
                    alvos_encontrados.add(nome_exe)

    if not alvos_encontrados:
        return f"Não encontrei nenhum programa aberto com o nome '{nome}', {_titulo_usuario()}."

    fechados = []
    for exe in alvos_encontrados:
        res = subprocess.run(["taskkill", "/F", "/T", "/IM", exe], capture_output=True, text=True)
        if res.returncode == 0:
            fechados.append(exe)

    if not fechados:
        return f"Encontrei {', '.join(alvos_encontrados)}, mas o Windows bloqueou o fechamento."

    return f"Encerrei: {', '.join(fechados)}."


@acao("modo_estudo", 'Ativa ou desativa o Modo Estudo/Ocupado (barreira contra amigos). args: {"ativar": true ou false}')
def modo_estudo(ativar: bool):
    global MODO_ESTUDO
    MODO_ESTUDO = bool(ativar)
    estado = "ATIVADO" if MODO_ESTUDO else "DESATIVADO"
    return f"Modo Estudo/Ocupado {estado}."


@acao("enviar_discord", 'Envia uma mensagem ou recado no canal configurado do Discord a mando do Senhor. args: {"mensagem": "texto do recado"}')
def enviar_discord(mensagem):
    import discord_bot
    recado = f"📢 **Recado do {_titulo_usuario()}:** {mensagem}"
    return discord_bot.enviar_mensagem_canal(recado)


@acao("procurar_arquivo", 'Procura arquivos pelo nome em Downloads/Documents/Desktop. args: {"nome": "parte do nome"}')
def procurar_arquivo(nome):
    alvo, achados = str(nome).lower(), []
    for raiz in PASTAS_PERMITIDAS:
        for pasta, _, arquivos in os.walk(raiz):
            for a in arquivos:
                if alvo in a.lower():
                    achados.append(str(Path(pasta) / a))
                    if len(achados) >= LIMITE_BUSCA:
                        return "Achei:\n" + "\n".join(achados)
    return ("Achei:\n" + "\n".join(achados)) if achados else "Não encontrei nada."


@acao("mover_arquivo", 'Move um arquivo para outra pasta. args: {"origem": "caminho", "destino_pasta": "pasta"}', perigosa=True)
def mover_arquivo(origem, destino_pasta):
    o, d = Path(origem), Path(destino_pasta)
    if not (_permitido(o) and _permitido(d)):
        raise PermissionError("fora das pastas permitidas")
    if not o.is_file():
        raise FileNotFoundError(origem)
    d.mkdir(parents=True, exist_ok=True)
    shutil.move(str(o), str(d / o.name))
    return f"Movi {o.name} para {d}."


@acao("excluir_arquivo", 'Exclui um arquivo (vai para a lixeira da Allmaid). args: {"caminho": "arquivo"}', perigosa=True)
def excluir_arquivo(caminho):
    c = Path(caminho)
    if not _permitido(c):
        raise PermissionError("fora das pastas permitidas")
    if not c.is_file():
        raise FileNotFoundError(caminho)
    LIXEIRA.mkdir(exist_ok=True)
    shutil.move(str(c), str(LIXEIRA / f"{datetime.now():%Y%m%d-%H%M%S}_{c.name}"))
    return f"{c.name} foi para a lixeira da Allmaid."


def catalogo() -> str:
    return "\n".join(f"- {nome}: {info.get('desc')}" for nome, info in ACOES.items())


def schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "fala": {"type": "string"},
            "acao": {"type": "string", "enum": list(ACOES) + ["nenhuma"]},
            "args": {"type": "object"},
        },
        "required": ["fala", "acao", "args"],
    }


def executar(nome: str, args, confirmar) -> str:
    usuario = _titulo_usuario()
    info = ACOES.get(nome)
    if not info:
        return f"Não conheço a ação '{nome}', {usuario}. Ignorei."
    if not isinstance(args, dict):
        args = {}
    fn = info.get("fn")
    aceitos = inspect.signature(fn).parameters
    args = {k: v for k, v in args.items() if k in aceitos}
    if info.get("perigosa") and not confirmar(f"A Allmaid quer executar:\n{nome} {args}\n\nPermitir?"):
        return f"Cancelei, {usuario}."
    try:
        return str(fn(**args))
    except TypeError:
        return f"Faltaram informações para essa ação, {usuario}."
    except Exception as e:
        return f"Não consegui: {e}"
