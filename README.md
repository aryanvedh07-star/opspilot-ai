# OpsPilot AI — free portfolio prototype

This is a functional prototype for an AI business operations copilot. It includes:
- Company document upload and question answering (TXT, MD, CSV, PDF, DOCX)
- AI-assisted research/analysis based on user-supplied public notes and URLs
- Basic exact duplicate-payment screening for CSV files
- Email reply drafting (draft only; no sending)
- AgentGate policy-decision and approval demo
- Session audit log and CSV export

## Important limits
- It is not a production system or a complete autonomous agent.
- Web research is not automatically fetched in this version. Supply evidence/URLs in the research box.
- Financial checks flag possible duplicates, not confirmed fraud or loss.
- AgentGate decisions are a UI demonstration, not a production security boundary.
- No external email, phone, bank, CRM, or payment actions are executed.
- Data and audit events live in the current Streamlit session and may reset.
- Do not upload confidential company/customer/financial data to a public demo.
- If using the Gemini API, review the provider's current data and pricing terms. Free-tier limits can change.

## Fastest way to publish for free
1. Create/sign in to GitHub.
2. Create a new **public** repository named `opspilot-ai`.
3. Upload `app.py`, `requirements.txt`, and `README.md` from this folder.
4. Open Streamlit Community Cloud and connect GitHub.
5. Click **Create app**.
6. Select repository `opspilot-ai`, branch `main`, main file path `app.py`.
7. Click **Deploy**.
8. In the deployed app, enter your Gemini API key in the sidebar to enable AI-generated responses. Do not publish your API key in GitHub.

Official deploy guide: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app

## Create a Gemini API key
1. Open https://aistudio.google.com/apikey
2. Sign in and create an API key if the option is available.
3. Paste it into the app's sidebar for a quick personal test.
4. For a shared/public production app, never ask visitors to paste their own keys as a product design. Configure your own key in Streamlit's server-side Secrets and enforce authentication, rate limits, and usage limits first.

Gemini API pricing and free tier: https://ai.google.dev/gemini-api/docs/pricing

## Run locally (optional)
Install Python 3.11 or newer, then open a terminal in this folder:
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Suggested next engineering milestones
1. Add persistent database storage with per-user access control.
2. Add source-aware retrieval and chunking rather than placing whole documents into the prompt.
3. Add real web-search integration with source extraction and timestamps.
4. Add OAuth integrations only after secrets management and user authentication are implemented.
5. Route every external tool call through server-side policy checks; do not trust the UI.
6. Add tests for authorization, prompt injection, duplicate execution, retries, and audit integrity.
7. Measure actual time saved and verified outcomes with consenting pilot users.
