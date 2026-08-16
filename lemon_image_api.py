"""Single-port Lemon Image API with a unified provider dashboard."""

import uvicorn
from fastapi.responses import HTMLResponse

import api_server as _api


app = _api.app
app.title = "Lemon Image API"

# Replace the inherited single-provider landing page with the one-port dashboard.
app.router.routes = [route for route in app.router.routes if getattr(route, "path", None) != "/"]

DASHBOARD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lemon Image API</title><style>
body{margin:0;min-height:100vh;display:grid;place-items:center;background:#111827;color:#f9fafb;font:16px system-ui,sans-serif;padding:24px}
main{width:min(720px,100%);background:#1f2937;border:1px solid #374151;border-radius:20px;padding:32px;box-sizing:border-box;box-shadow:0 20px 50px #0008}
h1{margin:0 0 6px;color:#fde047}.sub{color:#9ca3af;margin:0 0 26px}label{display:block;margin:15px 0 7px;font-weight:600}select,textarea,button{width:100%;box-sizing:border-box;border-radius:10px;font:inherit}select,textarea{border:1px solid #4b5563;background:#111827;color:#fff;padding:12px}textarea{height:120px;resize:vertical}button{margin-top:20px;border:0;background:#eab308;color:#111827;font-weight:800;padding:13px;cursor:pointer}button:disabled{opacity:.6}.note{font-size:13px;color:#9ca3af;margin-top:16px}.result{margin-top:24px;min-height:80px;display:grid;gap:12px}.result img{max-width:100%;border-radius:12px}.error{color:#fca5a5}</style></head>
<body><main><h1>🍋 Lemon Image API</h1><p class="sub">One local endpoint. Choose any available image provider.</p>
<label for="model">Provider / model</label><select id="model"><option value="freegen">FreeGen</option><option value="ezmaker">EzMaker AI</option><option value="zimage">ZImage</option><option value="redpanda">RedPanda</option><option value="bing">Bing Image Creator</option></select>
<label for="prompt">Prompt</label><textarea id="prompt" placeholder="Describe the image you want to generate..."></textarea>
<button id="generate">Generate image</button><p class="note">API: <code>POST /v1/images/generations</code> · Models: <code>GET /v1/models</code> · Bing requires Microsoft sign-in.</p><div class="result" id="result"></div>
</main><script>
const button=document.querySelector('#generate'),result=document.querySelector('#result');
button.onclick=async()=>{const prompt=document.querySelector('#prompt').value.trim(),model=document.querySelector('#model').value;if(!prompt){result.innerHTML='<span class="error">Enter a prompt first.</span>';return}button.disabled=true;button.textContent='Generating…';result.textContent='Your request is being sent to '+model+'…';try{const response=await fetch('/v1/images/generations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model,prompt,size:'512x512',n:1})}),data=await response.json();if(!response.ok)throw Error(data.detail||'Generation failed');result.innerHTML=data.data.map(x=>'<img alt="Generated image" src="data:image/png;base64,'+x.b64_json+'">').join('')}catch(error){result.innerHTML='<span class="error">'+error.message+'</span>'}finally{button.disabled=false;button.textContent='Generate image'}};
</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return DASHBOARD


if __name__ == "__main__":
    _api.logger.info("Starting Lemon Image API (all providers) on %s:%s", _api.HOST, _api.PORT)
    uvicorn.run(app, host=_api.HOST, port=_api.PORT)
