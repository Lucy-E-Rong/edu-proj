---
title: OS Command Injection Lesson
---

In this lesson, we continue building a practical understanding of how untrusted input can influence program behavior. We examine how a trusting assumption about admin input can open an execution path that attackers can exploit, and we connect this to safer coding practices we've discussed in the course so far.

OS Command Injection is a vulnerability pattern that emerges when user-supplied data is embedded into a shell command without proper validation or escaping. In the programming tasks we've tackled, the focus has been on validating inputs, escaping dangerous characters, and choosing safer APIs. This lesson grounds those ideas in a concrete scenario from the DeviceLab Configurator project, showing how a single unsafe data flow can escalate into remote command execution at startup time. By the end, you should be able to identify where user input travels, why the design is risky, and how a safer design can prevent the exploit.

## Introduction to the vulnerable program

The DeviceLab Configurator is a compact classroom-friendly project that provides a lightweight web-like interface for administrators to set per-device options for a fleet of on-premises devices. Administrators enter settings such as log_file_name and report_script_name for each device. The configurator writes these values into per-device configuration files, which are later read by a separate background service to carry out logging and reporting tasks.

A security misstep occurs when the backend component trusts administrator input and writes these values directly into a shell-invoking template without any server-side validation or escaping. The UI performs only a light client-side check and does not sanitize inputs on the server side. The code uses the raw user strings to compose a shell command line that will be executed when the service restarts. This creates a window where a malicious administrator (or an attacker who gains admin access) can inject shell metacharacters into the configuration values. When the background service restarts, the shell interprets the injected content as part of a command, potentially allowing arbitrary commands to run with the privileges of the service.

Below is a minimal example illustrating how the vulnerable pattern might look in code:

```python
import os

def write_device_config(device_id, log_file_name, report_script_name):
    # Vulnerable: interpolates user input into a shell command string
    cmd = f"/usr/local/bin/start_task --device {device_id} --log {log_file_name} --report {report_script_name}"
    os.system(cmd)
```

## Exploring an exploit against the vulnerable program

The exploit targets the moment when the device configuration is consumed to form a shell command. If an administrator provides a log_file_name that includes shell metacharacters, those characters become part of the command that is eventually executed when the service restarts. An attacker could, for example, inject a command separator and a follow-on command, turning a benign startup sequence into something that performs arbitrary actions with the service's privileges.

A small exploit example demonstrates how an attacker might set the vulnerable field to include a benign-looking injected segment. The attacker writes a configuration value like log_file_name: "log.txt; whoami; echo INJECTED" and keeps the rest of the fields valid. When the background service restarts and uses the resulting shell command, the injected segment executes, producing observable effects such as printing the current user or creating a file, depending on the environment.

```python
# Exploit program (conceptual)
import json

config = {
    "device_id": "devX",
    "log_file_name": "log.txt; whoami; echo INJECTED",
    "report_script_name": "report.sh"
}

# Persist the config in the location the service reads from
with open("/configs/devX.conf", "w") as f:
    json.dump(config, f)

# Trigger the restart path that would cause the shell to execute
# This is a placeholder call representing the restart workflow
restart_background_service()
```

Observable outcomes that indicate success might include the appearance of unexpected user information, new files, or other side effects in the system, all tied to the injected command executed during the restart of the background service.

## Patching the program to prevent the exploit

The secure design principle here is to stop passing untrusted user input directly into a shell context. Instead, validate inputs on the server side, restrict values to a safe format, and avoid shell interpretation altogether by writing configuration data to files and invoking services using explicit argument lists rather than shell strings. In practice this means replacing string interpolation that feeds a shell command with a safe data-writing pathway and a separate, well-defined service invocation that does not rely on the shell to parse the inputs.

```python
import json, re, subprocess

# Patched approach: validate inputs and avoid shell

def is_safe(name):
    # Allow only alphanumeric and a small set of punctuation characters
    return re.match(r'^[A-Za-z0-9._-]+$', name) is not None


def apply_config(device_id, log_file_name, report_script_name):
    if not (is_safe(log_file_name) and is_safe(report_script_name)):
        raise ValueError("Unsafe configuration values detected")

    conf = {"log_file_name": log_file_name, "report_script_name": report_script_name}
    with open(f"/configs/{device_id}.conf", "w") as f:
        json.dump(conf, f)

    # Restart the background service without shell involvement
    subprocess.run(["systemctl", "restart", "devicelab-service"], check=True)
```

This patch replaces the dangerous shell invocation with a safe write-to-config approach and a direct, argument-based service restart. It enforces a whitelist for input values, stores configuration in a structured file, and uses a non-shell-based restart mechanism so inputs cannot influence command-line execution. The combination of server-side validation, safe data handling, and explicit process invocation aligns with secure design practices taught in this course and reduces the attack surface for OS command injection.
