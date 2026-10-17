# PocketTube Studio — Render backend package

## Deploy using Android + GitHub + Render
1. Extract this ZIP.
2. Upload these files (`app.py`, `requirements.txt`, `render.yaml`) into a new GitHub repository. You can do this in the GitHub website on your phone, or use the GitHub mobile/web interface to upload files.
3. Open https://dashboard.render.com and sign in.
4. Choose **New + → Blueprint** and select the repository containing `render.yaml`, or choose **New + → Web Service**, connect the repository, set Runtime to Python, build command `pip install -r requirements.txt`, and start command `uvicorn app:app --host 0.0.0.0 --port $PORT`.
5. Choose the Free instance plan and deploy.
6. When it finishes, open `https://YOUR-SERVICE.onrender.com/health`. It should return `{"ok":true,"service":"PocketTube Studio API"}`.
7. In Render Environment, set `FRONTEND_ORIGINS` to your exact Netlify URL, such as `https://your-site.netlify.app`. Do not leave `*` for a public production app.
8. Redeploy, then connect the Netlify frontend to this backend URL.

## Important limitations and security
- This is a starter backend, not a production-secure multi-user service. Add authentication before letting other people use it.
- Render free services sleep after 15 minutes of inactivity; the first request after sleep may take about a minute.
- Render free filesystems are ephemeral. Uploaded media, generated MP4s, and OAuth token files can disappear after restart/redeploy/sleep. Do not treat this as permanent storage.
- Video rendering may exceed free memory/time limits. For reliability, render locally on your Android/PC or use a separate worker with adequate resources.
- The current YouTube OAuth helper was originally written for a local desktop flow. YouTube publishing on a remote host requires a web-server OAuth flow and a registered redirect URL; don't upload `client_secret.json` to GitHub. Add secrets only as Render environment variables or a secure secret store after updating the auth code.
- The current frontend still needs API integration for the production actions. A backend URL alone will not automatically connect all buttons.
- Never commit API keys, OAuth secrets, tokens, or user content to a public repository.
