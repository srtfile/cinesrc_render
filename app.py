import json
import requests
import hashlib
import base64
import os
from flask import Flask, render_template_string, request, jsonify

app = Flask(__name__)

HEADERS = {
    "Origin": "https://cinesrc.st",
    "Referer": "https://cinesrc.st/",
    "Content-Type": "text/plain;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.37 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.37"
}

API = "https://enc-dec.app/api"

HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CineSrc Extractor</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', sans-serif; background: #0f0f1a; color: #e0e0e0; min-height: 100vh; padding: 20px; }
  .container { max-width: 900px; margin: 0 auto; }
  h1 { text-align: center; color: #9c27b0; margin-bottom: 8px; font-size: 2rem; }
  .subtitle { text-align: center; color: #888; margin-bottom: 30px; font-size: 0.9rem; }
  .card { background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
  label { display: block; margin-bottom: 6px; color: #aaa; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; }
  input, select { width: 100%; padding: 10px 14px; background: #0f0f1a; border: 1px solid #3a3a5a; border-radius: 8px; color: #e0e0e0; font-size: 0.95rem; margin-bottom: 16px; outline: none; }
  input:focus, select:focus { border-color: #9c27b0; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .row3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
  button { width: 100%; padding: 12px; background: #9c27b0; color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; transition: background 0.2s; }
  button:hover { background: #7b1fa2; }
  button:disabled { background: #444; cursor: not-allowed; }
  .output { background: #0a0a15; border: 1px solid #2a2a4a; border-radius: 8px; padding: 16px; min-height: 120px; font-family: monospace; font-size: 0.85rem; white-space: pre-wrap; word-break: break-all; color: #a0f0a0; }
  .step { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #2a2a4a; color: #888; font-size: 0.85rem; }
  .step:last-child { border-bottom: none; }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #444; flex-shrink: 0; }
  .step.done .dot { background: #4caf50; }
  .step.active .dot { background: #9c27b0; animation: pulse 1s infinite; }
  .step.error .dot { background: #f44336; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; background: #2a2a4a; color: #9c27b0; margin-left: 8px; }
  .error-msg { color: #f44336; }
  .warn { color: #ff9800; font-size: 0.8rem; padding: 8px 12px; background: rgba(255,152,0,0.1); border-radius: 6px; margin-bottom: 16px; border-left: 3px solid #ff9800; }
</style>
</head>
<body>
<div class="container">
  <h1>🎥 CineSrc</h1>
  <p class="subtitle">Extract decrypted stream data from cinesrc.st</p>
  <div class="card">
    <div class="warn">⚠️ CineSrc requires challenge solving. The solve_stage1 implementation must be available via the enc-dec API. If it fails, try a different provider index.</div>
    <div class="row">
      <div>
        <label>Type</label>
        <select id="type">
          <option value="tv">TV Show</option>
          <option value="movie">Movie</option>
        </select>
      </div>
      <div>
        <label>IMDB ID</label>
        <input type="text" id="imdb_id" value="tt0944947" placeholder="tt0944947">
      </div>
    </div>
    <div class="row3">
      <div>
        <label>TMDB ID</label>
        <input type="text" id="tmdb_id" value="1399" placeholder="1399">
      </div>
      <div>
        <label>Season</label>
        <input type="text" id="season" value="1">
      </div>
      <div>
        <label>Episode</label>
        <input type="text" id="episode" value="1">
      </div>
    </div>
    <div class="row">
      <div>
        <label>Provider Index</label>
        <input type="number" id="provider_idx" value="1" min="0" max="10">
      </div>
    </div>
    <button id="runBtn" onclick="run()">▶ Extract Stream Data</button>
  </div>
  <div class="card">
    <label>Progress</label>
    <div id="steps">
      <div class="step" id="s1"><div class="dot"></div> Bootstrap Cookies</div>
      <div class="step" id="s2"><div class="dot"></div> Solve PoW Challenges</div>
      <div class="step" id="s3"><div class="dot"></div> Get Encrypted Token</div>
      <div class="step" id="s4"><div class="dot"></div> Get Providers List</div>
      <div class="step" id="s5"><div class="dot"></div> Decrypt Stream Data</div>
    </div>
  </div>
  <div class="card">
    <label>Output <span class="badge" id="badge"></span></label>
    <div class="output" id="output">Results will appear here...</div>
  </div>
</div>
<script>
async function run() {
  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  document.getElementById('output').textContent = 'Running... (CineSrc can take 30-60s due to PoW solving)';
  document.getElementById('badge').textContent = '';
  ['s1','s2','s3','s4','s5'].forEach(id => document.getElementById(id).className = 'step');
  try {
    const resp = await fetch('/run', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({
        type: document.getElementById('type').value,
        imdb_id: document.getElementById('imdb_id').value,
        tmdb_id: document.getElementById('tmdb_id').value,
        season: document.getElementById('season').value,
        episode: document.getElementById('episode').value,
        provider_idx: parseInt(document.getElementById('provider_idx').value),
      })
    });
    const data = await resp.json();
    data.steps.forEach((s,i) => document.getElementById('s'+(i+1)).classList.add(s.status));
    if (data.error) {
      document.getElementById('output').innerHTML = '<span class="error-msg">ERROR: ' + data.error + '</span>';
      document.getElementById('badge').textContent = 'FAILED';
    } else {
      document.getElementById('output').textContent = JSON.stringify(data.result, null, 2);
      document.getElementById('badge').textContent = 'SUCCESS';
    }
  } catch(e) {
    document.getElementById('output').innerHTML = '<span class="error-msg">' + e.message + '</span>';
  }
  btn.disabled = false;
}
</script>
</body>
</html>'''

def solve_stage2(data):
    target = data["pack"][0][::-1]
    salt = data["pack"][3][::-1]
    r = data["pack"][4][::-1]
    decode = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()
    body = decode(r.split(".")[1])
    payload = decode(body.split(".", 1)[1])
    difficulty = json.loads(payload)["d"]
    width = (difficulty + 3) // 4
    for counter in range(1 << difficulty):
        key = format(counter, "x").zfill(width)
        digest = hashlib.sha256((salt + key).encode()).hexdigest()
        if digest == target:
            return key
    raise RuntimeError("no solution found")

def get_cookie(content_type, tmdb_id, season, episode):
    fields = [content_type, tmdb_id, season, episode]
    encoded = base64.urlsafe_b64encode(json.dumps(fields, separators=(",", ":")).encode()).decode().rstrip("=")
    headers = {**HEADERS, "x-cs-q": encoded}
    bootstrap = requests.post("https://cinesrc.st/api/c/bootstrap", headers=headers, timeout=15).json()
    return {"x-cs-q": encoded, "x-cs-r": bootstrap["r"], "x-cs-p": bootstrap["p"]}

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/run', methods=['POST'])
def run():
    data = request.json
    content_type = data.get('type', 'tv')
    imdb_id = data.get('imdb_id', '')
    tmdb_id = data.get('tmdb_id', '')
    season = data.get('season', '1')
    episode = data.get('episode', '1')
    provider_idx = data.get('provider_idx', 1)
    steps = [{"status": "active"}, {"status": ""}, {"status": ""}, {"status": ""}, {"status": ""}]

    url = f"https://cinesrc.st/embed/tv/{imdb_id}?s={season}&e={episode}" if content_type == "tv" else f"https://cinesrc.st/embed/movie/{imdb_id}"

    try:
        # Step 1: Bootstrap
        cookies = get_cookie(content_type, tmdb_id, season, episode)
        steps[0]["status"] = "done"

        # Step 2: PoW
        steps[1]["status"] = "active"
        h = {**HEADERS, **cookies}
        challenge1 = requests.get("https://cinesrc.st/api/c/issue", headers=h, timeout=15).json()
        enc_cinesrc = f"{API}/enc-cinesrc-stage1"
        s1_resp = requests.post(enc_cinesrc, json={"challenge": challenge1}, timeout=30).json()
        if s1_resp.get("status") != 200:
            steps[1]["status"] = "error"
            return jsonify({"steps": steps, "error": f"Stage1 solve failed: {s1_resp.get('error','unknown')}"})
        stage1_sol = s1_resp["result"]

        challenge2 = requests.get("https://cinesrc.st/api/c/stage2/issue", headers=h, timeout=15).json()
        stage2_sol = solve_stage2(challenge2)
        challenge_data = {
            "stage1": {"challenge": challenge1, "solution": stage1_sol},
            "stage2": {"challenge": challenge2, "solution": stage2_sol}
        }
        steps[1]["status"] = "done"

        # Step 3: Encrypted token
        steps[2]["status"] = "active"
        enc_payload = {"url": url, "agent": HEADERS["User-Agent"], "challenge_data": challenge_data}
        token_resp = requests.post(f"{API}/enc-cinesrc", json=enc_payload, timeout=30).json()
        if token_resp.get("status") != 200:
            steps[2]["status"] = "error"
            return jsonify({"steps": steps, "error": token_resp.get("error", "Token fetch failed")})
        token_data = token_resp["result"]
        token = f"{token_data['token']}::c3::{cookies['x-cs-r']}"
        key = token_data["key"]
        h2 = token_data["headers"]
        steps[2]["status"] = "done"

        # Step 4: Get providers
        steps[3]["status"] = "active"
        ph = {**HEADERS, "Next-Action": h2["getProviderList"]}
        providers_text = requests.post(url, headers=ph, data=json.dumps([]), timeout=15).text
        line = providers_text.splitlines()[1].split(":", 1)[1]
        providers = json.loads(line)
        provider = providers[provider_idx]["id"]
        steps[3]["status"] = "done"

        # Step 5: Get stream
        steps[4]["status"] = "active"
        sh = {**HEADERS, "Next-Action": h2["getStream"]}
        payload = [tmdb_id, "show" if content_type == "tv" else content_type,
                   season if content_type == "tv" else "$undefined",
                   episode if content_type == "tv" else "$undefined", token, provider]
        stream_resp = requests.post(url, headers=sh, data=json.dumps(payload), timeout=15)
        if stream_resp.status_code != 200:
            steps[4]["status"] = "error"
            return jsonify({"steps": steps, "error": f"Provider {provider} returned {stream_resp.status_code}. Try another provider index."})
        streams_text = stream_resp.text
        line = streams_text.splitlines()[1]
        encrypted = line.split(",", 1)[1].split(":", 1)[0]
        dec_resp = requests.post(f"{API}/dec-cinesrc", json={"text": encrypted, "key": key}, timeout=15).json()
        if dec_resp.get("status") != 200:
            steps[4]["status"] = "error"
            return jsonify({"steps": steps, "error": dec_resp.get("error", "Decryption failed")})
        decrypted = dec_resp["result"]
        steps[4]["status"] = "done"

        return jsonify({"steps": steps, "result": decrypted})
    except Exception as e:
        for s in steps:
            if s["status"] == "active":
                s["status"] = "error"
        return jsonify({"steps": steps, "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
