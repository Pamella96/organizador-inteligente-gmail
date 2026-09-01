"""Funções puras compartilhadas pelo organizador de e-mails."""

import base64
import re
import unicodedata


def normalizar_texto_busca(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(ch for ch in texto if not unicodedata.combining(ch)).lower()


def decode_b64_urlsafe(data):
    if not data:
        return ""
    try:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def extrair_textos_payload(payload):
    textos = []
    if not payload:
        return textos

    mime = (payload.get("mimeType") or "").lower()
    data = (payload.get("body") or {}).get("data")
    if data and ("text/plain" in mime or "text/html" in mime or not mime):
        textos.append(decode_b64_urlsafe(data))

    for parte in payload.get("parts") or []:
        textos.extend(extrair_textos_payload(parte))
    return textos


def labels_intermediarios(nomes):
    """Expande nomes como A/B/C para A, A/B e A/B/C."""
    todos = set()
    for nome in nomes:
        partes = nome.split("/")
        for indice in range(1, len(partes) + 1):
            todos.add("/".join(partes[:indice]))
    return sorted(todos)


def slug(nome):
    """Converte um nome para o formato usado nas opções da CLI."""
    return re.sub(r"[^a-z0-9]+", "-", nome.lower()).strip("-")


def operacao_usa_lixeira(add_label_ids):
    """Indica se a alteração pretende mover mensagens para a lixeira."""
    return "TRASH" in (add_label_ids or [])
