from flask import Flask, render_template_string, request, redirect, url_for, flash
import csv
import os
import re
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecret'
CSV_FILE = 'exposed_urls.csv'

# --- API Key Regex Patterns ---
API_KEY_PATTERNS = [
    # OpenAI
    r'sk-[A-Za-z0-9\-]{20,}',
    r'sk-proj-[A-Za-z0-9\-]{20,}',
    r'sk-svcacct-[A-Za-z0-9\-]{20,}',
    r'sk-[A-Za-z0-9]{48}',
    r'Bearer sk-[A-Za-z0-9\-]{20,}',
    # Google/Gemini
    r'AIza[0-9A-Za-z\-_]{35,40}',
    # Anthropic
    r'sk-ant-api\\d{0,2}-[a-zA-Z0-9\\-_]{40,120}',
    r'sk-ant-[a-zA-Z0-9\\-_]{40,95}',
    r'sk-ant-v\\d+-[a-zA-Z0-9\\-_]{40,95}',
    r'sk-ant-[a-zA-Z0-9]+-[a-zA-Z0-9\\-_]{20,120}',
    r'sk-ant-[a-zA-Z0-9]{40,64}',
    r'\\bsk-ant-[a-zA-Z0-9\\-_]{20,120}\\b',
    # Cohere
    r'co-[a-zA-Z0-9]{32}',
    r'\\bco[a-zA-Z0-9]{38}\\b',
    # Mistral
    r'mis_[a-zA-Z0-9]{32,}',
    # DeepSeek
    r'sk-[a-zA-Z0-9]{32,48}',
    r'deepseek-[a-zA-Z0-9]{32,48}',
    # Perplexity
    r'pplx-[a-zA-Z0-9]{48,56}',
    r'pplx-[a-f0-9]{48}',
    # Replicate
    r'r8_[a-zA-Z0-9]{24,}',
    # ElevenLabs
    r'sk_[a-f0-9]{32}',
    r'xi-api-key:[a-f0-9]{32}',
    r'\\b[a-f0-9]{32}\\b',
    # HuggingFace
    r'hf_[a-zA-Z0-9]{34,}',
]

# --- GitHub Token (put your token here) ---
GITHUB_TOKEN = "ghp_xxx..."  # <-- Yahan apna token daal do

# --- CSV Storage ---
def init_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['url', 'found_at'])

def read_urls():
    urls = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                urls.append({'url': row['url'], 'found_at': row.get('found_at', '')})
    return sorted(urls, key=lambda x: x['found_at'], reverse=True)

