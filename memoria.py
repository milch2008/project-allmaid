"""Gerenciador de Memória Permanente da Maid-chan (Aprendizados Web + Perfis de Amigos)."""
import json
from datetime import datetime
from pathlib import Path
from paths import PASTA_APP as BASE

ARQ_MEMORIA = BASE / "memoria_maid.json"


def _carregar() -> dict:
    if not ARQ_MEMORIA.exists():
        return {"fatos_mestre": [], "aprendizados_web": [], "amigos": {}}
    try:
        dados = json.loads(ARQ_MEMORIA.read_text(encoding="utf-8"))
        dados.setdefault("fatos_mestre", [])
        dados.setdefault("aprendizados_web", [])
        dados.setdefault("amigos", {})
        return dados
    except Exception:
        return {"fatos_mestre": [], "aprendizados_web": [], "amigos": {}}


def _salvar(dados: dict) -> None:
    ARQ_MEMORIA.write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")


# --- 1. APRENDIZADO COM PESQUISAS NA INTERNET ---

def salvar_aprendizado_web(consulta: str, resumo_fato: str) -> None:
    """Guarda um resumo curto do que ela pesquisou na web (mantém os últimos 25)."""
    dados = _carregar()
    hoje = datetime.now().strftime("%d/%m/%Y")
    entrada = f"[{hoje}] Sobre '{consulta}': {resumo_fato.strip()}"
    
    # Evita duplicar a mesma pesquisa exata
    dados["aprendizados_web"] = [
        item for item in dados["aprendizados_web"] if f"Sobre '{consulta}':" not in item
    ]
    dados["aprendizados_web"].append(entrada)
    dados["aprendizados_web"] = dados["aprendizados_web"][-25:]
    _salvar(dados)


def obter_conhecimentos_recentes(limite: int = 12) -> str:
    """Retorna os aprendizados recentes formatados para o prompt da Maid-chan."""
    dados = _carregar()
    itens = dados.get("aprendizados_web", [])[-limite:]
    if not itens:
        return "Nenhum conhecimento extra pesquisado recentemente."
    return "\n".join(f"- {i}" for i in itens)


# --- 2. MEMÓRIA DE AMIGOS NO DISCORD ---

def obter_ficha_amigo(user_id: str, nome_atual: str) -> str:
    """Retorna o histórico e características conhecidas de um amigo específico."""
    dados = _carregar()
    amigo = dados["amigos"].get(str(user_id))
    if not amigo:
        return f"Amigo novo: {nome_atual}. Ainda não há registros anteriores sobre ele."
    
    notas = " | ".join(amigo.get("notas", [])[-5:]) or "Sem observações específicas."
    interacoes = amigo.get("interacoes", 0)
    return (
        f"Nome: {amigo.get('nome', nome_atual)} | Total de interações: {interacoes} | "
        f"O que você lembra sobre ele: {notas}"
    )


def atualizar_amigo(user_id: str, nome_atual: str, nova_nota: str = "") -> None:
    """Incrementa o contador de interações e salva um fato/nota sobre o amigo."""
    dados = _carregar()
    uid = str(user_id)
    amigo = dados["amigos"].setdefault(uid, {"nome": nome_atual, "interacoes": 0, "notas": []})
    
    amigo["nome"] = nome_atual
    amigo["interacoes"] += 1
    
    if nova_nota and nova_nota.strip().lower() != "nada":
        nota_limpa = nova_nota.strip()
        if nota_limpa not in amigo["notas"]:
            amigo["notas"].append(nota_limpa)
            amigo["notas"] = amigo["notas"][-6:]  # Mantém as 6 notas mais recentes por amigo
            
    _salvar(dados)
