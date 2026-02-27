---
title: Command Injection Lesson
---

In this lesson, we connect the topic to prior material about how untrusted input can flow through a program and why strict input handling is essential for secure software. We examine a concrete vulnerability pattern that arises when code constructs or generates commands from user-supplied data, showing how design choices can expose an attack surface in real-world tooling.

Command Injection, CWE-94, occurs when untrusted input is used to form or influence a shell command. It sits within the Secure Coding and Software Security themes of this course, illustrating why data boundaries matter when APIs and scripts interact with the operating system and how misusing shell features can undermine deployment workflows.

The core concept is to treat all input as untrusted and to avoid constructing shell commands from that input. Secure design favors clear data-flow boundaries, validated inputs, and the use of safe interfaces or parameterized calls rather than string-concatenated commands. This aligns with the course emphasis on least privilege, defense in depth, and minimizing the attack surface presented by management interfaces reachable from untrusted networks.

## Introduction to the vulnerable program

The UpdateBridge tool is a lightweight enterprise maintenance utility that exposes a web API used by IT staff to map software update URLs to device groups and to configure file transfer settings for a fleet of internal devices. Behind the scenes, a Bash script participates in the update workflow to validate inputs and drive deployment commands based on request fields such as a timestamp and a target group. The intended behavior is straightforward: given a group and a timestamp, the system should invoke the appropriate deployment step with those values. The system assumes that inputs sourced from the API are trusted or sufficiently sanitized before influencing command execution.

However, a security mistake occurs when the backend script processes user-supplied fields by placing them into a Bash arithmetic expansion construct, for example using $(( ... )). The design assumes basic sanitization is enough and that arithmetic evaluation will operate only on harmless data; in reality, parts of the user input are evaluated as arithmetic expressions. This can allow crafted input to alter the command flow, potentially causing the server to execute commands beyond the intended deployment logic.

```bash
#!/bin/bash
# Vulnerable snippet illustrating the risky pattern described in the storyline
GROUP="$1"
TIMESTAMP="$2"

# Vulnerable: attacker-controlled TIMESTAMP is evaluated inside arithmetic expansion
RESULT=$(( TIMESTAMP ))
/usr/local/bin/deploy --group "$GROUP" --timestamp "$RESULT"
```

## Exploring an exploit against the vulnerable program

Exploitation aims to achieve arbitrary command execution by feeding the endpoint with crafted input that manipulates the arithmetic evaluation performed on user data. An attacker who can reach the exposed API without credentials can submit a request whose TIMESTAMP field contains an expression intended to alter the flow of execution or trigger unintended behavior. When the script evaluates the arithmetic expression, parts of the input may influence which commands run next, and, in some scenarios, additional shell commands can be introduced into the evaluated context. The observable impact would be unexpected commands executing on the updater host, unusual process activity, and potential exposure of configuration data used to manage devices and credentials.

```python
# Exploit Program (illustrative)
import requests

# Target endpoint used by UpdateBridge (illustrative URL)
target_url = "http://updatebridge.internal/api/map"
payload = {
    "group": "default",
    "timestamp": "0) ; whoami ; ("  # crafted to break out of the arithmetic context
}
response = requests.post(target_url, json=payload)
print(response.status_code, response.text)
```

## Patching the program to prevent the exploit

The secure design change replaces the risky arithmetic evaluation with strict input validation and a direct, safe invocation of the deployment command. The timestamp field should be treated as data only and must be validated against a strict allowlist (for example, digits only). The code should avoid constructing or evaluating shell commands from user data entirely, instead passing trusted parameters to a well-defined deployment tool or API. This reduces the risk of code being injected through untrusted input and enforces the principle of least privilege by ensuring that only a controlled, predictable operation is performed.

```bash
# Patched Bash snippet (safe approach)
GROUP="$1"
TIMESTAMP="$2"

# Validate TIMESTAMP strictly as digits only and avoid any shell arithmetic expansion
if [[ "$TIMESTAMP" =~ ^[0-9]+$ ]]; then
  /usr/local/bin/deploy --group "$GROUP" --timestamp "$TIMESTAMP"
else
  echo "Invalid timestamp" >&2
  exit 1
fi
```
