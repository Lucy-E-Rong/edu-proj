---
title: Insecure Deserialization Practice
---

In this practice, you extend the deserialization topic by examining a local configuration loader that mishandles serialized data. The scenario centers on a vulnerability pattern tied to a hypothetical CVE-2025-62368, where a trusted-looking configuration file is deserialized without validating its origin or type. The goal is to understand how untrusted serialized data can become active code paths in a running program, and to explore safe design choices that prevent such abuse. You will work with two small, self-contained programs that run entirely on a workstation: a target program called ConfigLoader and an exploit helper called payload_builder. The exercise stays on a local machine and uses only in-memory or disk-based data, ensuring this is an isolated lab exercise suitable for classroom discussion. The storyline emphasizes how unsafe deserialization can enable unintended behavior, such as file creation or the invocation of system commands, and then moves toward practical defenses through safer loading practices and integrity checks.

## Getting Started

This exercise uses Python and the standard library to illustrate the vulnerability pattern. You will study a tiny desktop/CLI tool named ConfigLoader that reads a file named config.dat, deserializes its contents, and applies the resulting configuration to the current session. The exploit helper, payload_builder, conceptually generates the malicious payload that could trigger unintended actions when processed by the loader. The vulnerability arises when the loader deserializes untrusted data and then invokes methods on the resulting object without validating its type or shape. The learning objective is to connect the observable behavior of a running program with the underlying deserialization risk, and to practice mitigation strategies such as type whitelisting, safer formats, and payload integrity checks.

### Virtual Environment

A virtual environment creates an isolated Python workspace where you can install and manage packages without affecting anything else on your system. It is not required for this practice, but it is strongly recommended because it gives you a clean and consistent setup. Using a virtual environment helps avoid conflicts and makes it easier to remove or reset dependencies later. You may continue without one, but adopting virtual environments early is a valuable habit.

```title="Create a Virtual Environment"
python -m venv .venv
```

```title="Activate the Virtual Environment"
# On Windows
.venv\Scripts\activate

# On MacOS or Linux
source .venv/bin/activate
```

```title="Deactivate the Virtual Environment"
deactivate
```

### Install Requirements

This practice relies on Python's standard library; no external dependencies are required. You will work with a small deserialization example and simple file-based I/O to illustrate the vulnerability and the defenses. If you choose to run the exercises in a dedicated environment, you can still use the instructions below as a baseline.

```bash title="Install Requirements"
# No external dependencies required; use the Python standard library only.
```

## Scenario Overview

The scenario provides a controlled lab to explore how an insecure deserialization vulnerability manifests in a local configuration system. The ConfigLoader reads config.dat, deserializes its contents into an object, and then calls a method on that object to apply the configuration. The vulnerability pattern occurs when the loader accepts the deserialized object without validating its type or origin. An attacker who can influence config.dat could craft a serialized payload that, when deserialized, executes unintended actions on the host—for example, creating marker files, writing logs, or even invoking system commands. This practice ties the concept of unsafe deserialization to a concrete, observable outcome in a local environment and demonstrates how secure design decisions prevent such abuse.

### Target Program

ConfigLoader is a tiny desktop/CLI tool designed to illustrate a realistic yet simplified configuration workflow. Its responsibility is to load a file named config.dat, deserialize its contents, and apply the resulting settings to the running session. The security mistake lies in deserializing untrusted data and then directly invoking methods on the resulting object without validating that the object is of an approved type or shape. The observable consequence of this misdesign is that a crafted payload could cause the loader to perform actions beyond legitimate configuration changes, such as creating files or running shell commands.

```python title="target.py"
import pickle
import sys

# Vulnerable ConfigLoader that deserializes a payload and calls apply()

def load_config(path: str = "config.dat"):
    with open(path, 'rb') as f:
        data = f.read()
    # Unsafe: untrusted data is directly deserialized
    obj = pickle.loads(data)
    # Intentionally naive: call an expected method without type checks
    if hasattr(obj, 'apply'):
        obj.apply()
    else:
        print("Loaded object has no apply() method; nothing to apply.")

if __name__ == '__main__':
    load_config()
```

### Exploit Program

payload_builder is a local helper script conceptually designed to generate a malicious payload intended to demonstrate the vulnerability when loaded by ConfigLoader. In a controlled lab, the exploit payload would be written to config.dat so that, when ConfigLoader runs, the deserialization step triggers the unintended action. The exact payload construction is purposefully not provided here to keep the exercise safe for classroom use; the emphasis is on understanding the vulnerability pattern and observing its observable effects in a contained setting.

