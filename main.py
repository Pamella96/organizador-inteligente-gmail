"""
Engine genérico de organização de e-mails do Gmail.

Para adicionar ou editar serviços, edite services.py — não é necessário
tocar neste arquivo.

Uso:
  python main.py --sync-spotify
  python main.py --sync-mercado-livre
  python main.py --sync-all
  python main.py --sync-amazon --people Ana Bruno
  python main.py --refine-amazon-indefinido
  python main.py --delete-band-inuteis
  python main.py --limpar-instagram     # remove labels de e-mails não-oficiais
  python main.py --remove-inbox         # combinável com qualquer --sync-*
"""

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

import argparse
import json
import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import re
import time
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from google import genai
from googleapiclient.discovery import build as _gdisco_build
from auth import get_gmail_service as _auth_get_gmail_service
from core import (
    decode_b64_urlsafe as _decode_b64_urlsafe,
    extrair_textos_payload as _extrair_textos_payload,
    labels_intermediarios as _labels_intermediarios,
    normalizar_texto_busca as _normalizar_texto_busca,
    operacao_usa_lixeira,
    slug as _slug,
)
from services import SERVICES
from relatorio_pdf import gerar_pdf

# ---------------------------------------------------------------------------
# Gemini setup
# ---------------------------------------------------------------------------

def _carregar_chave_gemini():
    """Lê a chave do Gemini somente do ambiente.

    Os arquivos ``credentials.json`` e ``token.json`` pertencem ao fluxo OAuth
    do Gmail e não devem acumular outros segredos.
    """
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


_gemini_api_key = _carregar_chave_gemini()
client = genai.Client(api_key=_gemini_api_key) if _gemini_api_key else None
model_name = "gemini-2.5-flash"
_dry_run = False
_allow_ai_processing = False
_allow_trash = False


# ---------------------------------------------------------------------------
# Gmail service — thread-safe
# ---------------------------------------------------------------------------

_gmail_creds = None
_thread_local = threading.local()


def get_gmail_service():
    """Constrói o serviço Gmail e salva credenciais para uso em threads."""
    global _gmail_creds
    svc = _auth_get_gmail_service()
    if svc and _gmail_creds is None:
        try:
            _gmail_creds = svc._http.credentials
        except AttributeError:
            pass
    return svc


def _get_thread_service():
    """Retorna um serviço Gmail local da thread atual (thread-safe)."""
    if not hasattr(_thread_local, "svc"):
        if _gmail_creds is not None:
            _thread_local.svc = _gdisco_build("gmail", "v1", credentials=_gmail_creds)
        else:
            _thread_local.svc = _auth_get_gmail_service()
    return _thread_local.svc

# ---------------------------------------------------------------------------
# Helpers de API Gmail
# ---------------------------------------------------------------------------

def _listar_message_ids(service, query):
    ids = []
    page_token = None
    while True:
        resp = service.users().messages().list(
            userId="me", q=query, maxResults=500, pageToken=page_token
        ).execute()
        ids.extend(m["id"] for m in resp.get("messages", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids


def _contar_query(service, query):
    """Estimativa rápida de contagem (1 chamada à API)."""
    resp = service.users().messages().list(
        userId="me", q=query, maxResults=1, fields="resultSizeEstimate"
    ).execute()
    return resp.get("resultSizeEstimate", 0)


def _garantir_labels(service, nomes_labels):
    nomes_todos = _labels_intermediarios(nomes_labels)
    labels = service.users().labels().list(userId="me").execute().get("labels", [])
    by_name = {l["name"]: l for l in labels if l.get("type") == "user"}
    for nome in nomes_todos:
        if nome in by_name:
            continue
        by_name[nome] = service.users().labels().create(
            userId="me",
            body={"name": nome, "labelListVisibility": "labelShow", "messageListVisibility": "show"},
        ).execute()
    return by_name


def _batch_modificar(service, ids, add_label_ids=None, remove_label_ids=None):
    if not ids:
        return
    add_label_ids = add_label_ids or []
    remove_label_ids = remove_label_ids or []
    if _dry_run:
        add_names = add_label_ids or []
        rem_names = remove_label_ids or []
        print(f"[DRY-RUN] {len(ids)} e-mails  +{add_names}  -{rem_names}")
        return
    if operacao_usa_lixeira(add_label_ids) and not _allow_trash:
        print(
            "[SEGURANÇA] Operação de lixeira bloqueada. "
            "Revise com --dry-run e repita com --confirm-trash."
        )
        return
    for i in range(0, len(ids), 1000):
        chunk = ids[i : i + 1000]
        body = {"ids": chunk}
        if add_label_ids:
            body["addLabelIds"] = add_label_ids
        if remove_label_ids:
            body["removeLabelIds"] = remove_label_ids
        service.users().messages().batchModify(userId="me", body=body).execute()


def _buscar_mensagens_paralelo(ids, max_workers=15):
    """Busca detalhes de múltiplas mensagens em paralelo (thread-safe)."""
    if not ids:
        return {}

    def fetch(mid):
        svc = _get_thread_service()
        return mid, svc.users().messages().get(userId="me", id=mid, format="full").execute()

    resultado = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch, mid): mid for mid in ids}
        for future in as_completed(futures):
            try:
                mid, msg = future.result()
                resultado[mid] = msg
            except Exception as e:
                print(f"[WARN] Falha ao buscar mensagem: {e}")
    return resultado

