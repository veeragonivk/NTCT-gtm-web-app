import os
import re
from uuid import uuid4
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from llm_router import route_intent
from function_clients import (
    call_function_app1,       # Item Details
    call_function_app2,       # CoC Details
    call_function_app_report, # BI Report
    call_function_app_tracking# Tracking
)

load_dotenv()
app = Flask(__name__, static_url_path="/static")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

# Simple in-memory pending state (replace with Redis in production)
pending = {}

def _get_session_id():
    sid = session.get("sid")
    if not sid:
        sid = str(uuid4())
        session["sid"] = sid
    return sid

@app.route("/")
def index():
    return render_template("index.html")


@app.post("/chat")
def chat():
    sid = _get_session_id()
    payload = request.get_json(force=True) or {}
    user_msg = (payload.get("message") or "").strip()
    incoming_params = payload.get("params") or {}

    # Consume pending parameters if any
    state = pending.get(sid)
    if state and state.get("awaiting_params"):
        state["collected"].update({k: v for k, v in incoming_params.items() if v})
        remaining = [p for p in state["required"] if not _has_value(p, state["collected"])]
        if remaining:
            pending[sid] = state
            return jsonify({
                "reply": f"I still need: {', '.join(remaining)}.",
                "ask_params": True,
                "required": remaining,
                "optional": state.get("optional", [])
            })
        # All required params collected → call function
        intent = state["intent"]
        pending.pop(sid, None)
        try:
            result = _call_function_by_intent(intent, state["collected"])
        except Exception as e:
            return jsonify({"reply": f"Error calling service: {e}", "ask_params": False})
        return jsonify({"reply": format_result(result), "ask_params": False})

    # Fresh message → route via LLM
    routing = route_intent(user_msg)
    intent = routing.get("intent", "unknown")
    params = routing.get("params", {})

    if intent == "unknown":
        return jsonify({"reply": "Do you want item/product details, CoC info, reports, or tracking info?", "ask_params": False})

    # Determine required params and pending state
    required, optional, prompt_label = _get_required_optional(intent, params)
    if required or prompt_label:
        pending[sid] = {
            "awaiting_params": True,
            "intent": intent,
            "required": required,
            "optional": optional,
            "collected": params.copy()
        }
        prompt_text = ""
        if required:
            prompt_text += f"{', '.join(required)}"
        if prompt_label:
            prompt_text += f"{', ' if prompt_text else ''}{prompt_label}"
        return jsonify({
            "reply": f"Please provide the following: {prompt_text}.",
            "ask_params": True,
            "required": required,
            "optional": optional
        })

    # All required params available → call function
    try:
        result = _call_function_by_intent(intent, params)
    except Exception as e:
        return jsonify({"reply": f"Error calling service: {e}", "ask_params": False})

    return jsonify({"reply": format_result(result), "ask_params": False})


def _has_value(key: str, collected: dict) -> bool:
    """Check if at least one value is provided for combined required field."""
    if key == "sales_order/delivery_name/po_number":
        return any(collected.get(k) for k in ["sales_order", "delivery_name", "po_number"])
    return bool(collected.get(key))


def _get_required_optional(intent: str, params: dict) -> tuple[list[str], list[str], str | None]:
    required = []
    optional = []
    prompt_label = None

    if intent == "item_details":
        if not (params.get("item") or params.get("product")):
            required = ["item"]
    elif intent == "coc_details":
        if not params.get("model_item"):
            required = ["model_item"]
        optional = ["country_query"]
    elif intent == "report":
        if not params.get("report_name"):
            required = ["report_name"]
        if not (params.get("sales_order") or params.get("delivery_name") or params.get("po_number")):
            prompt_label = "sales_order/delivery_name/po_number"
        optional = ["sales_order", "delivery_name", "po_number"]
    elif intent == "tracking":
        if not params.get("sales_order"):
            required = ["sales_order"]
        optional = []

    return required, optional, prompt_label


def _call_function_by_intent(intent: str, params: dict) -> dict:
    if intent == "item_details":
        val = params.get("item") or params.get("product")
        return call_function_app1(val)
    elif intent == "coc_details":
        return call_function_app2(
            model_item=params["model_item"],
            country_query=params.get("country_query")
        )
    elif intent == "report":
        return call_function_app_report(
            report_name=params.get("report_name"),
            sales_order=params.get("sales_order"),
            delivery_name=params.get("delivery_name"),
            po_number=params.get("po_number")
        )
    elif intent == "tracking":
        return call_function_app_tracking(
            sales_order=params.get("sales_order")
        )
    else:
        return {"text": "Unknown intent."}


def format_result(result: dict) -> str:
    """
    Format Function App responses neatly.
    - Item details: line-by-line key-value.
    - PDF URLs clickable.
    """
    if "text" in result and isinstance(result["text"], str):
        txt = result["text"].strip()

        # Item details formatting
        if "Item Name" in txt:
            txt = txt.replace("**", "")
            pattern = re.compile(r"([A-Za-z0-9\s]+):\s*([^:]+)(?=\s+[A-Za-z0-9\s]+:|$)")
            matches = pattern.findall(txt)
            if matches:
                lines = [f"{key.strip():<20}: {value.strip()}" for key, value in matches]
                return "\n".join(lines)

        # Convert PDF URLs to clickable links
        url_pattern = re.compile(r"(https?://[^\s]+\.pdf[^\s]*)")
        txt = url_pattern.sub(r'<a href="\1" target="_blank">\1</a>', txt)

        # Clean up lines
        lines = [line.strip() for line in txt.splitlines() if line.strip()]
        return "\n".join(lines)

    # JSON fallback
    return "\n".join([f"{k}: {v}" for k, v in result.items()])


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
