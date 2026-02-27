---
title: Commvault Backup & Recovery Real Exploit
course: Programming 2
---

Argument injection is a vulnerability class where user-supplied input is unsafely incorporated into command-line arguments. When a web endpoint forwards such input directly to internal commands without proper validation, an attacker can inject additional switches or parameters, altering the program's behavior. This lesson highlights why interfaces that accept user data must enforce strict boundaries between data and control flow to prevent legitimate features from being weaponized.

## About the Product

Commvault Backup & Recovery is a comprehensive on-premises data protection solution used by many organizations to safeguard critical data. It coordinates backup, replication, recovery, and disaster recovery workflows across endpoints and data centers. The product exposes management interfaces for administrators to configure backup policies, monitor job status, and orchestrate large-scale data protection operations.

Core services authenticate users, coordinate tasks, and expose web-based controls for operators to manage protected resources. In production deployments, these interfaces often reside in the exposed management layer and have privileged access to encryption keys, backup repositories, and repository-level metadata.

## The Intended Behavior

The endpoint is expected to provide secure, authenticated access to high-privilege management functions. Under normal conditions, it should sanitize and validate all user inputs, preventing the introduction of stray argument delimiters or unexpected switches.

The pathway to perform authentication and orchestration should rely on clearly defined APIs that treat user data as data, not as part of a shell or command string. The system should ensure that arguments cannot be injected or misinterpreted as control commands, and that backend processes receive strictly parsed and safe parameters. In short, the web interface should function as a trusted boundary, translating user actions into discrete, safe operations rather than concatenating arbitrary strings into shell commands.

## The Vulnerability

The vulnerability stems from a design flaw in how the /commandcenter/restservlet/ endpoint processes inputs, failing to neutralize or strictly validate command-line argument delimiters in user-controlled data.

User input is included directly in the argument string for backend processes (notably the QLogin command) without proper escaping or delimiting, which allows an attacker to inject additional arguments and alter parameter boundaries.

This can enable unauthorized actions or privilege escalation through downstream processes.

```pseudo title="Vulnerable /commandcenter/restservlet/"
# Pseudocode illustrating insecure argument propagation
endpoint_input = get_request_param('username')  # attacker-controlled input
constructed_args = "QLogin " + endpoint_input + " " + get_request_param('password')
# The backend passes constructed_args to QLogin without escaping or validation
execute_backend_command(constructed_args)
```

## Mitigation

Upgrade to patched Commvault versions 11.36.60 (main), 11.32.102, or 11.38.32, which implement robust input validation and strict delimitation of command-line arguments. The patch strategy typically involves neutralizing dangerous delimiters, enforcing strong input schemas, and replacing direct string construction with safer invocation mechanisms that separate data from command structure.

In addition to code fixes, organizational and network controls remain important: restrict management-interface access to trusted networks, monitor for anomalous authentication attempts and command activity, and deploy web application firewalls and detection signatures to recognize exploitation patterns. Keeping detection and protection tools up-to-date with the latest signatures is a complementary defense to the patch, reducing the likelihood that attackers can operationalize the vulnerability in new environments.

```pseudo title="Secure /commandcenter/restservlet/"
# Secure handling with input validation and safe invocation
user_input = get_request_param('username')
safe_input = sanitize_and_validate(user_input)  # remove dangerous delimiters, enforce schema
password_input = get_request_param('password')
safe_password = sanitize_and_validate(password_input)
# Do not construct a shell command from user input
invoke_backend_api('QLogin', {'user': safe_input, 'pass': safe_password})
# Or, if a shell must be avoided, use parameterized calls or internal APIs
```

---

---
title: Argument Injection Lesson
---

Building on earlier work on validating inputs, sanitizing data, and using safe interfaces when software interacts with the operating system, this lesson shows how untrusted input can influence command-level interactions when a web layer talks to backend tools.

This lesson introduces Argument Injection (CWE-88) and fits into the course topic of secure interaction with the operating system and external tools, emphasizing safe parameter passing and least-privilege design.