# ---------------------------------------------------------------------------
# Gemini — classificação em batch
# ---------------------------------------------------------------------------

_INBOX_CATS = {"TRABALHO", "ACADEMICO", "PESSOAL", "FINANCEIRO", "NEWSLETTER", "SPAM"}


def _classificar_inbox_batch(batch):
    """Classifica lote de e-mails da caixa de entrada com urgência e resumo.

    batch: list of (mid, assunto, snippet, corpo)
    Retorna: dict {mid: {categoria, urgencia, resumo}}
    """
    if not client or not batch:
        return {}

    emails_txt = ""
    for i, (_, assunto, snippet, corpo) in enumerate(batch, 1):
        emails_txt += f"\n--- E-mail {i} ---\n"
        emails_txt += f"Assunto: {assunto[:200]}\n"
        emails_txt += f"Preview: {snippet[:200]}\n"
        if corpo.strip():
            emails_txt += f"Corpo (trecho): {corpo[:400]}\n"

    prompt = f"""Classifique cada e-mail abaixo.

Categorias:
- TRABALHO: profissional, carreira, vagas, projetos, clientes
- ACADEMICO: newsletters técnicas lidas ativamente, cursos, artigos científicos
- PESSOAL: e-mails pessoais, família, amigos, cotidiano
- FINANCEIRO: faturas, pagamentos, cobranças, recibos, bancos, cartões
- NEWSLETTER: boletins de notícias genéricas, digests, marketing
- SPAM: spam, promoções não solicitadas

urgencia: 1=irrelevante 2=baixa 3=média 4=alta 5=crítico

Responda SOMENTE com JSON array:
[{{"idx":1,"categoria":"...","urgencia":1,"resumo":"uma frase curta"}}]

{emails_txt}"""

    delay = 5
    for attempt in range(7):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            json_text = (response.text or "").replace("```json", "").replace("```", "").strip()
            resultados = json.loads(json_text)
            if not isinstance(resultados, list):
                raise ValueError("não é lista")
            mapa = {}
            for item in resultados:
                idx = int(item.get("idx", 0)) - 1
                if 0 <= idx < len(batch):
                    mid = batch[idx][0]
                    cat = str(item.get("categoria", "PESSOAL")).upper()
                    if cat not in _INBOX_CATS:
                        cat = "PESSOAL"
                    mapa[mid] = {
                        "categoria": cat,
                        "urgencia": min(5, max(1, int(item.get("urgencia", 1)))),
                        "resumo": str(item.get("resumo", "")).strip(),
                    }
            return mapa
        except Exception as e:
            msg = str(e).lower()
            is_rate_limit = any(k in msg for k in ("429", "resource_exhausted", "quota", "rate limit"))
            if attempt < 6:
                if is_rate_limit:
                    print(f"[GEMINI] Rate limit. Aguardando {delay}s...")
                    time.sleep(delay)
                    delay = min(delay * 2, 120)
                else:
                    time.sleep(3)
                continue
            print(f"[GEMINI] Falha na classificação: {e}")
            return {}


