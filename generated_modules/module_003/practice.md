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
