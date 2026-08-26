# SurveyAI Live Deployment Guide

> [!CRITICAL]
> **CRITICAL DEPLOYMENT RULES:**
> 1. **Application Entry File:** The backend entry point MUST ALWAYS be named [`app.py`](file:///d:/SUNIL%20KUMAWAT/survey-ai-create/app.py). Do NOT rename or replace `app.py` as Windows services, systemd, and Apache supervisor rely specifically on `python app.py` to start the application.
> 2. **Backend Communication Port:** The Apache reverse proxy for `https://ai-surveycreate.qdegrees.com/` is configured to communicate with backend port **5005** (`PORT=5005`).

Since you are hosting this directly from your project folder (`d:\SUNIL KUMAWAT\survey-ai-create`), here are the exact steps to transition your local environment into a live production environment.

## 1. Create & Activate Virtual Environment
Before installing anything, ensure you are working inside a clean virtual environment. 

Open your terminal (PowerShell or Command Prompt), ensure you are in the `d:\SUNIL KUMAWAT\survey-ai-create` folder, and run:
```powershell
python -m venv venv
```
Activate the virtual environment:
```powershell
.\venv\Scripts\activate
```

## 2. Install Required Dependencies
With your virtual environment active, install all required packages (this includes `waitress`, which handles live internet traffic safely with multi-threading). 

```powershell
pip install -r requirements.txt
```

## 3. Verify Environment Variables
Ensure your `.env` file is set up correctly in the root folder. It must contain your active OpenAI API key, `FLASK_ENV="production"`, and `PORT=5005` so the reverse proxy connects seamlessly.

```env
OPENAI_API_KEY="your_openai_api_key_here"
FLASK_ENV="production"
PORT=5005
```

## 4. Allow Traffic Through Windows Firewall
By default, Windows Firewall blocks incoming traffic to port 5005. You must allow it so external users & local proxies can reach your API.

**Option A (Fastest - Run in Administrator PowerShell):**
```powershell
New-NetFirewallRule -DisplayName "SurveyAI Flask Port 5005" -Direction Inbound -LocalPort 5005 -Protocol TCP -Action Allow
```

**Option B (Manual Windows GUI):**
1. Open **Windows Defender Firewall with Advanced Security**.
2. Click **Inbound Rules** > **New Rule...**
3. Select **Port**, click Next.
4. Select **TCP** and specify local port **5005**, click Next.
5. Select **Allow the connection**, click Next.
6. Name the rule (e.g., "Flask Survey API Port 5005") and save.

## 5. Run the Live Server
Start your application using the standard entry command:

```powershell
python app.py
```
*You will see the console output:*
`[INFO] Starting production server with Waitress on http://0.0.0.0:5005 ...`

## 6. Keep the Server Running (Optional)
If you close the terminal window, the API will go offline. To keep it running in the background persistently on your Windows machine, you can run the command using a tool like **NSSM (Non-Sucking Service Manager)** to install `python app.py` as a background Windows Service on port 5005.

---
**Your API is now live!** 
- Apache Reverse Proxy Domain: **[https://ai-surveycreate.qdegrees.com/](https://ai-surveycreate.qdegrees.com/)**
- Local Backend Service: **[http://127.0.0.1:5005](http://127.0.0.1:5005)**
*(Note: CORS is fully enabled, meaning your APIs can be securely called from any external web domain without browser errors).*
