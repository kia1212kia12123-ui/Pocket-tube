# PocketTube Studio — Netlify Frontend

## Deploy from Android
1. Download this ZIP and extract it on your phone.
2. Sign in at https://app.netlify.com/drop (or open Netlify dashboard → Add new project → Deploy manually).
3. Upload the `public` folder (not the whole project root) to Netlify's drop area. If the UI only accepts a ZIP, upload this ZIP and follow Netlify's prompts; otherwise extract it and select `public`.
4. Netlify will publish a static site URL.

## Important
This is the Netlify-hosted frontend only. Netlify static hosting does not run the existing FastAPI/FFmpeg Python app as a persistent server. Full functionality requires hosting `app.py` separately on a Python-compatible host/VPS, then integrating the frontend API calls, configuring CORS, persistent storage, and secure OAuth secrets. Do not put `client_secret.json` or Google tokens in the public frontend.
