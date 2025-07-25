from flask import Flask, render_template_string, request, redirect, url_for, flash
import csv
import os
import re
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecret'
CSV_FILE = 'exposed_urls.csv'

API_KEY_PATTERNS = [
    # ... (same as above) ...
]

# --- No token here ---
GITHUB_TOKEN = ""  # Blank

GITHUB_API = 'https://api.github.com'
TRENDING_REPOS = [
    # ... (same as above) ...
]

def get_github_file_content(owner, repo, path):
    url = f'{GITHUB_API}/repos/{owner}/{repo}/contents/{path}'
    headers = {'Accept': 'application/vnd.github.v3.raw'}
    # No token header
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.text
    return None

def get_github_repo_files(owner, repo):
    url = f'{GITHUB_API}/repos/{owner}/{repo}/git/trees/HEAD?recursive=1'
    headers = {}
    # No token header
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = r.json()
        return [f['path'] for f in data.get('tree', []) if f['type'] == 'blob' and any(f['path'].endswith(ext) for ext in ['.py','.js','.ts','.env','.json','.yml','.yaml','.txt'])]
    return []

# ...rest of the code (UI, scan, add, etc.) bilkul same as above...