def _classificar_batch_gemini(svc_config, batch):
    """Classifica um lote de e-mails em uma única chamada ao Gemini.

    batch: list of (mid, assunto, snippet, corpo)
    Retorna: dict {mid: categoria}
    """
    if not client or not batch:
        return {}

    name = svc_config["name"]
    categorias_validas = {c["name"] for c in svc_config["categories"]}
    categorias_validas.add(svc_config["default"])

    cat_descricoes = "\n".join(
        f'  - {c["name"]}: {c["descricao"]}' for c in svc_config["categories"]
    )
    cat_descricoes += f'\n  - {svc_config["default"]}: Qualquer outro tipo não listado acima'

    emails_txt = ""
    for i, (_, assunto, snippet, corpo) in enumerate(batch, 1):
        emails_txt += f"\n--- E-mail {i} ---\n"
        emails_txt += f"Assunto: {assunto[:200]}\n"
        emails_txt += f"Preview: {snippet[:200]}\n"
        if corpo.strip():
            emails_txt += f"Corpo (trecho): {corpo[:600]}\n"

    prompt = f"""Classifique os e-mails abaixo, todos do serviço {name}.

Categorias disponíveis:
{cat_descricoes}

Para cada e-mail, escolha a categoria mais adequada com base no conteúdo.
Responda SOMENTE com JSON array, sem nenhum texto extra:
[{{"idx": 1, "categoria": "NomeDaCategoria"}}, {{"idx": 2, "categoria": "..."}}, ...]

{emails_txt}"""

    delay = 5
    for attempt in range(7):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            json_text = (response.text or "").replace("```json", "").replace("```", "").strip()
            resultados = json.loads(json_text)

            if not isinstance(resultados, list):
                raise ValueError("Resposta não é uma lista JSON")

            mapa = {}
            for item in resultados:
                idx = int(item.get("idx", 0)) - 1
                categoria = str(item.get("categoria", "")).strip()
                if 0 <= idx < len(batch) and categoria in categorias_validas:
                    mid = batch[idx][0]
                    mapa[mid] = categoria
            return mapa

        except Exception as e:
            msg = str(e).lower()
            is_rate_limit = any(k in msg for k in ("429", "resource_exhausted", "quota", "rate limit"))
            if attempt < 6:
                if is_rate_limit:
                    print(f"[GEMINI] Rate limit. Aguardando {delay}s... (tentativa {attempt + 1}/7)")
                    time.sleep(delay)
                    delay = min(delay * 2, 120)
                else:
                    time.sleep(3)
                continue
            print(f"[GEMINI] Falha na classificação de {name}: {e}")
            return {}

# ---------------------------------------------------------------------------
# Engine genérico
# ---------------------------------------------------------------------------

def sincronizar_servico(config, remover_inbox=False):
    """Sincroniza qualquer serviço definido em services.py."""
    service = get_gmail_service()
    if not service:
        return

    name = config["name"]
    label_root = config.get("label_root", name)
    domains = config.get("official_domains")
    categorias = [c["name"] for c in config["categories"]] + [config["default"]]

    # Garante labels (incluindo intermediários como 'Compras', 'Compras/AliExpress')
    by_name = _garantir_labels(service, [f"{label_root}/{c}" for c in categorias])
    cat_ids = {c: by_name[f"{label_root}/{c}"]["id"] for c in categorias}

    # Coleta IDs dos e-mails
    ids = set()
    for q in config["queries"]:
        ids.update(_listar_message_ids(service, q))

    if not ids:
        print(f"{name}: nenhum e-mail encontrado.")
        return

    print(f"{name}: {len(ids)} e-mails encontrados. Buscando conteúdo em paralelo...")

    # Busca todos os e-mails em paralelo
    mensagens = _buscar_mensagens_paralelo(sorted(ids))

    cat_label_ids = set(cat_ids.values())
    nao_oficiais = []
    ja_classificados = 0
    to_classify = []  # (mid, assunto, snippet, corpo)

    for mid, msg in mensagens.items():
        existing = set(msg.get("labelIds") or [])
        if existing & cat_label_ids:
            ja_classificados += 1
            continue

        payload = msg.get("payload") or {}
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        from_addr = headers.get("from", "").lower()

        if domains and not any(d in from_addr for d in domains):
            nao_oficiais.append(mid)
            continue

        assunto = headers.get("subject", "")
        snippet = msg.get("snippet", "")
        corpo = "\n".join(_extrair_textos_payload(payload)[:5])
        to_classify.append((mid, assunto, snippet, corpo))

    if ja_classificados:
        print(f"{name}: {ja_classificados} já classificados, ignorados.")

    add_por_cat = defaultdict(list)

    if client and _allow_ai_processing and to_classify:
        # Classifica com Gemini em batches de 10
        # Intervalo de 4s entre batches para respeitar o rate limit do free tier (~15 RPM)
        batch_size = 10
        total_batches = (len(to_classify) + batch_size - 1) // batch_size
        print(f"{name}: classificando {len(to_classify)} e-mails com Gemini ({total_batches} batch(es))...")

        for i in range(0, len(to_classify), batch_size):
            batch = to_classify[i : i + batch_size]
            resultado = _classificar_batch_gemini(config, batch)

            for mid, categoria in resultado.items():
                add_por_cat[cat_ids[categoria]].append(mid)

            # Fallback para e-mails sem classificação no batch
            classificados = set(resultado.keys())
            for mid, _, _, _ in batch:
                if mid not in classificados:
                    add_por_cat[cat_ids[config["default"]]].append(mid)

    else:
        if not client:
            print(f"{name}: Gemini não disponível (configure GEMINI_API_KEY). Usando categoria padrão.")
        elif not _allow_ai_processing:
            print(
                f"{name}: envio ao Gemini não autorizado. "
                "Use --allow-ai-processing após revisar docs/PRIVACIDADE.md."
            )
        for mid, _, _, _ in to_classify:
            add_por_cat[cat_ids[config["default"]]].append(mid)

    # Aplica labels em batch
    for lid, mids in add_por_cat.items():
        _batch_modificar(service, mids, add_label_ids=[lid])

    if remover_inbox:
        classificados = [m for ms in add_por_cat.values() for m in ms]
        _batch_modificar(service, classificados, remove_label_ids=["INBOX"])

    sufixo = f" (ignorados por domínio: {len(nao_oficiais)})" if nao_oficiais else ""
    print(f"{name}: {len(to_classify)} processados{sufixo}")
    for c in categorias:
        q = f'label:"{label_root}/{c}"'
        print(f"  - {c}: {_contar_query(service, q)}")


