---
title: SQL Injection through unsafe dictionary expansion Lesson
---

This lesson continues the exploration of how untrusted input can influence data access paths and query generation, even when using a robust framework. It shows how unsafe input can steer query construction and undermine protections if internal controls are exposed to the query-building path.

Security Concept: SQL Injection through unsafe dictionary expansion. This concept fits into the course topic Secure Data Access and Query Integrity, which examines how inputs flow from the web layer into the data layer and how improper handling can undermine data protection controls.

This lesson builds on the broader idea that inputs flow from the web layer into the data layer and that validating, whitelisting, and separating input handling from query construction are essential to maintain deterministic and auditable access controls.

## Introduction to the vulnerable program

The setting is a fictional internal HR analytics web application written in server-side Python. Its job is to let staff filter employee records through a web interface by supplying query parameters in HTTP requests. The program assumes that whatever comes from the web layer will be treated as part of the query specification and handed directly to the query builder. In this setup, internal control keys—such as a parameter named _connector or similar ones—can be exposed to the query construction path. There is no explicit whitelisting or validation to separate legitimate filter fields from internal control parameters. This creates a straightforward path for untrusted input to influence the resulting SQL logic.

```python
# Vulnerable: direct dictionary unpacking from user input

def search_employees(request):
    # User-provided query parameters, e.g., ?department=Engineering&_connector=OR
    params = dict(request.GET)
    # Unvalidated expansion into the query builder
    results = Employee.filter(**params)
    return results
```

## Exploring an exploit against the vulnerable program

The exploit aims to alter how the WHERE clause is assembled by injecting an internal control parameter that the query builder interprets as a logical connector. By supplying a key like _connector with a crafted value, an attacker can change the intended conjunction of conditions from the safe default (typically AND) to a broader one (such as OR). This effectively widens the scope of matching records, potentially bypassing access controls and exposing sensitive employee data. The exploit interacts with the vulnerable program by sending HTTP query parameters that include both legitimate filters and attacker-controlled control parameters, which the program then forwards directly into the query construction path.

```python
# Illustrative exploit (conceptual)
class MockRequest:
    def __init__(self, params):
        self.GET = params

def exploit_example():
    # Attacker targets the _connector to change join logic
    req = MockRequest({'department': 'Engineering', '_connector': ' OR '})
    return search_employees(req)
```

## Patching the program to prevent the exploit

The secure design approach removes the risk by refusing to pass untrusted user input through to the query builder as raw parameters. Instead, the application defines a whitelist of allowed filter fields and explicitly constructs the query from only those fields. Internal control parameters are filtered out early, and the query is built using safe, parameterized methods rather than unconstrained dictionary expansion. This ensures that attacker-provided keys cannot influence how the SQL logic is joined, and it aligns with the broader principle of keeping data access deterministic and auditable.

Safe, responsible usage: Demonstrations of this vulnerability and the mitigation should occur only in isolated lab environments and never against production data. Instructors should emphasize ethics and responsible security practice.

```python
# Patched approach: enforce a whitelist and build the query deterministically
ALLOWED_FIELDS = {'department', 'role', 'status', 'location'}

def search_employees_secure(request):
    raw_params = dict(request.GET)
    # Only keep whitelisted fields; drop internal controls like _connector
    safe_params = {k: v for k, v in raw_params.items() if k in ALLOWED_FIELDS}

    # Build the query in a controlled way using only safe parameters
    q = Employee.filter(**safe_params)
    return q.all()
```