The course concept overview: When software constructs commands or passes data to system tools, inputs must be treated as data, not as code or command fragments. Validate inputs against allowlists, avoid composing commands with user data, and invoke tools via safe APIs or argument arrays. Avoid shell-based command construction to prevent unintended interpretation of inputs.

## Introduction to the vulnerable program

DataGuard Admin Portal is a fictional but realistic web-based portal used by a small IT team on an internal network. Its purpose is to start backup jobs, view status, and manage credentials for the DataGuard backup system. The portal exposes a REST endpoint that accepts small sets of user inputs — for example a username and a requested operation — and then relies on a local helper tool to perform authentication and orchestration tasks. The intended flow is that a portal user provides a legitimate username and a supported operation (such as start, status, or cancel), and the helper tool carries out the actual work with the correct privileges.

However, a security mistake occurs at the web layer: the endpoint constructs a single shell command by directly concatenating user-provided inputs into the command line string and then invokes the helper tool. There is no strict input validation or argument binding at the web layer, and the system does not neutralize special characters like quotes, spaces, or dash-prefixed flags. In short, the application treats user data as if it were plain text to append to a command, rather than as distinct, validated arguments to a program. This simple oversight enables argument injection and creates a path for attackers to influence the backend.

```python
# Vulnerable example: naive command construction from user input
import os

def handle_request(request):
    username = request.get("username")
    operation = request.get("operation")

    # Naive, unsafe command assembly
    cmd = "backup_helper --user " + username + " --operation " + operation
    os.system(cmd)
```

## Exploring an exploit against the vulnerable program

An attacker's goal is to cause the helper tool to interpret injected arguments as if they were part of the original command. By inserting special characters and additional flags into the username or operation fields, the attacker can alter the execution path, override defaults, or request the backend to create authenticated sessions that the attacker controls. In practice, the exploit leverages the lack of input validation and the use of a shell interpreter to run an injected command string. The rest endpoint remains the same, but the resulting shell invocation may interpret injected tokens as new options or even execute additional commands—potentially compromising the system's integrity and the confidentiality of credentials.

```python
# Exploit example: crafted payload to inject additional arguments
import requests

# Craft input that breaks out of the intended command and adds new flags
payload = {
    "username": "regular_user; --admin --session=evil_session",
    "operation": "start"
}
response = requests.post("http://dataguard.local/start_backup", json=payload)
print(response.status_code, response.text)
```

## Patching the program to prevent the exploit

The secure design change centers on separating user input from the command invocation and treating inputs as data, not as command components. The fixes involve validating inputs against a defined allowlist, using a safe invocation mechanism that does not concatenate user input into a shell command, and employing an argument list that the underlying runtime can pass as discrete parameters. Additionally, enforcing least privilege on the portal and the helper tool minimizes the potential impact if an injection were attempted. Practically, this means never calling a shell with a string constructed from user input; instead, call the tool with a structured argument array, and validate input before it ever reaches the invocation layer.

```python
import subprocess
import re

def safe_handle_request(request):
    username = request.get("username", "")
    operation = request.get("operation", "")

    # Validation: allow only known, safe characters for username and a small set of operations
    if not re.match(r"^[a-zA-Z0-9_.-]+$", username):
        raise ValueError("invalid username")
    allowed_ops = {"start", "status", "cancel", "stop"}
    if operation not in allowed_ops:
        raise ValueError("invalid operation")

    # Use an argument list to avoid shell interpretation
    cmd = ["backup_helper", "--user", username, "--operation", operation]
    subprocess.run(cmd, check=True)
```

This patched version eliminates the vulnerability by removing shell interpretation from the critical path, enforcing a strict input policy, and using a safe, explicit argument passing style. It also reinforces the principle of least privilege: the portal should operate with only the privileges necessary to perform backup-related tasks, reducing the risk if an attacker can influence the invoked arguments. In practice, you validate inputs, constrain the allowed values, and rely on programmatic interfaces that treat user data as data, not as commands to be executed.

---

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