def limpar_nao_oficiais(config):
    """Remove labels do serviço de e-mails que não vieram de domínios oficiais."""
    service = get_gmail_service()
    if not service:
        return

    name = config["name"]
    label_root = config.get("label_root", name)
    domains = config.get("official_domains")

    if not domains:
        print(f"{name}: sem filtro de domínios configurado, nada a limpar.")
        return

    all_labels = service.users().labels().list(userId="me").execute().get("labels", [])
    label_ids = [
        l["id"] for l in all_labels
        if l["name"] == label_root or l["name"].startswith(label_root + "/")
    ]
    if not label_ids:
        print(f"{name}: nenhum label encontrado.")
        return

    ids = set(_listar_message_ids(service, f'label:"{label_root}"'))
    if not ids:
        print(f"{name}: nenhum e-mail com esse label.")
        return

    mensagens = _buscar_mensagens_paralelo(list(ids))
    nao_oficiais = []
    for mid, msg in mensagens.items():
        payload = msg.get("payload") or {}
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        from_addr = headers.get("from", "").lower()
        if not any(d in from_addr for d in domains):
            nao_oficiais.append(mid)

    if nao_oficiais:
        _batch_modificar(service, nao_oficiais, remove_label_ids=label_ids)
    print(f"{name}: label removido de {len(nao_oficiais)} e-mails não-oficiais.")

# ---------------------------------------------------------------------------
# Amazon — handler especial (lógica de detecção de comprador/pessoa)
# ---------------------------------------------------------------------------

def _extrair_comprador(texto_norm, pessoas_alvo):
    pessoas = [p.strip() for p in pessoas_alvo if p and p.strip()]
    if not pessoas:
        return None
    pessoas_norm = [_normalizar_texto_busca(p) for p in pessoas]

    encontrados = []
    for nome_orig, nome_norm in zip(pessoas, pessoas_norm):
        if re.search(rf"\b(?:ola|olá|oi)\s*,?\s*{re.escape(nome_norm)}\b", texto_norm, re.IGNORECASE):
            encontrados.append(nome_orig)
    for nome_orig, nome_norm in zip(pessoas, pessoas_norm):
        padrao = re.compile(
            rf"\b{re.escape(nome_norm)}\b[\s\-–,:\n\r]{{0,120}}\brio\s+de\s+janeiro\s*,\s*rj\b",
            re.IGNORECASE,
        )
        if padrao.search(texto_norm):
            encontrados.append(nome_orig)
    if len(encontrados) == 1:
        return encontrados[0]

    blocos = [
        m.group(0) for m in re.finditer(
            r"(entrega|delivery|recipient|destinatario|entregar para|enviar para).{0,240}",
            texto_norm, re.IGNORECASE | re.DOTALL,
        )
    ]
    encontrados = []
    for nome_orig, nome_norm in zip(pessoas, pessoas_norm):
        for bloco in blocos:
            if re.search(rf"\b{re.escape(nome_norm)}\b", bloco):
                encontrados.append(nome_orig)
                break
    return encontrados[0] if len(encontrados) == 1 else None


