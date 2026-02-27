---
title: CWE-502: Deserialization of Untrusted Data Lesson
---

This lesson connects to prior material on trust boundaries in API design, illustrating how unchecked deserialization at a network boundary can undermine security.

CWE-502: Deserialization of Untrusted Data is the security concept illustrated in this lesson, fitting into Secure API design and data handling.

Deserialization of untrusted data relies on the broader course idea of trust boundaries and input handling. It demonstrates how turning client-provided object graphs into executable behavior can enable remote code execution, and outlines mitigations such as using schema-driven formats, explicit unmarshalers with type guards, and least-privilege handling.

## Introduction to the vulnerable program

A small Python service called NoteShare API, designed as a teaching prototype for a class project, accepts a payload representing a Note object and deserializes it on the server side using pickle. This trust-at-the-boundary assumption allows an attacker to craft input that could run arbitrary code during deserialization, compromising data integrity and service availability.

```python
# Vulnerable NoteShare API (conceptual)
import pickle

class Note:
    def __init__(self, title, content):
        self.title = title
        self.content = content

def store_note(raw_payload):
    # Unsafe: deserializes untrusted data
    note = pickle.loads(raw_payload)
    # pretend to persist the note
    return note
```

## Exploring an exploit against the vulnerable program

An attacker tries to perform actions beyond simply reconstructing a Note object. By submitting a specially crafted serialized payload, unpickling can invoke code during deserialization. In Python, pickle can reconstruct objects by calling constructors and by evaluating special methods that can execute code during unpickling. The payload is designed so that, when unpickled, it runs attacker-chosen commands, such as creating files, spawning a shell, or contacting a malicious server.

```python
# Attacker crafts a payload that triggers code execution upon unpickling
import pickle, os

class Evil:
    def __reduce__(self):
        # Run a harmless command to demonstrate execution
        return (os.system, ("echo pwned > /tmp/pwned.txt",))

payload = pickle.dumps(Evil())
print(payload)
```

If the NoteShare API blindly executes pickle.loads(payload), the embedded function will run, illustrating how untrusted, deserialized data can act on the server beyond merely reconstructing a Note object. The observable impact could be as simple as a new file being created, a process spawning, or an outbound network connection being made, signaling a successful exploit.

## Patching the program to prevent the exploit

The secure design change is to remove the untrusted object deserialization at the API boundary and instead parse and validate only a well-defined data shape. In practical terms, this means switching to a safe, schema-driven data format (such as JSON) and implementing an explicit, type-checked deserialization path that constructs only the intended Note objects. The untrusted data boundary is closed by ensuring that client input cannot influence the code execution path on the server, and by validating both the presence and types of required fields before any Note instance is created. This approach prevents arbitrary code execution and makes the service more robust against malformed or malicious input.

```python
# Secure deserialization: parse JSON with strict schema
import json
from dataclasses import dataclass

@dataclass
class Note:
    title: str
    content: str

def deserialize_note_secure(payload_bytes):
    # Expect a JSON payload representing a Note
    data = json.loads(payload_bytes.decode('utf-8'))
    if not isinstance(data, dict):
        raise ValueError("Invalid payload: expected JSON object")

    title = data.get("title")
    content = data.get("content")

    if not isinstance(title, str) or not isinstance(content, str):
        raise ValueError("Invalid field types: 'title' and 'content' must be strings")

    return Note(title=title, content=content)

def store_note_safe(payload_bytes):
    note = deserialize_note_secure(payload_bytes)
    # Here we would persist the note securely
    return note
```
