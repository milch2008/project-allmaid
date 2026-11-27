"""Cliente da API da Groq (compatível com OpenAI). Chave e modelo vêm do arquivo .env."""
import json
import re
import requests

import config

API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODELO_PADRAO = "llama-3.3-70b-versatile"


class IAErro(Exception):
    """Erro com mensagem já pronta para aparecer no balão da Maid-chan."""


def _extrair_json(texto: str) -> str:
    """Garante que apenas o bloco JSON válido seja retornado, evitando o erro 400 da Groq."""
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        return match.group(0)
    return json.dumps({"fala": texto.strip(), "acao": "nenhuma", "args": {}}, ensure_ascii=False)


def chat(messages, json_mode: bool = False, temperature: float = 0.85, timeout: int = 60) -> str:
    chave = config.get("GROQ_API_KEY")
    if not chave or chave.startswith("cole_"):
        raise IAErro("Mestre, falta a chave da Groq. Coloque GROQ_API_KEY no arquivo .env ao lado do programa.")
    payload = {
        "model": config.get("GROQ_MODEL", MODELO_PADRAO),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 600,
    }
    try:
        r = requests.post(
            API_URL,
            json=payload,
            timeout=timeout,
            headers={"Authorization": f"Bearer {chave}", "User-Agent": "MaidChan/1.0"},
        )
    except requests.ConnectionError:
        raise IAErro("Mestre, estou sem internet para falar com a Groq.")
    except requests.Timeout:
        raise IAErro("A Groq demorou demais para responder, Mestre.")

    if r.status_code == 401:
        raise IAErro("A Groq recusou a chave (erro 401). Confira o GROQ_API_KEY no .env, Mestre.")
    if r.status_code == 429:
        raise IAErro("Atingi o limite gratuito da Groq, Mestre. Espere um pouco e tente de novo.")
    if r.status_code != 200:
        raise IAErro(f"A Groq devolveu o erro {r.status_code}: {r.text[:200]}")

    bruto = r.json()["choices"][0]["message"]["content"].strip()
    return _extrair_json(bruto) if json_mode else bruto


class Conversa:
    """Histórico com janela deslizante + prompt de sistema sempre na frente."""

    def __init__(self, system_prompt: str, max_msgs: int = 12):
        self.system = {"role": "system", "content": system_prompt}
        self.hist: list[dict] = []
        self.max_msgs = max_msgs

    def perguntar(self, texto: str, json_mode: bool = False) -> str:
        self.hist.append({"role": "user", "content": texto})
        self.hist = self.hist[-self.max_msgs:]
        bruto = chat([self.system] + self.hist, json_mode=json_mode)
        self.hist.append({"role": "assistant", "content": bruto})
        return bruto


if __name__ == "__main__":  # teste rápido: py ia_client.py
    print(chat([{"role": "user", "content": "Diga olá em uma frase."}]))
