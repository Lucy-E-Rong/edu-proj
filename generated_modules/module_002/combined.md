---
title: n8n Real Exploit
course: Software Engineering
---

The security concept introduced here is the danger of allowing user-provided code to run in a live automation system without watertight isolation. When a system evaluates arbitrary expressions supplied by users, the boundary between safe evaluation and full access to the host must be clearly enforced. If that boundary is porous, attackers can escape the sandbox and execute commands on the host, leading to remote code execution (RCE) and control over the automation environment.

## About the Product

n8n is an open-source workflow automation platform that enables users to model and orchestrate business processes by connecting services, transforming data, and automating tasks through visual workflows and code expressions. Users compose nodes that perform actions, fetch data, and route information, creating end-to-end automations across cloud services, on-premises systems, and custom APIs. The platform emphasizes flexibility, allowing dynamic logic through embedded JavaScript expressions wrapped in double curly braces {{ }} that are evaluated during workflow execution.

The product is designed to run in diverse environments, including self-hosted deployments and cloud-based instances. It exposes a browser-based workflow editor for creating and editing automations, REST API endpoints for programmatic workflow management, and a sandboxed environment intended to securely evaluate user-provided expressions. In multi-tenant or collaborative deployments, the ability for diverse users to freely compose logic amplifies the importance of strong isolation between the safe evaluation context and the host runtime.

## The Intended Behavior

Under normal operation, the workflow engine accepts user-defined JavaScript expressions embedded in the workflow, evaluates them within a restricted sandbox, and returns computed results or transforms runtime data. The evaluation context is meant to expose only a limited set of workflow variables (such as node outputs, input payloads, and whitelisted utility methods) while blocking access to privileged APIs, the Node.js global object, the require function, and system-level modules. The overarching goal is to enable powerful, user-driven automation without granting access to the host operating system or sensitive capabilities.

This separation depends on a secure evaluation engine that interprets the expressions with strict boundaries. The sandbox should prevent a user from escaping to the host or obtaining credentials, secrets, or network access beyond what the workflow itself is intended to manage. In practice, this means that only a carefully curated surface area of the runtime is visible to the expression, and any attempt to reach beyond that surface should be blocked or sanitized.

## The Vulnerability

The vulnerability arises when the isolation between the user-provided expression and the host runtime is incomplete. A critical flaw allowed an authenticated user to escape the intended safe context by leveraging the value of this inside an expression. Instead of resolving to a benign, empty object, this could resolve to the Node.js global context, enabling access to dangerous capabilities such as requiring modules from the host environment.

As a result, an attacker could inject crafted expressions in a workflow, for example by using the expression syntax {{ ... }}, to access system-level modules and execute operating-system commands. The sandbox failed to effectively constrain access to the Node.js runtime, breaking the core security boundary and enabling remote code execution with the privileges of the automation server process. This kind of flaw is categorized under improper control of dynamically managed code resources.

The breakdown point was that the system evaluated embedded instructions without sufficiently stripping or neutralizing privileged references, effectively turning the host runtime into a playground for attacker-controlled code.

```js title="Vulnerable src/workflow/evaluator.js"
{{ require('child_process').execSync('id') }}
```

## Mitigation

The complete resolution involves upgrading to patched software releases where the expression evaluation engine enforces a strict, attacker-resistant boundary. The patch replaces the unsafe evaluation path with a sanitized execution model that neutralizes dangerous references, particularly the this keyword and any attempt to access privileged modules. By introducing a sanitizer or restricted execution context, the evaluator ensures that evaluating user-supplied code cannot resolve this to a privileged or unsafe context, effectively preventing code execution on the host.

In environments where immediate upgrade is not feasible, several defensive measures help reduce risk: restrict workflow creation and editing permissions to highly trusted users, limit exposure of the service to the internet with network controls, and harden the runtime environment to least privilege. Ongoing monitoring of workflow edits, API activity, and sandbox usage can help detect anomalies that might indicate attempted injections. Deploying a web application firewall and keeping asset inventories up to date are also prudent steps, though they are not substitutes for a proper secure evaluation model.

