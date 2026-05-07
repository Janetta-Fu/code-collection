# 最简单多人网页版

这是给现有 `okki_trade_automation.py` 包的一层最小 Web 版。

## 功能

- 多用户登录
- 网页免登录：每台电脑/每个浏览器自动分配本地使用人
- 每个本地使用人只能看到自己的任务
- 多人可同时提交任务
- 后台线程执行采集，不阻塞网页
- 每个任务独立 Chrome 资料目录、导出目录、增量状态文件
- 支持查看任务进度、日志、下载 Excel/HTML
- 支持停止正在运行的任务
- 每个任务可手动填写 OKKI 账号、密码、Cookie、智能贸易数据 URL

## 安装

```bash
pip install -r simple_web/requirements_web.txt
```

## 启动

```bash
simple_web\run_web.bat
```

或：

```bash
python -m uvicorn simple_web.web_app:app --host 0.0.0.0 --port 8000
```

局域网访问：

```text
http://本机IP:8000
```
