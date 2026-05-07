import sqlite3
conn = sqlite3.connect('web_data/mail_system.db')

# 查看对应的回复日志
rows = conn.execute("""
SELECT id, status, subject, created_at FROM sent_logs 
WHERE recipient = 'test@example.com' 
AND status = '自动回复成功'
ORDER BY id DESC LIMIT 5
""").fetchall()

print('回复日志：')
for row in rows:
    print(f"  ID: {row[0]}, 状态: {row[1]}, 主题: {row[2][:50]}, 时间: {row[3]}")

# 查看是否有对应的已回复标记
rows2 = conn.execute("""
SELECT id, message_key FROM replied_messages 
WHERE user_id = 1
ORDER BY id DESC LIMIT 5
""").fetchall()

print('\n已回复标记：')
for row in rows2:
    print(f"  ID: {row[0]}, message_key: {row[1]}")

conn.close()
