import os
import json
import requests

SYSTEM_PROMPT = """You are an intent router for a GTM assistant.
Output ONLY valid JSON with keys: intent, params, missing.
Intents:
- item_details: for item/product lookups
- coc_details: for country of conformity / CoC questions
- report: for BI report requests
- tracking: for sales order tracking requests
- unknown: if unclear

Params schema:
- item (string, optional)
- product (string, optional)  # synonym for item
- model_item (string, optional)
- country_query (string, optional)  # country name used for CoC queries
- report_name (string, optional)  # "PackSlip", "Commercial Invoice", "SLI"
- sales_order (string, optional)
- delivery_name (string, optional)
- po_number (string, optional)
"""

USER_GUIDE = """Extract intent and params from the user's message.
Rules:
- If user asks for item/product info → intent=item_details; expect `item` or `product`.
- If user asks for CoC/country of conformity → intent=coc_details; expect `model_item` and optional `country_query`.
- If user asks for a report → intent=report; expect `report_name` and at least one of `sales_order`, `delivery_name`, `po_number`.
- If user asks for tracking → intent=tracking; expect `sales_order`.
- missing: list of required params not present yet.

Examples:
- "Find details of item 4910" → intent=item_details, params.item="4910", missing=[]
- "COC for model NATL in Uganda" → intent=coc_details, params.model_item="NATL", params.country_query="Uganda", missing=[]
- "Get PackSlip for delivery 17749190" → intent=report, params.report_name="PackSlip", params.delivery_name="17749190", missing=[]
- "Track sales order 1047644" → intent=tracking, params.sales_order="1047644", missing=[]
Return JSON only.
"""

def route_intent(user_message: str) -> dict:
    """
    Uses AI Hub to classify intent and extract parameters.
    Returns a dict: {intent, params, missing}
    """
    base_url = os.getenv("AIHUB_BASE_URL", "https://aihub.netscout.com/api/v1").rstrip("/")
    token = os.getenv("AIHUB_API_KEY")
    model = os.getenv("AIHUB_MODEL", "gpt-5")

    if not token:
        return {"intent": "unknown", "params": {}, "missing": [], "error": "Missing AIHUB_API_KEY"}

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0,
        "stream": False,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_GUIDE + "\n\nUser: " + user_message},
        ],
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
    except Exception as e:
        return {"intent": "unknown", "params": {}, "missing": [], "error": f"LLM network error: {e}"}

    if not resp.ok:
        snippet = resp.text[:400].replace("\n", " ")
        return {"intent": "unknown", "params": {}, "missing": [], "error": f"LLM call failed ({resp.status_code}): {snippet}"}

    ctype = (resp.headers.get("Content-Type") or "").lower()

    if "application/json" in ctype:
        try:
            obj = resp.json()
            content = _extract_text(obj)
            return _parse_router_json(content)
        except Exception:
            body = resp.text
            combined = _parse_sse_body(body)
            return _parse_router_json(combined)

    body = resp.text
    combined = _parse_sse_body(body)
    return _parse_router_json(combined)


def _extract_text(obj: dict) -> str:
    if not isinstance(obj, dict):
        return ""
    choices = obj.get("choices")
    if isinstance(choices, list) and choices:
        ch = choices[0]
        if isinstance(ch.get("message"), dict):
            content = ch["message"].get("content")
            if isinstance(content, str):
                return content
    return ""


def _parse_sse_body(body: str) -> str:
    output = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if line == "[DONE]":
            break
        try:
            obj = json.loads(line)
            choices = obj.get("choices")
            if isinstance(choices, list) and choices:
                ch = choices[0]
                if isinstance(ch.get("delta"), dict):
                    piece = ch["delta"].get("content")
                    if isinstance(piece, str) and piece:
                        output.append(piece)
                elif isinstance(ch.get("message"), dict):
                    content = ch["message"].get("content")
                    if isinstance(content, str) and content:
                        output.append(content)
        except Exception:
            pass
    return "".join(output).strip()


def _parse_router_json(content: str) -> dict:
    try:
        data = json.loads(content)
        data.setdefault("intent", "unknown")
        data.setdefault("params", {})
        data.setdefault("missing", [])
        return data
    except Exception:
        return {"intent": "unknown", "params": {}, "missing": [], "error": "Router returned non-JSON"}
