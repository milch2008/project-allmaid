"""Resposta a mensagens externas (WhatsApp/Discord/e-mail). SEM ações e SEM ferramentas:
texto de terceiros é entrada não confiável, então esse caminho nunca executa nada no PC."""
from ia_client import chat
from persona import Paciencia, eh_vip, prompt_terceiro

paciencia = Paciencia()


def responder_terceiro(remetente: str, mensagem: str) -> str | None:
    if eh_vip(remetente):
        return None  # VIPs nunca recebem resposta automática: avise o Mestre
    nivel = paciencia.nivel(remetente)
    texto = chat(
        [{"role": "system", "content": prompt_terceiro(nivel)},
         {"role": "user", "content": mensagem}],
        temperature=0.9,
    )
    if nivel == 3 and not texto.endswith("(lol) 💖"):
        texto = texto.rstrip() + " (lol) 💖"
    return texto
