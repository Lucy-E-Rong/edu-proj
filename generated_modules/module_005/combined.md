---
title: MotionEye Real Exploit
course: Programming 2
---

OS command injection can occur when a web-based configuration interface writes user-supplied fields into system or backend templates without proper sanitization. If input is later executed by a shell or shell-like interpreter, an attacker can run arbitrary commands with the privileges of the affected process. In MotionEye, an administrative field used to name image or movie files was found unsafe when written into backend configuration data that the MotionEye server processes, creating a path for command execution during a restart or reload of the service. Clear separation and rigorous validation of input handling, data representation, and back-end execution boundaries are essential to prevent such risks.

## About the Product

MotionEye is an open-source, Python-based web front-end for the Motion video surveillance backend. It translates Motion's capability to record and manage video streams into a browser-based interface that administrators can use to configure cameras, storage locations, and file naming conventions. The project is commonly deployed on local networks, often in containerized environments, where admins rely on MotionEye to organize captured snapshots and video clips and to provide convenient access to configuration settings through the web UI. The configuration data written by the UI ultimately informs how the Motion backend stores and handles media files.

MotionEye's design favors accessibility and rapid configuration: an authenticated administrator can specify where to store snapshots and recordings, and the UI persists these preferences into per-camera configuration files that the Motion backend reads during operation. This abstraction, while user-friendly, moves powerful decisions into the web interface and its server-side processing, making secure handling of user input essential to prevent unintended command execution or manipulation of system state.

## The Intended Behavior

Under normal operation, the web interface allows an administrator to configure per-camera settings, including the destination paths for image and video assets. The fields image_file_name and movie_file_name are meant to accept simple, safe filenames or path templates. When the administrator saves settings, the server should sanitize and store these values in a backend configuration representation that is later consumed by Motion's processing pipeline. The design assumes that the values entered by trusted administrators will be treated as data, not as commands, and that the backend will interpret them strictly as data for file naming rather than as instructions to be executed by the system shell.

This assumption relies on a secure boundary between user input and the shell or command interpreter that orchestrates the backend. If that boundary is blurred—if user-provided values are interpolated into shell commands or shell-like templates without proper escaping—ordinary configuration workflows can become a conduit for remote code execution. In short, the intended behavior presumes input data safety, while the actual implementation risks treating that data as executable instructions when the configuration pipeline interpolates values into shell contexts.

## The Vulnerability

CVE-2025-60787 describes a critical OS command injection vulnerability within MotionEye's configuration pipeline. The core failure stems from inadequate input validation and escaping in the function that converts the web UI input into a configuration representation that the Motion backend processes. Specifically, values entered for image_file_name and movie_file_name are written into a template or command string without sufficient filtering. When MotionEye restarts and the backend interprets the configuration, maliciously crafted values containing shell metacharacters can be executed in the host shell. This vulnerability is rooted in improper input validation (CWE-20) and OS command injection (CWE-78), as well as insufficient encoding or escaping of output (CWE-116).

In practice, an attacker who has administrative access to MotionEye's web UI and can modify camera configuration fields could insert input that includes shell constructs such as $(...) or other metacharacters. The vulnerable code paths concatenate or interpolate the user input into a shell-invoked command or a shell-expanded template. After the configuration is saved and the MotionEye service restarts, the shell interprets the injected payload, executing arbitrary commands with the privileges of the MotionEye process. The impact is severe, potentially granting full command execution, access to stored media, and broader compromise if the container or host is misconfigured.

```python title="Vulnerable motioneye/config.py"
# This exemplary snippet illustrates insecure handling where user input is
# directly interpolated into a shell command template and then executed.
import os

def motion_camera_ui_to_dict(ui_input):
    # ui_input is a dictionary from the web UI containing fields like
    # 'image_file_name' and 'movie_file_name'
    image_file = ui_input.get("image_file_name")
    movie_file = ui_input.get("movie_file_name")

    # Insecure: directly interpolating user input into a shell command
    # The resulting shell command could be interpreted with metacharacters
    # from the user input, leading to command execution.
    shell_cmd = f"setup_camera --image '{image_file}' --movie '{movie_file}'"

    # Danger: executing a shell command constructed from untrusted input
    os.system(shell_cmd)

    return {"image_file_name": image_file, "movie_file_name": movie_file}
```

## Mitigation

Mitigating this vulnerability requires removing any design that allows untrusted input to influence shell commands or other interpretable system operations. The secure approach includes validating inputs against a whitelist of safe characters, escaping or encoding only when appropriate, and avoiding the use of shell commands for configuration tasks altogether. A robust defense-in-depth strategy combines input validation, safe data handling, and explicit separation of data from command execution. Instead of building and executing shell strings from user input, the backend should use safe APIs, structured configuration formats, and explicit parameter passing. This approach prevents attacker-controlled input from being treated as executable code and reduces the blast radius if input validation fails.

A concrete secure implementation replaces the risky template-based approach with a controlled, data-only write path. Validated file name components are stored in a structured format (for example, JSON) and consumed by a dedicated, well-audited backend component that performs the actual file storage operations without invoking the shell. Whitelisting for allowed filename characters, along with explicit basename extraction and path reconciliation, prevents path traversal and command injection risks. Additionally, restricting admin UI access with proper authentication, network controls, and monitoring reduces the likelihood that an attacker gains the necessary access to alter configuration settings in the first place.

