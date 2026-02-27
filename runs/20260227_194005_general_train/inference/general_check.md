# Inference Output
- timestamp: 2026-02-27T19:43:19
- adapter: runs/20260227_194005_general_train/adapter

## PROMPT
Create one MCQ on SQL injection prevention with explanation.

## OUTPUT
Practice Exercise - Prevention Patch: Patch the vulnerability by introducing a whitelist of allowed fields alongside a strict parameter binding process. This prevents users from injecting arbitrary commands through the request. The patch should verify that only the expected fields are processed and that any untrusted input is neutralized before being used in a query. This approach reduces the risk by ensuring that users can only influence a limited, defined set of actions and data, rather than executing arbitrary SQL. The patch should be accompanied by logging and monitoring to detect any attempts to bypass the restrictions.
- Practice Patch: The patched version of the login endpoint should enforce a clear policy of only accepting a strict set of parameters (e.g., the username, password, and a return_to path) and should bind these parameters to the query using parameterized statements that separate data from command structure. Here's an example of how the patch might be implemented:
- The login handler accepts and validates a whitelist of parameters and converts them into a structured data object.
- Instead of building the query with user input directly, the handler constructs a parameterized query that only contains the fields from the whitelist.
- Untrusted input is escaped and never directly inserted into the query string or
