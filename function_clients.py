import os
import requests

TIMEOUT = 30  # seconds

# Existing Function Apps
FA1_URL = os.getenv("FUNCTIONAPP1_URL")
FA1_CODE = os.getenv("FUNCTIONAPP1_CODE")

FA2_URL = os.getenv("FUNCTIONAPP2_URL")
FA2_CODE = os.getenv("FUNCTIONAPP2_CODE")

# New Function Apps
FA_REPORT_URL = os.getenv("FUNCTIONAPP_REPORT_URL")
FA_REPORT_CODE = os.getenv("FUNCTIONAPP_REPORT_CODE")

FA_TRACKING_URL = os.getenv("FUNCTIONAPP_TRACKING_URL")
FA_TRACKING_CODE = os.getenv("FUNCTIONAPP_TRACKING_CODE")


def call_function_app1(item_or_product: str) -> dict:
    """Item Details"""
    if not FA1_URL or not FA1_CODE:
        return {"text": "❌ FunctionApp1 configuration missing."}
    params = {"code": FA1_CODE, "item": item_or_product}
    try:
        r = requests.get(FA1_URL, params=params, timeout=TIMEOUT)
        if r.status_code == 404:
            return {"text": f"❌ Item **{item_or_product}** not found in the database."}
        r.raise_for_status()
        return _parse_response(r)
    except requests.RequestException as e:
        return {"text": f"❌ Error retrieving item **{item_or_product}**: {e}"}


def call_function_app2(model_item: str, country_query: str | None) -> dict:
    """CoC Details"""
    if not FA2_URL or not FA2_CODE:
        return {"text": "❌ FunctionApp2 configuration missing."}
    params = {"code": FA2_CODE, "model_item": model_item}
    if country_query:
        params["country_query"] = country_query
    try:
        r = requests.get(FA2_URL, params=params, timeout=TIMEOUT)
        if r.status_code == 404:
            return {"text": f"❌ Model item **{model_item}** is not found or not certified."}
        r.raise_for_status()
        return _parse_response(r)
    except requests.RequestException as e:
        return {"text": f"❌ Error retrieving CoC for **{model_item}**: {e}"}


def call_function_app_report(report_name: str, sales_order=None, delivery_name=None, po_number=None) -> dict:
    """BI Report"""
    if not FA_REPORT_URL or not FA_REPORT_CODE:
        return {"text": "❌ Report FunctionApp configuration missing."}

    payload = {"report": report_name}
    if sales_order:
        payload["sales_order"] = sales_order
    if delivery_name:
        payload["delivery_name"] = delivery_name
    if po_number:
        payload["po_number"] = po_number

    headers = {"Content-Type": "application/json"}
    params = {"code": FA_REPORT_CODE}

    try:
        r = requests.post(FA_REPORT_URL, params=params, json=payload, headers=headers, timeout=TIMEOUT)
        if r.status_code == 404:
            return {"text": f"❌ Report **{report_name}** not found or invalid parameters."}
        r.raise_for_status()
        return _parse_response(r)
    except requests.RequestException as e:
        return {"text": f"❌ Error generating report **{report_name}**: {e}"}


def call_function_app_tracking(sales_order: str) -> dict:
    """Tracking Info"""
    if not FA_TRACKING_URL or not FA_TRACKING_CODE:
        return {"text": "❌ Tracking FunctionApp configuration missing."}
    params = {"code": FA_TRACKING_CODE, "sales_order": sales_order}
    try:
        r = requests.get(FA_TRACKING_URL, params=params, timeout=TIMEOUT)
        if r.status_code == 404:
            return {"text": f"❌ Tracking info not found for sales order **{sales_order}**."}
        r.raise_for_status()
        return _parse_response(r)
    except requests.RequestException as e:
        return {"text": f"❌ Error retrieving tracking info for **{sales_order}**: {e}"}


def _parse_response(resp: requests.Response) -> dict:
    """Return JSON if content-type is application/json, else return {'text': str}."""
    ct = resp.headers.get("Content-Type", "")
    if "application/json" in ct:
        return resp.json()
    return {"text": resp.text.strip()}