```python title="Secure motioneye/config.py"
import json
import os
import re

FOLDER_ROOT = "/var/lib/motioneye/cams"

def sanitize_filename(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError("Invalid filename type")
    # Whitelist: letters, digits, dot, dash, underscore
    if not re.fullmatch(r"[\w.\-]+", name):
        raise ValueError("Invalid characters in filename")
    return os.path.basename(name)


def update_camera_config(ui_input: dict):
    image = ui_input.get("image_file_name", "")
    movie = ui_input.get("movie_file_name", "")

    image_safe = sanitize_filename(image)
    movie_safe = sanitize_filename(movie)

    config = {
        "image_file_name": image_safe,
        "movie_file_name": movie_safe,
    }

    # Write configuration in a structured format, avoiding shell usage
    cam_id = ui_input.get("camera_id", "default")
    cfg_path = f"{FOLDER_ROOT}/{cam_id}.cfg.json"
    with open(cfg_path, "w") as f:
        json.dump(config, f, indent=2)
```

---

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

---

---
title: Shell Command Injection via Configuration-Driven Startup Practice
---

In this practice, you will confront a concrete OS command injection vulnerability that arises when a program constructs shell commands by inserting user-controlled configuration data into a shell invocation. The scenario demonstrates how a locally run tool can be manipulated through its configuration file, turning benign inputs into commands the local shell will interpret and execute. Throughout the tasks, you will see how a secure design—avoiding string interpolation in shells, validating inputs, and using safer process invocation patterns—prevents the exploitation shown here.

This practice connects OS command injection concepts to a configuration-driven workflow in Local Data Studio.

## Getting Started

This exercise uses Python as the implementation language for both the target program and the exploit. You will work with Local Data Studio, a small local CLI/desktop-like tool that reads a YAML/INI-like configuration file to manage per-job settings. The exploit runs on the same machine and directly edits the configuration file used by Local Data Studio. The workflow remains entirely local with no network communication required. A virtual environment is provided to keep dependencies isolated and repeatable, but it is optional if you prefer to run the code in your own environment.

### Virtual Environment

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

This task uses Python and a lightweight parser for the YAML/INI-like configuration. You will install a small set of dependencies sufficient for loading and writing the configuration file used by Local Data Studio.

```bash title="Install Requirements"
pip install pyyaml
```

## Scenario Overview

Local Data Studio manages simple analysis jobs for a local dataset. It stores per-job settings in a YAML/INI-like configuration file. One setting, start_command_template, is used by the startup workflow to assemble a shell command that launches the analysis task. The system builds the final shell command by inserting the configured start_command_template into a shell invocation and then executes that command with the local shell. Because this runs locally, there is no remote component, but the vulnerability demonstrates how attacker-controlled input can influence what commands get executed on the host.

### Target Program

Local Data Studio is a small Python-based CLI/desktop-like tool capable of starting analysis jobs using a per-job configuration file. The critical vulnerability lies in how the program constructs the shell command: it takes the user-supplied start_command_template and directly interpolates it into a shell invocation. If an attacker can modify this configuration, they can inject additional commands that the shell will execute.

```python title="target.py"
import os
import yaml

CONFIG_PATH = 'config.yaml'

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def start_job(job_id=1):
    config = load_config(CONFIG_PATH)
    template = config.get('start_command_template', 'echo Hello')
    # Vulnerable: interpolate user-controlled template into a shell command
    full_cmd = "/bin/sh -c '" + template + "' " + str(job_id)
    os.system(full_cmd)

if __name__ == '__main__':
    start_job()
```

### Exploit Program

ExploitScript is a tiny Python tool that edits the target's configuration file used by Local Data Studio. It writes a crafted start_command_template that contains a shell metacharacter payload. The exploit interacts with the target by directly updating its config file (or simulating user edits via the program's own CLI) and then triggers the job start/restart flow to observe whether the payload executes.

```python title="exploit.py"
import yaml
import time

CONFIG_PATH = 'config.yaml'

payload = "echo INJECTED_MARKER; touch /tmp/injected_marker; echo DONE"

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)

def write_config(path, cfg):
    with open(path, 'w') as f:
        yaml.safe_dump(cfg, f)

if __name__ == '__main__':
    cfg = load_config(CONFIG_PATH)
    cfg['start_command_template'] = payload
    write_config(CONFIG_PATH, cfg)
    print('Exploit injected payload into config.')
    # In a real workflow, you would trigger the start/restart flow here.
    time.sleep(0.5)
    print('Payload committed. Trigger the job start to observe effect.')
```

## Practice Objectives

### Task 1: Observe vulnerable behavior

You will run the Local Data Studio with a benign start_command_template and observe normal startup behavior. The configuration data is embedded into a shell command that is executed by /bin/sh, so the system prints output or creates results that confirm normal operation without any side effects beyond the intended job.

### Task 2: Trigger the vulnerability

Using ExploitScript, insert a payload into start_command_template that contains shell metacharacters designed to execute a secondary command. Save the configuration and trigger the job start flow. Observe whether the injected payload executes, evidenced by a marker file or output printed by the injected command.

### Task 3: Patch Task — implement a sanitization/safer invocation

Patch the target program to prevent command injection. You have two secure design options to explore:

- Implement a sanitization function that validates start_command_template against a whitelist of safe characters and patterns before it is used. Demonstrate that dangerous payloads are rejected or sanitized.
- Change the invocation approach to avoid shell interpretation entirely by parsing the template into a token list and invoking the command without a shell, or by passing arguments to a separate process in a safe, parameterized manner.

### Task 4: Patch Task — verify the patch

Re-run the exploit steps to verify that the patched target neutralizes the payload. Demonstrate that previously dangerous payloads are rejected or that the command is executed without shell interpretation, preventing unintended command execution.