def add_url(url):
    urls = [u['url'] for u in read_urls()]
    if url not in urls:
        with open(CSV_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([url, datetime.utcnow().isoformat()])
        return True
    return False

# --- GitHub Scanner ---
GITHUB_API = 'https://api.github.com'
TRENDING_REPOS = [
    'openai/openai-python',
    'google/gemini-api',
    'mistralai/mistral-src',
    'anthropics/anthropic-sdk',
    'huggingface/transformers',
    'cohere-ai/cohere-python',
    'deepseek-ai/DeepSeek-LLM',
    'perplexity-ai/pplx',
    'replicate/replicate',
    'elevenlabs/elevenlabs-python',
]

def get_github_file_content(owner, repo, path):
    url = f'{GITHUB_API}/repos/{owner}/{repo}/contents/{path}'
    headers = {'Accept': 'application/vnd.github.v3.raw'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.text
    return None

def get_github_repo_files(owner, repo):
    url = f'{GITHUB_API}/repos/{owner}/{repo}/git/trees/HEAD?recursive=1'
    headers = {}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        return [f['path'] for f in data.get('tree', []) if f['type'] == 'blob' and any(f['path'].endswith(ext) for ext in ['.py','.js','.ts','.env','.json','.yml','.yaml','.txt'])]
    return []

def scan_github_repos():
    found = 0
    for repo_full in TRENDING_REPOS:
        owner, repo = repo_full.split('/')
        files = get_github_repo_files(owner, repo)
        for file_path in files[:20]:
            content = get_github_file_content(owner, repo, file_path)
            if not content:
                continue
            for pattern in API_KEY_PATTERNS:
                for match in re.findall(pattern, content):
                    url = f'https://github.com/{owner}/{repo}/blob/HEAD/{file_path}'
                    if add_url(url):
                        found += 1
    return found

# --- Improved HTML Template ---
TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Exposed API Key Repos</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background: #f4f6fb; }
        .container { max-width: 700px; margin: 40px auto; background: #fff; border-radius: 10px; box-shadow: 0 2px 16px #0002; padding: 32px; }
        h1 { color: #222; margin-bottom: 16px; }
        form { display: flex; gap: 8px; margin-bottom: 24px; flex-wrap: wrap; }
        input[type=url] { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
        button { padding: 10px 18px; border: none; border-radius: 4px; background: #007bff; color: #fff; font-weight: bold; cursor: pointer; }
        button.scan-btn { background: #28a745; }
        button:hover { opacity: 0.9; }
        .flash { color: #28a745; margin-bottom: 10px; }
        .search-box { margin-bottom: 18px; }
        .search-box input { width: 100%; padding: 8px; border-radius: 4px; border: 1px solid #ccc; }
        ul { list-style: none; padding: 0; }
        li { background: #f9f9f9; margin-bottom: 8px; padding: 10px 12px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; }
        .url-link { word-break: break-all; color: #007bff; text-decoration: none; }
        .copy-btn { background: #eee; color: #333; border: none; border-radius: 4px; padding: 4px 10px; margin-left: 10px; cursor: pointer; }
        .copy-btn:hover { background: #ddd; }
        @media (max-width: 600px) {
            .container { padding: 12px; }
            form { flex-direction: column; gap: 6px; }
        }
    </style>
    <script>
        function filterUrls() {
            var input = document.getElementById('searchInput').value.toLowerCase();
            var items = document.querySelectorAll('.url-item');
            items.forEach(function(item) {
                var url = item.getAttribute('data-url').toLowerCase();
                item.style.display = url.includes(input) ? '' : 'none';
            });
        }
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text);
            alert('Copied to clipboard!');
        }
    </script>
</head>
<body>
    <div class="container">
        <h1>Exposed API Key Repos</h1>
        <form method="post" action="/add">
            <input type="url" name="url" placeholder="Paste repo URL..." required>
            <button type="submit">Add URL</button>
            <button type="submit" formaction="/scan" class="scan-btn">Scan Now</button>
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="flash">{{ messages[0] }}</div>
          {% endif %}
        {% endwith %}
        <div class="search-box">
            <input type="text" id="searchInput" onkeyup="filterUrls()" placeholder="Search URLs...">
        </div>
        <ul>
            {% for item in urls %}
                <li class="url-item" data-url="{{ item.url }}">
                    <a class="url-link" href="{{ item.url }}" target="_blank">{{ item.url }}</a>
                    <span>
                        <small>{{ item.found_at[:19].replace('T',' ') }}</small>
                        <button class="copy-btn" onclick="copyToClipboard('{{ item.url }}');return false;">Copy</button>
                    </span>
                </li>
            {% else %}
                <li>No URLs stored yet.</li>
            {% endfor %}
        </ul>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    urls = read_urls()
    return render_template_string(TEMPLATE, urls=urls)

@app.route('/add', methods=['POST'])
def add():
    url = request.form.get('url')
    if url:
        if add_url(url):
            flash('URL added!')
        else:
            flash('URL already exists.')
    return redirect(url_for('index'))

@app.route('/scan', methods=['POST'])
def scan():
    found = scan_github_repos()
    if found:
        flash(f'Scan complete! {found} new exposed URLs found.')
    else:
        flash('Scan complete! No new exposed URLs found.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_csv()
    app.run(debug=True)