```python title="exploit.py"
import pickle

# Demonstrative, self-contained payload that, if loaded by an unsafe deserializer,
# would execute a harmless side effect (creating a marker file).
class Payload:
    def __reduce__(self):
        import os
        return (os.system, ("echo 'payload executed' > payload_marker.txt",))


def build_payload():
    payload = Payload()
    with open('config.dat', 'wb') as f:
        f.write(pickle.dumps(payload))

if __name__ == '__main__':
    build_payload()
```

## Practice Objectives

### Task 1: Observe vulnerable behavior

In this task you observe how the vulnerable loader behaves when given a benign configuration payload. Generate a safe, non-harmful payload that exposes the normal application flow. Create a benign payload file using a small Python object that defines an apply() method and then run the loader to confirm that the benign path executes as expected. You may generate a benign configuration and save it to config.dat, then run the loader to verify that apply() is invoked and the expected output is shown.

```python
# Task 1: Create a benign config file for Task 1
import pickle

class SafeConfig:
    def __init__(self):
        self.settings = {'theme': 'dark', 'volume': 70}
    def apply(self):
        print("Applied settings:", self.settings)

with open('config.dat', 'wb') as f:
    f.write(pickle.dumps(SafeConfig()))
```

### Task 2: Trigger the vulnerability

Now use the exploit payload to demonstrate the deserialization vulnerability. Run the exploit builder to place a crafted payload into config.dat, then run the vulnerable loader. Observe the side effect that occurs when the payload is deserialized and executed. In this controlled setting, you should see the marker file or a visible side effect indicating that the exploit payload ran.

```python
# Task 2: Generate a malicious payload and load it with the vulnerable loader
# Run this to produce the payload
# python exploit.py
# Then run the loader to observe the effect
```

Expected observable outcome: a side effect such as the creation of a marker file (payload_marker.txt) indicating that the payload was executed by the deserializer.

### Task 3: Patch a single vulnerability surface

Apply a targeted patch to the vulnerability surface by replacing the unsafe deserialization with a safe loading approach that validates the type of the deserialized object. The patch should prevent arbitrary code execution by ensuring only known, expected configurations are accepted. Implement a whitelist-based check or switch to a safe data format such as JSON for the configuration, with strict structure verification.

```python
# Task 3: Patch to whitelist allowed types
import pickle

ALLOWED_TYPES = {'SafeConfig'}

class SafeConfig:
    def __init__(self, settings=None):
        self.settings = settings or {'theme': 'dark', 'volume': 70}
    def apply(self):
        print("Patched: Applied settings:", self.settings)


def load_config(path: str = "config.dat"):
    with open(path, 'rb') as f:
        data = f.read()
    obj = pickle.loads(data)
    # Security patch: only allow known, whitelisted types
    if type(obj).__name__ not in ALLOWED_TYPES:
        print("Untrusted object type; aborting load.")
        return
    if hasattr(obj, 'apply'):
        obj.apply()

if __name__ == '__main__':
    load_config()
```

### Task 4: Patch the verification layer

Go a step further by adding integrity and authenticity checks so that untrusted data cannot be accepted without verification. Introduce a signed payload mechanism (for example, a simple HMAC-based signature) and verify the signature before applying the configuration. The patch should preserve legitimate configuration loading while preventing arbitrary code execution from tampered data.

```python
# Task 4: Add a signed-payload verification step (HMAC-based)
import json
import hmac
import hashlib

SECRET_KEY = b'supersecret'

# The loader now expects a JSON payload with config and signature

def verify_signature(message_bytes, signature_hex):
    mac = hmac.new(SECRET_KEY, message_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature_hex)


def load_config(path: str = "config.dat"):
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        payload = json.loads(raw.decode('utf-8'))
    except Exception:
        print("Invalid JSON payload.")
        return

    config_obj = payload.get('config')
    signature = payload.get('signature')
    if config_obj is None or signature is None:
        print("Missing config or signature; aborting.")
        return

    # Verify integrity before using the config
    config_bytes = json.dumps(config_obj, sort_keys=True).encode('utf-8')
    if not verify_signature(config_bytes, signature):
        print("Payload integrity verification failed; aborting.")
        return

    # If verification passes, apply settings as a safe, structured dict-laden config
    print("Payload verified; applying safe configuration:", config_obj)

if __name__ == '__main__':
    load_config()
```

### Patch Verification

Re-run the exploit tasks against the patched ConfigLoader. Expectation: the benign load should still work, but the malicious payload should be rejected or ignored. The loader should log a security-focused message indicating that the payload was untrusted or failed integrity checks. In other words, the patched loader preserves legitimate configuration loading while blocking untrusted inputs.

Reflection: This exercise reinforces the core vulnerability pattern of unsafe deserialization, demonstrates practical defenses (type whitelisting, safe formats, and payload integrity checks), and helps students practice both identifying and mitigating this risk in a controlled, local lab setting.