```js title="Secure src/workflow/evaluator.js"
// Secure evaluation wrapper that prevents access to privileged objects
function evaluateExpressionSafe(expr) {
  // Create a restricted sandbox with a minimal, controlled context
  const sandbox = createSandbox({
    allowedGlobals: ['Math', 'Date', 'JSON'], // whitelisted, safe globals
    thisContext: {} // neutralize 'this' binding to avoid global access
  });
  // Do not expose 'require', 'process', or other privileged APIs
  return sandbox.run(expr);
}
```

---

---
title: "Isolation of Dynamically Evaluated Code Lesson"
---

Building on prior work about validating and sanitizing inputs across services and enforcing boundaries between software components, this lesson extends those ideas into dynamically managed code. It shows how a weak isolation boundary can turn a seemingly safe feature into a gateway for privilege escalation.

Security Concept: Isolation of dynamically evaluated code. This topic fits within Secure Software Design and Runtime Security, highlighting CWE-913 (Improper Control of Dynamically-Managed Code Resources) and the importance of strict context separation, least-privilege execution, and verified sanitization for code that originates from users or automated workflows.

In this lesson, we examine how code execution must occur in a controlled environment. When an expression provided by a user is evaluated at runtime, the surrounding context becomes an attack surface. The goal is to separate user-provided logic from privileged capabilities, preventing access to host modules, the file system, or sensitive data while still enabling useful data transformations.

## Introduction to the vulnerable program

Laid out in a lightweight, web-based Workflow Studio. Analysts assemble automated data tasks by connecting nodes in a graph, and each node can contain a field labeled Expression. The Expression uses a scripting-like syntax enclosed in double curly braces, e.g., {{ ... }}, and the server evaluates the expression as part of workflow execution. The intended behavior is that user-provided expressions transform or filter data without performing privileged actions on the host system. The core assumption is that the evaluation environment is a tight sandbox, isolating the expression from host capabilities.

```python
# Vulnerable evaluator used by the workflow engine (vulnerable)
# The evaluator naively uses the provided globals as the execution context
def evaluate_expression(expr, host_globals):
    return eval(expr, host_globals)

# Simulated host environment passed to the evaluator (vulnerable)
host_globals = {
    '__builtins__': {'print': print, 'open': open},  # limited builtins, but not a secure boundary
    'os': __import__('os'),                       # privilege: access to the operating system
    'secret': 'topsecret'                          # sensitive data
}
```

## Exploring an exploit against the vulnerable program

An attacker with permission to edit workflows could craft expressions designed to break out of the data transformation model by binding the host's global object into the expression's execution context. If the evaluator exposes host globals to the expression, payloads can reach into privileged modules or system resources. The attacker aims to execute commands, read secrets, or modify files, all while the user sees only a harmless data transformation.

```python
# Exploit program: demonstrates how an authenticated editor could run host commands
# Assume the server uses evaluate_expression(expr, host_globals) with the vulnerable evaluator

def exploit():
    host_globals = {
        '__builtins__': {'print': print},
        'os': __import__('os')  # exposed privileged module
    }
    payload = "os.system('echo compromised > /tmp/compromised.txt')"
    result = evaluate_expression(payload, host_globals)
    return result

if __name__ == '__main__':
    exploit()
```

## Patching the program to prevent the exploit

The secure design goal is to remove any binding between the dynamic expression and the host runtime. Instead of passing host globals into the evaluation, we run the expression in a tightly controlled sandbox with a minimal, explicit set of allowed capabilities. This reduces the blast radius of any misconfiguration or malicious input and enforces the principle of least privilege for code execution. A robust patch also considers migrating to a dedicated sandboxed evaluator or a well-vetted isolation library that prevents access to the host environment and system modules.

```python
# Patched evaluator using a strict sandbox
# This evaluator does not expose host modules or the host's globals to the expression

def evaluate_expression_safely(expr):
    # Create a sanitized, minimal globals dictionary
    safe_builtins = {
        'print': print,
        'str': str,
        'int': int,
        'float': float,
        'len': len,
        'range': range,
    }
    safe_globals = {'__builtins__': safe_builtins}
    safe_locals = {}
    return eval(expr, safe_globals, safe_locals)

# Example usage
# The following would raise an error or be undefined in the safe sandbox
# payload = "os.system('echo hacked')"
# evaluate_expression_safely(payload)
```

---

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
