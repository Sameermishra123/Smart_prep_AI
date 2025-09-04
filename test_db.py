# test_db.py
import sqlite3

conn = sqlite3.connect("studyai.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM users")
users = cursor.fetchall()

print("Users in database:")
for user in users:
    print(f"ID: {user[0]}, Username: {user[1]}, Email: {user[2]}")

conn.close()
