import re, json, subprocess
from flask import Flask, request, Response

app = Flask(__name__)
FMT = "bv*[vcodec^=avc1][height<=720]+ba[ext=m4a]/b[ext=mp4]/b"

PAGE = """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<body style="font-family:sans-serif;background:#111;color:#eee;margin:8px">
<video id=v controls autoplay playsinline style="width:100%;background:#000"></video>
<form onsubmit="go(event)"><input id=q placeholder="search or paste link" style="width:70%;padding:8px">
<button style="padding:8px">Go</button></form><div id=r></div>
<script>
function play(id){v.src='/stream?v='+id;v.play()}
async function go(e){e.preventDefault();let q=document.getElementById('q').value;
let m=q.match(/(?:v=|youtu\\.be\\/|shorts\\/|live\\/)([\\w-]{11})/);
if(m||/^[\\w-]{11}$/.test(q)){play(m?m[1]:q);return}
r.innerHTML='searching...';
let d=await (await fetch('/search?q='+encodeURIComponent(q))).json();
r.innerHTML=d.map(x=>`<p onclick="play('${x.id}')" style="padding:8px;background:#222">${x.title}</p>`).join('')}
</script>"""

@app.route("/")
def index():
    return PAGE

@app.route("/search")
def search():
    q = request.args.get("q", "")
    out = subprocess.check_output(
        ["yt-dlp", "--flat-playlist", "-J", f"ytsearch10:{q}"])
    return Response(json.dumps(
        [{"id": e["id"], "title": e["title"]} for e in json.loads(out)["entries"]]),
        mimetype="application/json")

@app.route("/stream")
def stream():
    v = request.args.get("v", "")
    if not re.fullmatch(r"[\w-]{11}", v):
        return "bad id", 400
    urls = subprocess.check_output(
        ["yt-dlp", "-g", "-f", FMT, "https://youtu.be/" + v]).decode().split()
    cmd = ["ffmpeg", "-loglevel", "error"]
    for u in urls:
        cmd += ["-reconnect", "1", "-reconnect_streamed", "1", "-i", u]
    cmd += ["-c", "copy", "-f", "mp4",
            "-movflags", "frag_keyframe+empty_moov+default_base_moof", "pipe:1"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    def gen():
        try:
            while True:
                c = p.stdout.read(65536)
                if not c:
                    break
                yield c
        finally:
            p.kill()
    return Response(gen(), mimetype="video/mp4")

app.run(host="0.0.0.0", port=8080, threaded=True)
