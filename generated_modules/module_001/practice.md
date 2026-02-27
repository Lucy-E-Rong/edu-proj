---
title: Shell Command Injection Practice
---

This practice builds on prior lessons by illustrating how untrusted input can drive shell commands in a local service and demonstrates secure design strategies to eliminate that risk. You will observe a small local deployment workflow, identify the injection surface, and apply a focused patch that moves decision logic into a safe, language-native path while invoking external commands through a safe argument list.

## Getting Started

This exercise uses Python for the service and a local Bash helper script, with a Python-based exploit client that communicates over HTTP. Students should have a basic Python development environment capable of running a small FastAPI server for local testing, and a Bash shell available to execute the helper script. The workflow emphasizes understanding how untrusted input is transformed and how to constrain that transformation to secure, explicit operations in the host language.

## Environment Overview

The practice runs entirely locally. It uses a Python-based FastAPI service, a local Bash helper script, and a Python exploit client that interacts with the service over HTTP. No external services are required.

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

This practice requires a minimal set of Python libraries for building a FastAPI service, handling JSON payloads, and making HTTP requests from the exploit client. The goal is to keep dependencies lightweight and focused on demonstrating the vulnerability and patching approach.

```bash title="Install Requirements"
pip install fastapi uvicorn requests pydantic
```

## Scenario Overview

The scenario imagines a small, local deployment service running on the student machine. The UpdateBroker Lab Service is a Python-based FastAPI application that exposes an endpoint /deploy/app-url. It accepts a JSON payload with fields such as app_id, target_group, and timestamp. The server delegates part of the work to a local Bash helper script. The Bash script uses the timestamp value inside an arithmetic expansion expression to decide which deployment path to take and then executes shell commands to fetch and apply updates. The target stores deployment decisions in an in-memory structure and writes occasional logs to a local file. All operations are designed to run strictly on the student's machine, with no external services involved.

The exploit program, ExploitBroker, is a local Python client that interacts with the UpdateBroker service. It sends POST requests to /deploy/app-url with crafted inputs, intentionally manipulating the timestamp field to include Bash arithmetic expansion syntax and shell metacharacters. The exploit prints any command output captured from the local server and notes when the server executes injected commands.

### Target Program

The target is a compact Python-based FastAPI service that exposes an endpoint to deploy applications. Its intended behavior is to receive deployment instructions and trigger a local deployment workflow that is supposed to be controlled and auditable. In the vulnerable version, a portion of the logic relies on a Bash helper script, and the input timestamp value is interpolated into a shell command, creating an opportunity for command injection if the input contains special characters or arithmetic constructs.

```python title="target.py"
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess

app = FastAPI()

class DeployRequest(BaseModel):
    app_id: str
    target_group: str
    timestamp: str

@app.post("/deploy/app-url")
def deploy(req: DeployRequest):
    # Vulnerable: user input is interpolated into a shell command
    # This allows an attacker to inject additional commands via crafted timestamp
    cmd = f"bash ./deploy_helper.sh {req.timestamp}"
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Note: The Bash helper script deploy_helper.sh contains the arithmetic expansion logic
# described in the storyline and is invoked by the shell command above.
```

```bash title="Example of the vulnerable helper script (deploy_helper.sh)"
TIMESTAMP="$1"

# Vulnerable behavior: arithmetic expansion is used to drive logic
case $((TIMESTAMP)) in
  0) echo "Deploy path A"; echo "Fetching updates for A";;
  1) echo "Deploy path B"; echo "Fetching updates for B";;
  *) echo "Default deploy path";;
esac

# The script then executes shell commands to fetch and apply updates.
```

### Exploit Program

The ExploitBroker client interacts with the local UpdateBroker service by sending a crafted payload that targets the vulnerability. The exploit's timestamp field is populated with a string intended to break out of a safe arithmetic path and introduce additional commands into the shell pipeline. When successful, the injected commands may execute on the host and produce observable side effects, such as creating files or emitting additional console output, which the student can observe through the exploit's printed results.

```python title="exploit.py"
import requests
import json

url = "http://localhost:8000/deploy/app-url"

# Normal input first (observe normal behavior)
normal_payload = {
    "app_id": "com.example.app",
    "target_group": "default",
    "timestamp": "1610000000"
}
print("Sending normal payload...")
resp = requests.post(url, json=normal_payload)
print("Status:", resp.status_code)
print("Response:", resp.text)

# Crafted input to trigger injection via shell command
# The timestamp includes a shell metacharacter sequence to inject commands after arithmetic expansion
exploit_timestamp = "0); echo INJECTED_COMMAND_EXECUTED; #"
exploit_payload = {
    "app_id": "com.example.app",
    "target_group": "default",
    "timestamp": exploit_timestamp
}
print("\nSending crafted payload to trigger vulnerability...")
resp = requests.post(url, json=exploit_payload)
print("Status:", resp.status_code)
print("Response:\n", resp.text)
```

## Practice Objectives

### Task 1: Observe vulnerable behavior

Begin by running the local UpdateBroker service and sending a normal request to /deploy/app-url. Observe that the service accepts the payload, routes the request to the Bash helper script, and logs or returns the outcome as expected. This establishes the baseline for normal operation and demonstrates how the endpoint behaves in the absence of an attack.

```python
# Example: Start the FastAPI server locally (you may use your preferred startup command)
# e.g., uvicorn target:app --reload --port 8000
```

### Task 2: Trigger the vulnerability

Craft a request where the timestamp field contains arithmetic and shell metacharacters designed to break out of the intended arithmetic path and inject additional commands into the shell. Send this request to the same endpoint and observe whether the server executes arbitrary commands, produces additional output, or creates files on the host. The goal is to recognize that the vulnerable code path can be exploited with untrusted input.

```python
# Example: Craft a harmful payload for testing (do not run in production)
# payload construction handled by your exploit client
```

### Task 3: Implement a single patch

Implement a targeted patch that removes the shell-based, input-derived command construction. Move the critical decision logic into a safe, language-native implementation and invoke external commands using a safe argument array rather than string concatenation. The patch can include two key changes: (a) validate and parse the timestamp in Python, and (b) perform any external operations through subprocess.run with a list of arguments or, better, implement the decision logic entirely in Python if feasible. The patch should preserve the service's behavior while eliminating the injection surface.

```python title="Patch Sketch"
# Example patch sketch (to be refined in your codebase)
import shlex

class DeployRequest(BaseModel):
    app_id: str
    target_group: str
    timestamp: str

def deploy(req: DeployRequest):
    # Validate timestamp as numeric and within range
    try:
        ts = int(req.timestamp)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp")
    # Implement logic in Python and call external commands with a safe argument list
    if ts == 0:
        # perform path A via Python-native logic, or via subprocess.run(["bash","-lc","..."], shell=False)
        pass
    # Example of safe external call
    # result = subprocess.run(["bash","deploy_helper.sh", str(ts)], capture_output=True, text=True, timeout=5)
```

### Task 4: Verify the patch

Re-run the exploit against the patched target. Confirm that the same crafted input no longer executes arbitrary commands and that the server responds with a safe handling message or error without performing unintended actions. Include a basic input validation rule (for example, only numeric timestamps within a defined range) and ensure logs reflect legitimate operations. Verify that normal requests still function as expected.

```python
# Example: basic verification test stub
```
