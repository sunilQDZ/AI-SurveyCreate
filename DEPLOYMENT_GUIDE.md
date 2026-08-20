# SurveyAI Live Deployment Guide

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
Ensure your `.env` file is set up correctly in the root folder. It must contain your active OpenAI API key and be set to production mode so it uses the Waitress server instead of the Flask development server.

```env
OPENAI_API_KEY="your_openai_api_key_here"
FLASK_ENV="production"
```

## 4. Allow Traffic Through Windows Firewall
By default, Windows Firewall blocks incoming traffic to port 5000. You must allow it so external users can reach your API.

**Option A (Fastest - Run in Administrator PowerShell):**
```powershell
New-NetFirewallRule -DisplayName "SurveyAI Flask Port 5000" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

**Option B (Manual Windows GUI):**
1. Open **Windows Defender Firewall with Advanced Security**.
2. Click **Inbound Rules** > **New Rule...**
3. Select **Port**, click Next.
4. Select **TCP** and specify local port **5000**, click Next.
5. Select **Allow the connection**, click Next.
6. Name the rule (e.g., "Flask Survey API Port 5000") and save.

## 5. Run the Live Server
Start your application using the normal command. Because `FLASK_ENV="production"` is set, it will automatically launch the high-performance Waitress server.

```powershell
python app.py
```
*You will see the console output:*
`Starting production server with Waitress on http://0.0.0.0:5000 ...`

## 6. Keep the Server Running (Optional)
If you close the terminal window, the API will go offline. To keep it running in the background persistently on your Windows machine, you can run the command using a tool like **NSSM (Non-Sucking Service Manager)** to install `python app.py` as a background Windows Service.

---
**Your API is now live!** 
- To view or test it locally, click: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**
- External users and frontend apps can access the APIs by sending POST requests to your machine's IP address on port 5000 (e.g., `http://YOUR_IP_ADDRESS:5000`). 
*(Note: CORS is fully enabled, meaning your APIs can be securely called from any external web domain without browser errors).*
