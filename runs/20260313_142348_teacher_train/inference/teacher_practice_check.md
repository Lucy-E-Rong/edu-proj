# Inference Output
- timestamp: 2026-03-13T14:26:26
- adapter: runs/20260313_142348_teacher_train/adapter

## PROMPT
Create a beginner-friendly SQL security practice activity about parameterized queries.

## OUTPUT
In this SQL defensive cybersecurity practice, you'll learn how to construct parameterized queries to prevent SQL injection attacks. You'll be working with a table containing user data, and your task is to create a stored procedure that safely handles user input for searching. The goal is to teach you how to use placeholders in SQL statements to protect against malicious input. This exercise emphasizes the importance of separating data from commands in SQL, a fundamental concept in secure database programming.

```sql
-- Create a table for user data (e.g., user_id, username, email)
CREATE TABLE users (user_id INT PRIMARY KEY, username VARCHAR(50), email VARCHAR(100));

-- Insert sample data (for practice purposes)
INSERT INTO users (user_id, username, email) VALUES (1, 'Alice', 'alice@example.com'), (2, 'Bob', 'bob@example.com');

-- Stored procedure to search for users by name
DELIMITER //
CREATE PROCEDURE search_user(IN user_name VARCHAR(50))
BEGIN
    SELECT * FROM users WHERE username LIKE CONCAT('%', user_name, '%');
END //
DELIMITER ;

-- Call the stored procedure with a safe input
CALL search_user('Alice');
```

This practice activity teaches defensive cybersecurity by demonstrating how to use parameterized queries to prevent SQL injection. It emphasizes the importance of separating data from commands, a fundamental principle in secure database programming. By practicing this technique, learners will develop a foundational understanding of how to protect against common SQL vulnerabilities.

Remember, in real-world scenarios, always validate and sanitize user inputs to ensure the safety and integrity of your database. This practice activity serves as a starting point for understanding SQL security best practices.

```python
import pandas as pd

# Simulate a database response for practice purposes
user_data = {
    'user_id': [1, 2],
    'username': ['Alice', 'Bob'],
    'email': ['alice@example.com', 'bob@example.com']
}
df = pd.DataFrame(user_data)

print("User Data (for practice purposes):")
print(df)
```

```python
def search_user(user_name):
    """Simulate a safe search function for practice."""
    safe_user_name = f'%{user_name}%'
    return df[df['username'].str.contains(safe_user_name)]

# Example usage: search for 'Alice'
result = search_user('Alice')
print("\nSearch Result (for practice purposes):")
print(result)
```

```sql
-- SQL defensive cybersecurity practice: parameterized queries
SELECT * FROM users WHERE username LIKE CONCAT('%', @user_name, '%');
```

```bash
# SQL defensive cybersecurity practice: parameterized queries
# Simulate a safe search using placeholders for practice
SELECT * FROM users WHERE username LIKE CONCAT('%', @user_name, '%');
```

```python
# SQL defensive cybersecurity practice: parameterized queries
# Simulate a safe search using string formatting for practice
safe_user_name = f'%{user_name}%'
query = f"SELECT * FROM users WHERE username LIKE '{safe_user_name}';"
print("Formatted Query (for practice purposes):")
print(query)
```

```sql
-- SQL defensive cybersecurity practice: parameterized queries
-- Using prepared statements for practice
PREPARE stmt FROM 'SELECT * FROM users WHERE username LIKE?';
EXECUTE stmt USING @user_name;
DEALLOCATE PREPARE stmt;
```

```python
# SQL defensive cybersecurity practice: parameterized queries
# Simulate a safe search using parameterized queries for practice
import mysql.connector

# Establish a database connection (for practice purposes)
cnx = mysql.connector.connect(user='username', password='password', host='localhost', database='dbname')
cursor = cnx.cursor()

# Prepare the query with placeholders
query = "SELECT * FROM users WHERE username LIKE %s"
param = f"%{user_name}%"

# Execute the query with a parameterized statement
cursor.execute(query, (param,))
results = cursor.fetchall()

# Print the results (for practice purposes)
print("Search Results (for practice purposes):")
for row in results:
    print(row)

cursor.close()
cnx.close()
```
