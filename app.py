import os, re, json, uuid, shutil, subprocess, textwrap, secrets
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"
STATIC = ROOT / "static"
PROJECTS.mkdir(exist_ok=True)
STATIC.mkdir(exist_ok=True)
app = FastAPI(title="PocketTube Studio API")
# Set FRONTEND_ORIGINS to your Netlify URL, e.g. https://your-site.netlify.app
_origins = [x.strip() for x in os.environ.get("FRONTEND_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

def safe_id(value):
    return re.sub(r"[^a-zA-Z0-9_-]", "", value)[:48]

def project_dir(pid):
    p = PROJECTS / safe_id(pid)
    if not safe_id(pid) or not p.exists():
        raise HTTPException(404, "Project not found")
    return p

def run_cmd(args):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=900)
    except FileNotFoundError:
        raise HTTPException(500, f"Required program not installed: {args[0]}")
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Rendering timed out. Try fewer/shorter assets.")
    if p.returncode != 0:
        raise HTTPException(500, (p.stderr or p.stdout)[-1800:])
    return p.stdout

def script_template(topic, style, duration):
    topic = topic.strip() or "a useful everyday idea"
    duration = max(15, min(int(duration or 60), 1800))
    if style == "educational":
        body = f"""Hook: Have you ever wondered about {topic}?

Today, we will break down {topic} in a clear and practical way.

First, understand the basic idea. Start with the key facts and define any unfamiliar terms.

Next, consider a simple example related to {topic}. Explain what happens, why it matters, and what a viewer should remember.

A useful tip is to check reliable sources before acting on information about this topic. Details can change, so verify important claims.

Here is the takeaway: focus on the core idea, look for trustworthy evidence, and apply what you learned carefully.

If this was helpful, subscribe for more clear explanations."""
    elif style == "story":
        body = f"""Imagine discovering something surprising about {topic}.

At first, the situation seems ordinary. Then one small detail changes how everything looks.

As the story unfolds, the main challenge becomes clear. Each new clue gives us another way to understand what is happening.

The turning point is the moment we connect the details and see the bigger picture.

The lesson is simple: stay curious, ask questions, and look beyond the first impression.

What would you have done? Share your thoughts and subscribe for more stories."""
    else:
        body = f"""Here are three useful things to know about {topic}.

Number one: start with the basics. Understand what it is and why people care about it.

Number two: look for practical examples. Real examples make a topic easier to remember and apply.

Number three: verify the details. Use trustworthy sources, especially when information may change or affect important decisions.

The main takeaway is to keep learning, test what you can safely test, and avoid assuming every claim is true.

Follow for more useful videos about {topic}."""
    return body

def get_font(size):
    candidates = ["/system/fonts/Roboto-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    for f in candidates:
        if os.path.exists(f):
            try: return ImageFont.truetype(f, size)
            except: pass
    return ImageFont.load_default()

def make_thumbnail(out, title, vertical=False):
    size = (720, 1280) if vertical else (1280, 720)
    im = Image.new("RGB", size, (17, 24, 39))
    d = ImageDraw.Draw(im)
    # simple gradient bands for visual hierarchy
    w,h=size
    for y in range(h):
        t=y/max(1,h-1)
        d.line((0,y,w,y), fill=(int(20+25*t), int(30+10*t), int(55+35*t)))
    d.rounded_rectangle((int(w*.06),int(h*.12),int(w*.94),int(h*.88)), radius=28, outline=(80,180,255), width=5)
    words=textwrap.wrap(title.upper(), width=18 if vertical else 24)[:7]
    font=get_font(64 if vertical else 72)
    line_h=font.size+14 if hasattr(font,"size") else 80
    total=len(words)*line_h
    y=(h-total)//2
    for word in words:
        box=d.textbbox((0,0),word,font=font)
        x=(w-(box[2]-box[0]))//2
        d.text((x+3,y+3),word,font=font,fill=(0,0,0))
        d.text((x,y),word,font=font,fill=(255,255,255),stroke_width=1,stroke_fill=(10,10,10))
        y+=line_h
    im.save(out, quality=92)

@app.get("/health")
def health():
    return {"ok": True, "service": "PocketTube Studio API"}

@app.get("/", response_class=HTMLResponse)
def home():
    return (STATIC / "index.html").read_text(encoding="utf-8")

@app.get("/api/projects")
def list_projects():
    result=[]
    for p in sorted(PROJECTS.iterdir(), key=lambda x:x.stat().st_mtime, reverse=True):
        if p.is_dir():
            meta={}
            try: meta=json.loads((p/"project.json").read_text())
            except: pass
            result.append({"id":p.name, **meta, "files":[x.name for x in p.iterdir() if x.is_file()]})
    return result

@app.post("/api/projects")
def create_project(topic: str = Form(...), format: str = Form("shorts"), style: str = Form("list"), duration: int = Form(60)):
    pid=uuid.uuid4().hex[:10]
    p=PROJECTS/pid; p.mkdir(parents=True)
    (p/"assets").mkdir()
    meta={"topic":topic.strip()[:300],"format":format,"style":style,"duration":max(15,min(duration,1800)),
          "script":script_template(topic,style,duration),"title":topic.strip()[:100],"description":f"Learn more about {topic.strip()}.\n\n#YouTube",
          "created":__import__("datetime").datetime.now().isoformat(timespec="seconds")}
    (p/"project.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return {"id":pid,**meta}

@app.get("/api/projects/{pid}")
def get_project(pid:str):
    p=project_dir(pid)
    meta=json.loads((p/"project.json").read_text())
    meta["id"]=p.name
    meta["files"]=[x.name for x in p.iterdir() if x.is_file()]
    meta["assets"]=[x.name for x in (p/"assets").iterdir() if x.is_file()]
    return meta

@app.post("/api/projects/{pid}/script")
def save_script(pid:str, script:str=Form(...), title:str=Form(""), description:str=Form("")):
    p=project_dir(pid); meta=json.loads((p/"project.json").read_text())
    meta.update({"script":script[:30000],"title":title[:100],"description":description[:5000]})
    (p/"project.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    return {"ok":True}

@app.post("/api/projects/{pid}/assets")
async def upload_assets(pid:str, files:list[UploadFile]=File(...)):
    p=project_dir(pid); target=p/"assets"; saved=[]
    allowed={".jpg",".jpeg",".png",".webp",".mp4",".mov"}
    for f in files[:30]:
        ext=Path(f.filename or "").suffix.lower()
        if ext not in allowed: continue
        name=safe_id(Path(f.filename or "asset").stem) or "asset"
        dest=target/f"{uuid.uuid4().hex[:6]}_{name}{ext}"
        data=await f.read()
        if len(data)>100*1024*1024: continue
        dest.write_bytes(data); saved.append(dest.name)
    return {"saved":saved}

@app.post("/api/projects/{pid}/voice")
def voice(pid:str):
    p=project_dir(pid); meta=json.loads((p/"project.json").read_text())
    text=meta.get("script","")
    # Strip section labels to make narration less awkward
    text=re.sub(r"(?im)^(hook|intro|outro|voiceover|script):\s*","",text)
    txt=p/"voice.txt"; txt.write_text(text,encoding="utf-8")
    out=p/"voice.wav"
    run_cmd(["espeak-ng","-s","155","-v","en-us","-f",str(txt),"-w",str(out)])
    return {"ok":True,"file":"voice.wav"}

@app.post("/api/projects/{pid}/thumbnail")
def thumbnail(pid:str):
    p=project_dir(pid); meta=json.loads((p/"project.json").read_text())
    vertical=meta.get("format")=="shorts"
    make_thumbnail(p/"thumbnail.jpg",meta.get("title") or meta.get("topic") or "New video",vertical)
    return {"ok":True,"file":"thumbnail.jpg"}

@app.post("/api/projects/{pid}/render")
def render(pid:str):
    p=project_dir(pid); meta=json.loads((p/"project.json").read_text())
    assets=list((p/"assets").glob("*"))
    media=[a for a in assets if a.suffix.lower() in {".jpg",".jpeg",".png",".webp",".mp4",".mov"}]
    if not media: raise HTTPException(400,"Upload at least one image or video asset first.")
    voice=p/"voice.wav"
    if not voice.exists():
        raise HTTPException(400,"Create the voiceover first.")
    vertical=meta.get("format")=="shorts"
    w,h=(720,1280) if vertical else (1280,720)
    # For robust phone rendering, create one FFmpeg input per asset; image duration defaults to 5s.
    inputs=[]; filters=[]
    for i,a in enumerate(media[:20]):
        if a.suffix.lower() in {".mp4",".mov"}:
            inputs += ["-i",str(a)]
            filters.append(f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,trim=duration=5,setpts=PTS-STARTPTS[v{i}]")
        else:
            inputs += ["-loop","1","-t","5","-i",str(a)]
            filters.append(f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=25,trim=duration=5,setpts=PTS-STARTPTS[v{i}]")
    concat="".join(f"[v{i}]" for i in range(len(media[:20])))
    filters.append(f"{concat}concat=n={len(media[:20])}:v=1:a=0[vout]")
    # audio input index is after all media inputs
    inputs += ["-i",str(voice)]
    cmd=["ffmpeg","-y",*inputs,"-filter_complex",";".join(filters),"-map","[vout]","-map",f"{len(media[:20])}:a:0",
         "-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p","-c:a","aac","-shortest","-movflags","+faststart",str(p/"video.mp4")]
    run_cmd(cmd)
    return {"ok":True,"file":"video.mp4","note":"Rendered slideshow video. Review before publishing."}

@app.get("/api/projects/{pid}/file/{name}")
def get_file(pid:str,name:str):
    p=project_dir(pid); name=Path(name).name
    allowed={"video.mp4","voice.wav","thumbnail.jpg","voice.txt"}
    path=p/name
    if name not in allowed and not (p/"assets"/name).exists(): raise HTTPException(404,"File not found")
    if not path.exists(): path=p/"assets"/name
    if not path.exists(): raise HTTPException(404,"File not found")
    return FileResponse(path)

@app.get("/api/youtube/status")
def youtube_status():
    return {"configured":(ROOT/"client_secret.json").exists(),
            "dependencies":__import__("importlib").util.find_spec("googleapiclient") is not None}

@app.post("/api/projects/{pid}/youtube")
def youtube_upload(pid:str, privacy:str=Form("private")):
    p=project_dir(pid); video=p/"video.mp4"
    if not video.exists(): raise HTTPException(400,"Render the video first.")
    secret=ROOT/"client_secret.json"
    if not secret.exists(): raise HTTPException(400,"Add client_secret.json. See README.md for OAuth setup.")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.auth.transport.requests import Request
        import pickle
    except ImportError:
        raise HTTPException(500,"Install optional packages: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
    meta=json.loads((p/"project.json").read_text())
    token=p/"token.pickle"
    creds=None
    if token.exists():
        with open(token,"rb") as f: creds=pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
        else:
            flow=InstalledAppFlow.from_client_secrets_file(str(secret),["https://www.googleapis.com/auth/youtube.upload"])
            creds=flow.run_local_server(host="127.0.0.1",port=0,open_browser=True)
        with open(token,"wb") as f: pickle.dump(creds,f)
    youtube=build("youtube","v3",credentials=creds)
    body={"snippet":{"title":meta.get("title","New video")[:100],"description":meta.get("description","")[:5000],"categoryId":"22"},
          "status":{"privacyStatus":privacy if privacy in {"private","unlisted","public"} else "private"}}
    result=youtube.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(str(video),chunksize=-1,resumable=True)).execute()
    return {"ok":True,"videoId":result.get("id"),"url":"https://www.youtube.com/watch?v="+result.get("id","")}

@app.post("/api/ollama")
def ollama(topic:str=Form(...), style:str=Form("educational"), duration:int=Form(60)):
    import requests
    url=os.environ.get("OLLAMA_URL","http://127.0.0.1:11434").rstrip("/")
    model=os.environ.get("OLLAMA_MODEL","llama3.2")
    prompt=f"Write an original YouTube voiceover script about: {topic}. Style: {style}. Target duration: {duration} seconds. Do not invent facts. Output narration only."
    try:
        r=requests.post(url+"/api/generate",json={"model":model,"prompt":prompt,"stream":False},timeout=180)
        r.raise_for_status()
        return {"script":r.json().get("response","")}
    except Exception as e:
        raise HTTPException(502,f"Ollama unavailable: {e}. Use the built-in script generator instead.")
