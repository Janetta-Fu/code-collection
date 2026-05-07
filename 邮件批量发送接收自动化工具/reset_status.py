import sqlite3
conn = sqlite3.connect('web_data/mail_system.db')

# 查看当前所有的"已回复"邮件（可能是错误的）
print("=== 重置前的数据 ===")
rows = conn.execute("""
SELECT id, status, sender_email, subject FROM inbox_messages 
WHERE status IN ('无明确业务内容', '系统自动回复', '广告垃圾邮件', '空内容/仅签名客套', '同会话旧邮件')
ORDER BY id DESC LIMIT 10
""").fetchall()
print(f"需要重置的邮件数：{len(rows)}")
for row in rows[:5]:
    print(f"  ID: {row[0]}, 当前状态: {row[1]}, 发件人: {row[2]}")

# 重置所有错误标记的邮件
conn.execute("""
UPDATE inbox_messages 
SET status = '待回复'
WHERE status IN ('无明确业务内容', '系统自动回复', '广告垃圾邮件', '空内容/仅签名客套', '同会话旧邮件')
""")

print("\n=== 重置完成 ===")
conn.commit()

# 验证
rows2 = conn.execute("""
SELECT COUNT(*) FROM inbox_messages WHERE status = '待回复'
""").fetchone()
print(f"现在有 {rows2[0]} 封待回复邮件")

conn.close()
