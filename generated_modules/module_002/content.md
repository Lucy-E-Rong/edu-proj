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
