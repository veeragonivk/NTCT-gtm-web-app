
# GTM Chat (Flask + LLM + Azure Function Apps)

A lightweight chat webapp that:
- Uses an LLM to **route intent** (item details vs CoC certification)
- **Slot-fills** missing parameters (asks for item/model, optional country)
- Calls your **Azure Function Apps** via GET and displays the result

## 1) Prereqs
- Python 3.10+
- Function Apps:
  - get_item_info (expects `?code=...&item=...`)
  - get_coc_cert (expects `?code=...&model_item=...&country_query=...` [optional])
- OpenAI or Azure OpenAI for intent routing

## 2) Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
