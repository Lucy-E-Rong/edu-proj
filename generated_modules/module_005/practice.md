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
