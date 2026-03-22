# Lumin Backend

The Flask backend powering [meetlumin.com](https://meetlumin.com) — Lumin's public presence.

## What this does
- Hides all API keys from public users
- Serves Lumin's chat, farming advisor, and climate news endpoints
- Deployed on Render (free tier)

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | / | Health check |
| GET | /status | Lumin's capabilities |
| POST | /chat | General conversation |
| POST | /farm | Farming advisor |
| POST | /climate | Climate news insights |

## Environment Variables (set in Render dashboard)
```
GROQ_API_KEY=your_groq_key
SERPAPI_API_KEY=your_serpapi_key
```

## Deploy to Render
1. Push this repo to GitHub
2. Create new Web Service on Render
3. Connect this GitHub repo
4. Add environment variables
5. Deploy

Built by Siya — creator of Lumin 🌟
