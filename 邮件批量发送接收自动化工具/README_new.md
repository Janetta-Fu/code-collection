# 外贸邮件自动化管理系统

一套完整的邮件营销和自动化工具，支持**桌面版**和**网页版**两种使用方式。可用于外贸企业进行客户开发、邮件批量发送、收件管理、自动回复等工作。

**主要特性：**
- ✅ 批量邮件发送（支持个性化模板变量）
- ✅ 邮件收件箱同步和管理
- ✅ AI 自动回复或人工批量回复
- ✅ 完整的邮件日志记录
- ✅ 多工作区支持（隔离不同项目/账户）
- ✅ 用户认证和权限管理
- ✅ HTML 邮件模板设计
- ✅ 自定义颜色和品牌标识

---

## 📋 目录

1. [系统要求](#1-系统要求)
2. [快速开始](#2-快速开始)
3. [配置说明](#3-配置说明)
4. [使用指南](#4-使用指南)
5. [功能详情](#5-功能详情)
6. [多工作区](#6-多工作区)
7. [常见问题](#7-常见问题)
8. [脚本说明](#8-脚本说明)

---

## 1. 系统要求

### 最低配置
- **操作系统：** Windows 10 / 11
- **Python 版本：** 3.8 及以上
- **内存：** 2GB+
- **磁盘空间：** 500MB+

### 依赖包

#### 桌面版必需
```bash
pandas
openpyxl
```

#### 网页版完整依赖
```bash
pip install -r requirements-web.txt
```

主要包含：
- `flask` - Web 框架
- `pandas, openpyxl` - Excel 处理
- `werkzeug` - 密码哈希和文件上传

---

## 2. 快速开始

### 方式一：桌面版（GUI）

**最简单的方式，无需命令行操作：**

```bash
python app.py
```

这会打开 Tkinter 图形界面，所有功能通过窗口按钮操作。

### 方式二：网页版（Web）

**支持多用户、远程访问：**

```bash
python web_app.py
```

默认访问地址：`http://localhost:5000`

> **提示：** 网页版支持多用户登录和权限管理，更适合团队使用。

### 方式三：一键启动脚本

**双击运行（无需命令行）：**

- **启动网页版：** 双击 `一键启动网页版.bat`
- **停止网页版：** 双击 `一键停止网页版.bat`
- **启动工作区：** 双击 `run_workspace.bat`

---

## 3. 配置说明

### 第一步：创建配置文件

```bash
# 复制示例配置
copy config.ini.example config.ini
```

### 第二步：编辑配置

用记事本或任何编辑器打开 `config.ini`，按以下内容修改：

#### `[project]` 项目配置
```ini
[project]
name = 你的公司名称
website = https://example.com
products_intro = 我们主要生产和销售...
business_intro_fallback = related products and services
contact_person = John
phone = +1234567890
```

#### `[mail]` 邮箱配置

**关键！这部分最重要**

```ini
[mail]
# SMTP 配置（发送邮件）
smtp_server = smtp.gmail.com          # 发件邮箱服务器
smtp_port = 465
smtp_user = your-email@gmail.com      # 发件邮箱地址
smtp_password = xxxx-xxxx-xxxx-xxxx   # 应用专用密码（不是普通密码！）
smtp_use_ssl = true

# IMAP 配置（收件管理）
imap_server = imap.gmail.com          # 收件邮箱服务器
imap_port = 993
imap_user = your-email@gmail.com
imap_password = xxxx-xxxx-xxxx-xxxx
```

**获取应用密码的方法：**

| 邮箱服务商 | 获取方法 |
|----------|--------|
| **Gmail** | 在 https://myaccount.google.com/apppasswords 中生成16位应用密码 |
| **Outlook** | 进入 https://account.microsoft.com/security-info 启用应用密码 |
| **企业邮箱** | 咨询邮箱提供商客服获取授权码 |

#### `[runtime]` 运行参数
```ini
[runtime]
interval = 5              # 每封邮件间隔（秒）
max_batch_size = 100      # 单次批量发送最多数量
inbox_days = 7            # 收件箱查询过去多少天的邮件
```

#### `[templates]` 邮件模板

```ini
[templates]
subject = Hi {company_name}, we are your ideal supplier
body = Dear {contact_person},

I am reaching out because I believe your company {company_name} might be interested in our {product_advantages}.

We specialize in {business_intro}.

Best regards,
{project_name}
Website: {project_website}
```

### 模板变量参考

在邮件主题和正文中使用 `{变量名}` 的格式。系统会从 Excel 表格中自动替换：

| 变量名 | 说明 | 来源 |
|-------|------|------|
| `{company_name}` | 公司名称 | Excel 必填列 |
| `{email}` | 邮箱地址 | Excel 必填列 |
| `{contact_person}` | 联系人名称 | 从 Excel 公司名称中提取 |
| `{business_intro}` | 业务介绍 | Excel 可选列（为空时用 fallback） |
| `{phone}` | 联系电话 | Excel 可选列 |
| `{website}` | 官网地址 | Excel 可选列 |
| `{country}` | 所在国家 | Excel 可选列 |
| `{city}` | 所在城市 | Excel 可选列 |
| `{project_name}` | 项目名称 | 配置文件 |
| `{project_website}` | 项目网站 | 配置文件 |
| `{product_advantages}` | 产品优势 | 配置文件 |

---

## 4. 使用指南

### 4.1 准备客户数据

**创建 Excel 文件，包含以下列（大小写敏感）：**

| 公司名称 | 邮箱 | 业务介绍 | 联系电话 | 官网地址 | 所在国家 | 所在城市 |
|---------|------|--------|--------|--------|--------|--------|
| ABC Trading | abc@example.com | Import/Export | +1234567890 | abc.com | USA | New York |
| XYZ Corp | info@xyz.com | Manufacturing | | xyz.com | Germany | Berlin |

**必填列：**
- `公司名称`
- `邮箱`

**可选列：** 业务介绍、联系电话、官网地址、所在国家、所在城市（若无此列，自动填充默认值）

### 4.2 发送邮件流程

#### 桌面版：
1. 启动 `app.py`
2. 设置好配置文件，点击"重新加载配置"
3. 点击"导入客户"，选择 Excel 文件
4. 点击"预览首封"验证模板效果
5. 点击"开始发送"，开始批量发送
6. 实时显示发送进度和日志

#### 网页版：
1. 启动 `web_app.py`，访问 `http://localhost:5000`
2. 用管理员账号登录
3. 进入 **设置** 页面配置邮箱和模板
4. 点击 **发送** 选项卡
5. 上传 Excel 文件
6. 预览首封邮件
7. 点击"开始发送"

### 4.3 查看和回复邮件

#### 收件箱功能（网页版）
1. 点击 **收件箱** 选项卡
2. 点击"获取邮件"，系统会从 IMAP 服务器同步邮件
3. 邮件按时间倒序显示
4. 点击邮件可查看完整内容

#### 邮件回复
- **自动回复：** 使用 AI 自动生成回复内容（需配置）
- **人工回复：** 选中邮件，手工编辑并发送
- **批量回复：** 选中多封邮件，统一回复内容

---

## 5. 功能详情

### 5.1 批量发送邮件

**特性：**
- 支持 HTML 和纯文本两种格式
- 自动个性化替换模板变量
- 发送失败自动重试
- 实时进度条和日志
- 完整的发送记录保存

**输出文件：**
- `sent_log.csv` - 详细的发送日志（时间、收件人、状态、错误信息）
- `sent_emails.txt` - 已发送邮箱列表
- `reply_history.csv` - 回复历史记录

### 5.2 邮件模板

支持 **HTML 格式邮件**，可自定义：
- 页眉颜色
- 页脚背景色和文字色
- 自定义公司 Logo（上传图片）

**邮件格式选项：**
- HTML + 纯文本（双份发送，兼容所有邮箱）
- 纯 HTML 格式
- 纯文本格式

### 5.3 邮件收件箱

- 自动同步 IMAP 收件箱
- 支持指定查询天数（默认7天）
- 显示邮件发件人、主题、时间
- 查看完整邮件内容（含附件）

### 5.4 自动回复（AI 驱动）

- 自动分析来信内容
- 生成专业回复
- 支持批量确认后一键发送
- 避免误发，提供人工审核环节

### 5.5 日志管理

系统记录所有操作：
- **发送日志** - 每封邮件是否成功
- **回复日志** - 所有回复的发送记录
- **错误日志** - SMTP/IMAP 连接错误
- 支持日志导出和分析

---

## 6. 多工作区

支持为不同项目/客户创建独立的工作区，完全隔离数据和配置。

### 工作区结构

```
workspaces/
├── default/              # 默认工作区
│   ├── config.ini       # 独立配置
│   ├── app_data/        # 数据文件
│   └── web_data/        # 上传文件
├── codex_test/          # 测试工作区
│   ├── config.ini
│   ├── app_data/
│   └── web_data/
└── demoA/               # 演示工作区
    ├── config.ini
    └── ...
```

### 启动不同工作区

**使用工作区启动器脚本：**

```bash
# 通过环境变量指定工作区
set MAIL_WORKSPACE_DIR=c:\path\to\workspaces\codex_test
python web_app.py
```

**或编辑批处理文件 `workspace_launcher.ps1`：**

```powershell
$env:MAIL_WORKSPACE_DIR = ".\workspaces\codex_test"
python web_app.py
```

### 多工作区优势

- 🔒 数据完全隔离
- 📊 独立的邮件日志
- ⚙️ 独立的配置文件
- 👥 多个团队/项目并行运行

---

## 7. 常见问题

### Q: 如何获取 Gmail 的应用密码？
**A:** 
1. 访问 https://myaccount.google.com/apppasswords
2. 选择"邮件"和"Windows 电脑"
3. Google 会生成一个16位密码
4. 复制粘贴到 `config.ini` 中的 `smtp_password` 字段

### Q: 发送卡住了怎么办？
**A:** 
- 检查网络连接
- 验证 SMTP 服务器地址和端口
- 确认邮箱授权码正确（不是普通密码！）
- 查看控制台错误信息
- 尝试降低 `interval` 值

### Q: 可以发送附件吗？
**A:** 当前版本不支持附件。可在邮件正文中添加下载链接。

### Q: 如何跳过已发送的邮箱？
**A:** 系统会自动检查 `sent_emails.txt` 文件，避免重复发送。

### Q: 网页版支持多人同时操作吗？
**A:** 是的！网页版支持多用户登录，每个用户有独立的配置和操作日志。

### Q: 如何导出发送记录？
**A:** 发送完成后，`sent_log.csv` 自动保存在 `app_data` 文件夹中，可用 Excel 打开分析。

---

## 8. 脚本说明

| 脚本文件 | 用途 |
|---------|------|
| `app.py` | 启动桌面版图形界面 |
| `web_app.py` | 启动网页版服务器 |
| `check_db.py` | 检查数据库完整性 |
| `check_reply_logs.py` | 检查回复日志 |
| `reset_status.py` | 重置发送状态（用于重新发送） |
| `fix_specific.py` | 修复特定客户的邮件状态 |
| `一键启动网页版.bat` | 双击启动网页版（无需命令行） |
| `一键停止网页版.bat` | 双击停止网页版 |
| `run_workspace.bat` | 启动默认工作区 |
| `workspace_launcher.ps1` | 工作区启动管理脚本 |
| `workspace_supervisor.ps1` | 后台监督脚本 |

### 使用这些脚本：

```bash
# 检查数据库状态
python check_db.py

# 重置某个客户的发送状态
python fix_specific.py --email customer@example.com --status pending

# 检查回复日志
python check_reply_logs.py
```

---

## 📝 建议和最佳实践

### 发送前准备
1. ✅ **先做小规模测试** - 用 5-10 个测试客户验证配置
2. ✅ **预览邮件** - 务必点击"预览首封"检查模板是否正确
3. ✅ **备份数据** - 发送前备份 Excel 文件和数据

### 发送过程
1. ✅ **选择合适的间隔时间** - 间隔过短可能被邮箱服务商限流
2. ✅ **避免重复发送** - 系统自动追踪已发送邮箱
3. ✅ **监视日志** - 定期查看发送日志，排查失败原因

### 后期跟进
1. ✅ **定期检查收件** - 每天查看"收件箱"中的客户回复
2. ✅ **整理回复日志** - 标记已处理的邮件
3. ✅ **导出统计** - 导出 `sent_log.csv` 进行分析

---

## 🔐 安全提示

- ⚠️ **永远不要**在代码中硬编码真实的邮箱密码
- ⚠️ 使用**应用专用密码**（不是普通登录密码）
- ⚠️ **不要上传** `config.ini` 到公开仓库（已配置 `.gitignore`）
- ⚠️ 定期修改邮箱密码
- ⚠️ 启用二步认证

---

## 📞 支持和反馈

遇到问题？请检查：
1. 是否正确复制了 `config.ini.example` 到 `config.ini`
2. 邮箱授权码是否正确（不是普通密码）
3. 网络连接是否正常
4. Excel 文件是否有 `公司名称` 和 `邮箱` 两列

祝你使用愉快！ 🚀
