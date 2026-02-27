---
title: Argument Injection Practice
---

This practice connects to the lesson by illustrating how untrusted input can influence shell commands through parametric construction. You will study the PhotoArchive Local Server, observe the vulnerability, attempt an injection, and then apply a safe design patch that stops constructing shell commands from user input and instead passes arguments in a structured, safe way.

## Getting Started

This exercise uses Python and Flask to simulate a vulnerable API alongside a local exploit client. You will run both the server and the exploit client on your machine to observe how vulnerability manifests and how a patch can mitigate it. The server maintains data in memory for simplicity, while the exploit client interacts with the server by sending crafted HTTP requests.

### Virtual Environment

A virtual environment creates an isolated Python workspace where you can install and manage packages without affecting anything else on your system. It is not required for this practice, but it is strongly recommended because it gives you a clean and consistent setup. Using a virtual environment helps avoid conflicts and makes it easier to remove or reset dependencies later. You may continue without one, but adopting virtual environments early is a valuable habit.

```title="Create a Virtual Environment"
python -m venv .venv
```

```title="Activate the Virtual Environment"
# On Windows
.\venv\Scripts\activate

# On MacOS or Linux
source .venv/bin/activate
```

```title="Deactivate the Virtual Environment"
deactivate
```

### Install Requirements

The exercise relies on Flask for the API and requests for the client.

```bash title="Install Requirements"
pip install flask requests
```

## Scenario Overview

The PhotoArchive Local Server is a tiny, in-memory API that exposes a basic administrative route for managing photo collections and access tokens. A backend helper uses a shell-like command string constructed from user inputs to perform authentication and initialize a session. The vulnerability lives in the server blindly concatenating user-provided fields into a single command line that is then executed by a local process. This setup is intentionally simple and runs entirely on the learner's machine, making it ideal for safely exploring how an attacker could influence backend behavior through crafted input. The exploit client, exploit_client.py, interacts with the vulnerable endpoint by sending HTTP requests that attempt to embed additional switches or delimiters in the input fields to simulate argument injection against a local API.

### Target Program

The Target Program is the PhotoArchive Local Server. Its purpose is to provide an administrative route to manage photo collections and tokens. The vulnerable behavior is the construction and execution of a shell-like command that includes user-supplied fields, which can be manipulated by an attacker to run unintended commands.

```python title="target.py"
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

# In-memory data store (simple and illustrative)
photos = {
    'collections': {'vacation': []},
    'tokens': {}
}

# Vulnerable helper: executes a shell command built from input

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), -1

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json or {}
    user = data.get('user', '')
    action = data.get('action', '')
    token = data.get('token', '')

    # Vulnerable: directly concatenating user input into a shell command
    cmd = f"auth --user {user} --action {action} --token {token}"
    out, code = run_command(cmd)

    if code == 0:
        return jsonify({'status': 'success', 'out': out}), 200
    else:
        return jsonify({'status': 'failure', 'out': out}), 401

if __name__ == '__main__':
    app.run(port=5000)
```

### Exploit Program

The Exploit Program demonstrates how an attacker could interact with the vulnerable endpoint to probe and potentially misuse the command execution. The exploit client sends a normal login-like request first to observe the server's baseline behavior, then injects extra command-line arguments by including a semicolon-delimited payload in the token field. This simulates an attacker-controlled input attempting to influence the shell execution.

```python title="exploit.py"
import requests

url = 'http://localhost:5000/admin/login'

# Normal request first (observe baseline)
payload_normal = {
    'user': 'admin',
    'action': 'login',
    'token': 'TOKEN123'
}
resp = requests.post(url, json=payload_normal)
print('Normal request status:', resp.status_code)
print(resp.json())

# Injection attempt (observe vulnerability)
payload_inject = {
    'user': 'admin',
    'action': 'login',
    'token': 'TOKEN123; whoami'  # injection payload
}
resp = requests.post(url, json=payload_inject)
print('Injection attempt status:', resp.status_code)
print(resp.json())
```

## Practice Objectives

### Task 1: Observe the vulnerable behavior

Send a normal login-like request to the vulnerable endpoint and observe the server's response. Note whether the response indicates a successful operation and whether any extra information appears in the output. This establishes the baseline behavior before any exploitation.

```python
import requests

url = 'http://localhost:5000/admin/login'
payload = {
    'user': 'admin',
    'action': 'login',
    'token': 'TOKEN123'
}
resp = requests.post(url, json=payload)
print('Status:', resp.status_code)
print(resp.json())
```

### Task 2: Trigger the vulnerability

Construct a request in which an input field embeds additional command-line arguments or delimiters. For example, append a semicolon and a simple command to the token field (e.g., TOKEN123; whoami). Observe how the server's response changes and whether any unintended information is exposed or additional commands appear to have executed.

```python
import requests

url = 'http://localhost:5000/admin/login'
payload_inject = {
    'user': 'admin',
    'action': 'login',
    'token': 'TOKEN123; whoami'  # injection payload
}
resp = requests.post(url, json=payload_inject)
print('Status:', resp.status_code)
print(resp.json())
```

### Task 3: Patch Task — Implement a safe design

Patch the target program so that it no longer builds a shell command from user input. Instead, pass arguments to the backend executable as a structured list, or validate and sanitize inputs to remove dangerous delimiters. The patch should preserve normal functionality but prevent arbitrary command execution.

``` python title="target.py (patched)"
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

photos = {'collections': {'vacation': []}, 'tokens': {}}

# Safe command execution: pass arguments as a list (no shell)

def run_command_safe(args):
    try:
        result = subprocess.run(args, capture_output=True, text=True)
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), -1

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json or {}
    user = data.get('user', '')
    action = data.get('action', '')
    token = data.get('token', '')

    # Validate inputs to remove dangerous characters
    safe_token = str(token).replace(';', '').replace('&', '').strip()
    safe_user = str(user).replace(';', '').replace('&', '').strip()
    safe_action = str(action).replace(';', '').replace('&', '').strip()

    # Build command safely without shell and with explicit arguments
    cmd_args = ['auth', '--user', safe_user, '--action', safe_action, '--token', safe_token]
    out, code = run_command_safe(cmd_args)

    if code == 0:
        return jsonify({'status': 'success', 'out': out}), 200
    else:
        return jsonify({'status': 'failure', 'out': out}), 401

if __name__ == '__main__':
    app.run(port=5000)
```

### Task 4: Patch Task — Verify the patch

Re-run the exploit tasks from Task 2 and confirm that the injection is ignored and no elevated or unintended behavior occurs, while normal operations continue to function as expected. This verification demonstrates that the patch prevents argument injection while preserving legitimate use cases.

```bash
# Verification steps (example)
# 1) Start the patched server
python target.py

# 2) Run Task 1 code to observe baseline
python - <<'PY'
import requests
url = 'http://localhost:5000/admin/login'
payload = {'user': 'admin', 'action': 'login', 'token': 'TOKEN123'}
resp = requests.post(url, json=payload)
print(resp.status_code, resp.json())
PY

# 3) Run Task 2 code with injection and ensure no injection occurs
python - <<'PY'
import requests
url = 'http://localhost:5000/admin/login'
payload_inject = {'user': 'admin', 'action': 'login', 'token': 'TOKEN123; whoami'}
resp = requests.post(url, json=payload_inject)
print(resp.status_code, resp.json())
PY
```