def _classificar_amazon_com_gemini(assunto, corpo, pessoas_validas):
    if not client:
        return None
    corpo_curto = (corpo or "")[:7000]
    prompt = f"""Leia este e-mail da Amazon e responda APENAS com JSON válido.

Pessoas permitidas: {", ".join(pessoas_validas)}
Tipos permitidos: Entrega, Avaliacao, PosCompra, Pedidos, Pagamentos, Servicos, Geral

Regras:
- pessoa: quem fez a compra ou vai receber a entrega. Use "Indefinido" se não souber.
- tipo: tipo do e-mail. Use "Geral" se não souber.
- confianca: de 1 (baixa) a 5 (certeza absoluta).
- resumo: máximo 1 frase curta.

Formato: {{"pessoa":"...","tipo":"...","confianca":1,"resumo":"..."}}

Assunto: {assunto}
Corpo: {corpo_curto}"""
    try:
        resp = client.models.generate_content(
            model=model_name, contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        txt = (resp.text or "").replace("```json", "").replace("```", "").strip()
        r = json.loads(txt)
        if not isinstance(r, dict):
            return None
        pessoa = str(r.get("pessoa") or "Indefinido").strip()
        if pessoa not in pessoas_validas:
            pessoa = "Indefinido"
        tipo = str(r.get("tipo") or "Geral").strip()
        if tipo not in {"Entrega", "Avaliacao", "PosCompra", "Pedidos", "Pagamentos", "Servicos", "Geral"}:
            tipo = "Geral"
        confianca = min(5, max(1, int(r.get("confianca", 1))))
        resumo = str(r.get("resumo") or "").strip() or "Resumo não informado."
        return {"pessoa": pessoa, "tipo": tipo, "confianca": confianca, "resumo": resumo}
    except Exception:
        return None


def sincronizar_amazon(pessoas_alvo=None, remover_inbox=False):
    service = get_gmail_service()
    if not service:
        return
    pessoas_alvo = [p.strip() for p in (pessoas_alvo or []) if p and p.strip()]
    tipos = ["Pedidos", "Pagamentos", "Servicos", "Geral", "Entrega", "Avaliacao", "PosCompra"]

    labels_base = ["Compras/Amazon/Pessoas/Indefinido"]
    for t in tipos:
        labels_base.append(f"Compras/Amazon/Pessoas/Indefinido/{t}")
    for p in pessoas_alvo:
        labels_base.append(f"Compras/Amazon/Pessoas/{p}")
        for t in tipos:
            labels_base.append(f"Compras/Amazon/Pessoas/{p}/{t}")
    by_name = _garantir_labels(service, labels_base)

    ids = set()
    for q in [
        "from:(amazon.com OR amazon.com.br OR @amazon.com OR @amazon.com.br OR @amazonaws.com)",
        'subject:(amazon OR "amazon.com.br")',
        'label:"Compras/Amazon"',
    ]:
        ids.update(_listar_message_ids(service, q))

    pessoa_ids = {p: by_name[f"Compras/Amazon/Pessoas/{p}"]["id"] for p in pessoas_alvo}
    pessoa_tipo_ids = {
        p: {t: by_name[f"Compras/Amazon/Pessoas/{p}/{t}"]["id"] for t in tipos}
        for p in pessoas_alvo
    }
    indef_id = by_name["Compras/Amazon/Pessoas/Indefinido"]["id"]
    indef_tipo_ids = {t: by_name[f"Compras/Amazon/Pessoas/Indefinido/{t}"]["id"] for t in tipos}
    compras_id = by_name["Compras"]["id"]
    amazon_id = by_name["Compras/Amazon"]["id"]

    add_por_label = defaultdict(list)
    add_por_tipo = defaultdict(list)
    remove_indef = []

    print(f"Amazon: {len(ids)} e-mails encontrados. Buscando em paralelo...")
    mensagens = _buscar_mensagens_paralelo(sorted(ids))

    pessoa_label_id_set = set(pessoa_ids.values())
    ja_classificados = 0

    for mid, msg in mensagens.items():
        existing = set(msg.get("labelIds") or [])
        if existing & pessoa_label_id_set:
            ja_classificados += 1
            continue

        payload = msg.get("payload") or {}
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        assunto = headers.get("subject", "")
        snippet = msg.get("snippet", "")
        corpo = "\n".join(_extrair_textos_payload(payload)[:5])
        texto_norm = _normalizar_texto_busca("\n".join([assunto, snippet, corpo]))

        add_por_label[compras_id].append(mid)
        add_por_label[amazon_id].append(mid)

        comprador = _extrair_comprador(texto_norm, pessoas_alvo)

        # Tipo via keywords simples (rápido, sem custo de API)
        if any(k in texto_norm for k in ["avaliar", "avaliacao", "review", "rate your purchase"]):
            tipo = "Avaliacao"
        elif any(k in texto_norm for k in ["cancelamento", "reembolso", "refund", "devolucao", "nota fiscal"]):
            tipo = "PosCompra"
        elif any(k in texto_norm for k in ["entrega", "enviado", "a caminho", "delivery", "saiu para entrega"]):
            tipo = "Entrega"
        elif any(k in texto_norm for k in ["pagamento", "payment", "recibo", "comprovante"]):
            tipo = "Pagamentos"
        elif any(k in texto_norm for k in ["pedido", "order", "confirmado"]):
            tipo = "Pedidos"
        elif any(k in texto_norm for k in ["prime", "kindle", "audible"]):
            tipo = "Servicos"
        else:
            tipo = "Geral"

        if comprador and comprador in pessoa_ids:
            add_por_label[pessoa_ids[comprador]].append(mid)
            add_por_tipo[pessoa_tipo_ids[comprador][tipo]].append(mid)
            remove_indef.append(mid)
        else:
            add_por_label[indef_id].append(mid)
            add_por_tipo[indef_tipo_ids[tipo]].append(mid)

    for lid, mids in add_por_label.items():
        _batch_modificar(service, mids, add_label_ids=[lid])
    for lid, mids in add_por_tipo.items():
        _batch_modificar(service, mids, add_label_ids=[lid])
    _batch_modificar(service, remove_indef, remove_label_ids=[indef_id])
    if remover_inbox:
        _batch_modificar(service, list(ids), remove_label_ids=["INBOX"])

    if ja_classificados:
        print(f"Amazon: {ja_classificados} já classificados, ignorados.")
    print(f"Amazon: {len(ids) - ja_classificados} processados")
    for p in pessoas_alvo:
        q = f'label:"Compras/Amazon/Pessoas/{p}"'
        print(f"  - {p}: {_contar_query(service, q)}")
    q = 'label:"Compras/Amazon/Pessoas/Indefinido"'
    print(f"  - Indefinido: {_contar_query(service, q)}")


def refinar_amazon_indefinido_com_gemini(pessoas_alvo=None):
    """Usa Gemini para reclassificar os e-mails Amazon que ficaram em Indefinido."""
    service = get_gmail_service()
    if not service:
        return
    if not client:
        print("Gemini não disponível. Configure GEMINI_API_KEY.")
        return
    if not _allow_ai_processing:
        print("Envio ao Gemini bloqueado. Use --allow-ai-processing após revisar a política de privacidade.")
        return

    pessoas_alvo = [p.strip() for p in (pessoas_alvo or []) if p and p.strip()]
    tipos = ["Entrega", "Avaliacao", "PosCompra", "Pedidos", "Pagamentos", "Servicos", "Geral"]

    labels_needed = ["Compras/Amazon/Pessoas/Indefinido"]
    for p in pessoas_alvo:
        labels_needed.append(f"Compras/Amazon/Pessoas/{p}")
        for t in tipos:
            labels_needed.append(f"Compras/Amazon/Pessoas/{p}/{t}")
    by_name = _garantir_labels(service, labels_needed)

    indef_id = by_name["Compras/Amazon/Pessoas/Indefinido"]["id"]
    pessoa_ids = {p: by_name[f"Compras/Amazon/Pessoas/{p}"]["id"] for p in pessoas_alvo}
    tipo_ids = {
        p: {t: by_name[f"Compras/Amazon/Pessoas/{p}/{t}"]["id"] for t in tipos}
        for p in pessoas_alvo
    }

    ids = _listar_message_ids(service, 'label:"Compras/Amazon/Pessoas/Indefinido"')
    if not ids:
        print("Nenhum e-mail em Indefinido para refinar.")
        return

    print(f"Amazon/Indefinido: {len(ids)} e-mails para analisar com Gemini...")
    mensagens = _buscar_mensagens_paralelo(ids)

    movidos = defaultdict(list)  # pessoa -> [(mid, tipo)]

    for mid, msg in mensagens.items():
        payload = msg.get("payload") or {}
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        assunto = headers.get("subject", "")
        corpo = "\n".join(_extrair_textos_payload(payload)[:5])
        snippet = msg.get("snippet", "")

        resultado = _classificar_amazon_com_gemini(assunto, f"{snippet}\n{corpo}", pessoas_alvo)
        if not resultado:
            continue

        pessoa = resultado["pessoa"]
        tipo = resultado["tipo"]
        if pessoa == "Indefinido" or resultado["confianca"] < 3 or pessoa not in pessoa_ids:
            continue

        tipo_real = tipo if tipo in tipo_ids[pessoa] else "Geral"
        movidos[pessoa].append((mid, tipo_real))

    total = 0
    for pessoa, items in movidos.items():
        mids = [m for m, _ in items]
        _batch_modificar(service, mids,
                         add_label_ids=[pessoa_ids[pessoa]],
                         remove_label_ids=[indef_id])
        por_tipo = defaultdict(list)
        for mid, tipo in items:
            por_tipo[tipo].append(mid)
        for tipo, tmids in por_tipo.items():
            _batch_modificar(service, tmids, add_label_ids=[tipo_ids[pessoa][tipo]])
        total += len(mids)

    print(f"Refinados com Gemini: {total}")
    for p in pessoas_alvo:
        q = f'label:"Compras/Amazon/Pessoas/{p}"'
        print(f"  - {p}: {_contar_query(service, q)}")
    q = 'label:"Compras/Amazon/Pessoas/Indefinido"'
    print(f"  - Indefinido restante: {_contar_query(service, q)}")

# ---------------------------------------------------------------------------
# Band — handler especial (move para lixeira, não cria labels)
# ---------------------------------------------------------------------------

def excluir_band_inuteis():
    service = get_gmail_service()
    if not service:
        return
    ids = set(_listar_message_ids(service, "in:inbox from:(band.com.br OR @band.com.br OR @minhaband.com.br)"))
    if not ids:
        print("Band: nenhum e-mail encontrado.")
        return
    if not _allow_trash and not _dry_run:
        print("Operação bloqueada. Revise com --dry-run e repita com --confirm-trash.")
        return

    mensagens = _buscar_mensagens_paralelo(list(ids))
    inutil_ids = []
    palavras_inuteis = [
        "bom dia", "boa tarde", "resenha", "noticia", "noticias", "aconteceu",
        "resumo", "newsletter", "promocao", "promo", "oferta", "destaques",
        "confira", "veja", "acompanhe", "gp", "formula 1", "f1", "automobilismo",
        "esporte na band", "band.com.br",
    ]
    for mid, msg in mensagens.items():
        payload = msg.get("payload") or {}
        headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
        texto = _normalizar_texto_busca(headers.get("subject", "") + " " + msg.get("snippet", ""))
        if any(k in texto for k in palavras_inuteis):
            inutil_ids.append(mid)

    if inutil_ids:
        print(f"Band: movendo {len(inutil_ids)} e-mails para a lixeira...")
        _batch_modificar(service, inutil_ids, add_label_ids=["TRASH"], remove_label_ids=["INBOX"])
    else:
        print("Band: nenhum e-mail inútil encontrado.")

# ---------------------------------------------------------------------------
# Caixa de entrada genérica (usado quando nenhuma flag é passada)
# ---------------------------------------------------------------------------

def processar_caixa_entrada(count=50):
    service = get_gmail_service()
    if not service:
        return
    if not client:
        print("Gemini não disponível. Configure GEMINI_API_KEY.")
        return
    if not _allow_ai_processing:
        print("Envio ao Gemini bloqueado. Use --allow-ai-processing após revisar docs/PRIVACIDADE.md.")
        return

    _CAT_MAP = {
        "TRABALHO":   "Geral/Trabalho",
        "ACADEMICO":  "Geral/Academico",
        "PESSOAL":    "Geral/Pessoal",
        "FINANCEIRO": "Geral/Financeiro",
        "SPAM":       "Geral/Spam",
    }
    by_name = _garantir_labels(service, list(_CAT_MAP.values()))

    print(f"Buscando {count} e-mails não lidos...")
    resp = service.users().messages().list(userId="me", q="is:unread", maxResults=count).execute()
    all_ids = [m["id"] for m in resp.get("messages", [])]
    if not all_ids:
        print("Nenhum e-mail não lido.")
        return

    msgs = _buscar_mensagens_paralelo(all_ids)

    to_classify = []
    meta = {}
    for mid in all_ids:
        msg = msgs.get(mid)
        if not msg:
            continue
        payload = msg.get("payload") or {}
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        assunto = headers.get("Subject", "Sem assunto")
        snippet = msg.get("snippet", "")
        corpo = "\n".join(_extrair_textos_payload(payload))[:2000]
        frm = headers.get("From", "?")
        to_classify.append((mid, assunto, snippet, corpo))
        meta[mid] = {"frm": frm, "assunto": assunto}

    batch_size = 10
    total = len(to_classify)
    n_batches = (total + batch_size - 1) // batch_size
    print(f"Classificando {total} e-mails ({n_batches} batch(es))...\n")

    resultados = {}
    for i in range(0, total, batch_size):
        lote = to_classify[i : i + batch_size]
        resultados.update(_classificar_inbox_batch(lote))

    # Aplica labels
    add_por_label = defaultdict(list)
    lixeira = []
    for mid, *_ in to_classify:
        r = resultados.get(mid)
        if not r:
            continue
        cat = r["categoria"]
        if cat in ("NEWSLETTER", "SPAM"):
            lixeira.append(mid)
        else:
            label_name = _CAT_MAP.get(cat)
            if label_name:
                add_por_label[by_name[label_name]["id"]].append(mid)

    for lid, mids in add_por_label.items():
        _batch_modificar(service, mids, add_label_ids=[lid])
    if lixeira:
        _batch_modificar(service, lixeira, add_label_ids=["TRASH"], remove_label_ids=["INBOX"])

    # Relatório
    contagem = defaultdict(int)
    urgentes = []

    print("=" * 65)
    print(f"RELATÓRIO — {total} e-mails processados")
    print("=" * 65)

    for mid, *_ in to_classify:
        r = resultados.get(mid, {"categoria": "?", "urgencia": 1, "resumo": ""})
        m = meta[mid]
        cat = r["categoria"]
        urg = r["urgencia"]
        contagem[cat] += 1
        apagado = cat in ("NEWSLETTER", "SPAM")
        marcador = "[APAGADO]" if apagado else f"[{cat}]"
        print(f"\n{marcador}  urgência {urg}/5")
        print(f"  De     : {m['frm'][:70]}")
        print(f"  Assunto: {m['assunto'][:80]}")
        if r["resumo"]:
            print(f"  Resumo : {r['resumo']}")
        if urg >= 4:
            urgentes.append((m["assunto"], m["frm"], r["resumo"]))

    print("\n" + "=" * 65)
    print("RESUMO POR CATEGORIA")
    print("=" * 65)
    for cat in ["TRABALHO", "FINANCEIRO", "PESSOAL", "ACADEMICO", "NEWSLETTER", "SPAM"]:
        n = contagem.get(cat, 0)
        if not n:
            continue
        suffix = " → lixeira" if cat in ("NEWSLETTER", "SPAM") else ""
        print(f"  {cat:<12} {n}{suffix}")

    if urgentes:
        print("\nREQUER ATENÇÃO (urgência >= 4):")
        for assunto, frm, resumo in urgentes:
            print(f"  • {assunto[:60]}")
            if resumo:
                print(f"    {resumo}")

    # Gera PDF
    emails_pdf = [
        (mid, resultados[mid]["categoria"], resultados[mid]["urgencia"],
         resultados[mid]["resumo"], meta[mid]["frm"], meta[mid]["assunto"])
        for mid, *_ in to_classify
        if mid in resultados
    ]
    caminho_pdf = gerar_pdf(emails_pdf)
    print(f"\nRelatório PDF salvo: {caminho_pdf}")

# ---------------------------------------------------------------------------
# CLI dinâmico — gerado automaticamente a partir de SERVICES
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(
        description="Organizador de e-mails Gmail com Gemini",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Flags geradas automaticamente para cada serviço
    for cfg in SERVICES:
        slug = _slug(cfg["name"])
        parser.add_argument(
            f"--sync-{slug}", action="store_true",
            help=f"Sincroniza e-mails de {cfg['name']}",
        )
        if cfg.get("official_domains"):
            parser.add_argument(
                f"--limpar-{slug}", action="store_true",
                help=f"Remove labels '{cfg['name']}' de e-mails não-oficiais",
            )

    # Handlers especiais
    parser.add_argument("--sync-amazon", action="store_true", help="Sincroniza e-mails da Amazon (com detecção de comprador)")
    parser.add_argument("--refine-amazon-indefinido", action="store_true", help="Usa Gemini para reclassificar Amazon/Indefinido")
    parser.add_argument("--delete-band-inuteis", action="store_true", help="Move newsletters da Band para a lixeira")

    # Opções globais
    parser.add_argument("--sync-all", action="store_true", help="Sincroniza todos os serviços de SERVICES + Amazon")
    parser.add_argument("--process-inbox", action="store_true", help="Classifica e-mails não lidos da caixa de entrada")
    parser.add_argument("--remove-inbox", action="store_true", help="Remove INBOX dos e-mails classificados")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o que seria feito sem aplicar labels")
    parser.add_argument(
        "--allow-ai-processing", action="store_true",
        help="Autoriza o envio de trechos de e-mails ao Gemini nesta execução",
    )
    parser.add_argument(
        "--confirm-trash", action="store_true",
        help="Autoriza mover mensagens para a lixeira nesta execução",
    )
    parser.add_argument("--count", type=int, default=50, help="Quantidade de e-mails a processar na caixa de entrada (padrão: 50)")
    parser.add_argument(
        "--people", nargs="*", default=[],
        help="Nomes para detecção de comprador na Amazon (ex: --people Ana Bruno)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _dry_run = args.dry_run
    _allow_ai_processing = args.allow_ai_processing
    _allow_trash = args.confirm_trash
    ri = args.remove_inbox
    handled = False

    if args.sync_all:
        for cfg in SERVICES:
            print(f"\n{'='*50}\n{cfg['name']}\n{'='*50}")
            sincronizar_servico(cfg, remover_inbox=ri)
        print(f"\n{'='*50}\nAmazon\n{'='*50}")
        sincronizar_amazon(pessoas_alvo=args.people, remover_inbox=ri)
        handled = True
    else:
        for cfg in SERVICES:
            slug_attr = _slug(cfg["name"]).replace("-", "_")
            if getattr(args, f"sync_{slug_attr}", False):
                sincronizar_servico(cfg, remover_inbox=ri)
                handled = True
            if cfg.get("official_domains") and getattr(args, f"limpar_{slug_attr}", False):
                limpar_nao_oficiais(cfg)
                handled = True

        if args.sync_amazon:
            sincronizar_amazon(pessoas_alvo=args.people, remover_inbox=ri)
            handled = True
        if args.refine_amazon_indefinido:
            refinar_amazon_indefinido_com_gemini(pessoas_alvo=args.people)
            handled = True
        if args.delete_band_inuteis:
            excluir_band_inuteis()
            handled = True

        if args.process_inbox:
            processar_caixa_entrada(count=args.count)
            handled = True

    if not handled:
        print("Nenhuma ação selecionada. Use --help para ver os comandos disponíveis.")
