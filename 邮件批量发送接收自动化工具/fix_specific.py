import sqlite3
conn = sqlite3.connect('web_data/mail_system.db')

# Check marked as replied
rows = conn.execute("""
SELECT id, status, sender_email, subject FROM inbox_messages 
WHERE id IN (315, 316)
""").fetchall()
print('Emails to fix:')
for row in rows:
    print(f"  ID: {row[0]}, Status: {row[1]}, From: {row[2]}")

# Reset to pending reply
conn.execute("UPDATE inbox_messages SET status = ? WHERE id IN (315, 316)", ('待回复',))
conn.commit()

print('Fixed - set status to pending reply')
conn.close()
