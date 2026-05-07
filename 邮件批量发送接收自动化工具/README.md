<<<<<<< HEAD
# 外贸邮件自动化发送系统

这是一个基于 `Python + Tkinter + pandas + openpyxl` 的桌面工具，用于：

- 导入 Excel 客户数据
- 根据项目配置自动生成个性化开发信
- 批量发送邮件并显示进度日志
- 查看最近收件箱邮件

## 1. 环境要求

- Windows 10 / 11
- Python 3.8+
- 已安装依赖：

```bash
pip install pandas openpyxl
```

## 2. 配置方式

1. 将 `config.ini.example` 复制为 `config.ini`
2. 修改以下内容：

- `[project]`：项目名称、官网、产品优势
- `[mail]`：发件邮箱、授权码、SMTP / IMAP 信息
- `[runtime]`：每封邮件发送间隔
- `[templates]`：邮件主题和正文模板

模板变量支持：

- `{company_name}`
- `{email}`
- `{business_intro}`
- `{phone}`
- `{website}`
- `{country}`
- `{city}`
- `{project_name}`
- `{project_website}`
- `{product_advantages}`

## 3. Excel 列要求

至少包含以下两列：

- `公司名称`
- `邮箱`

可选列：

- `业务介绍`
- `联系电话`
- `官网地址`
- `所在国家`
- `所在城市`

如果 `业务介绍` 为空，系统会自动填充 `related products and services`。

## 4. 启动方式

```bash
python app.py
```

## 5. 当前功能

- 项目配置热加载
- Excel 导入与字段识别
- 首封邮件预览
- 批量发送与进度条
- 成功 / 失败 / 跳过日志
- IMAP 最近 20 封邮件查看

## 6. 建议

- 首次使用前，先用少量测试客户验证模板内容和邮箱配置
- 批量发送前，先点击“预览首封邮件”
- 请勿把真实授权码提交到代码仓库
=======
# code-collection
自动化 &amp; AI 工具脚本
>>>>>>> 20aec00d66ae9ce1a1e1459d71efc43037c77f46
