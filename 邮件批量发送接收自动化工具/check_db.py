import sqlite3
conn = sqlite3.connect('web_data/mail_system.db')
rows = conn.execute("SELECT id, status, sender_email, subject FROM inbox_messages ORDER BY id DESC LIMIT 20").fetchall()
print('当前邮件状态：')
for row in rows:
    print(f"  ID: {row[0]}, 状态: {row[1]}, 发件人: {row[2]}, 主题: {row[3][:50]}")
conn.close()
