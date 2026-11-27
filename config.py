"""Lê o arquivo .env (ao lado do programa) sem precisar de bibliotecas extras."""
import os

from paths import PASTA_APP


def _ler_env() -> dict:
    arq = PASTA_APP / ".env"
    dados = {}
    if arq.exists():
        for linha in arq.read_text(encoding="utf-8-sig").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            k, v = linha.split("=", 1)
            dados[k.strip()] = v.strip().strip('"').strip("'")
    return dados


_ENV = _ler_env()


def get(nome: str, padrao: str = "") -> str:
    return os.environ.get(nome) or _ENV.get(nome, padrao)
