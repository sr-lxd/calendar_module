# Sofia 年历生成器

Flask 年历网页，支持公历、农历、节日、二十四节气、黄道吉日、个性化节日和多种导出格式。项目可作为 Sofia Blueprint 集成，也可独立运行。

## 本机运行

需要 Python 3.10 或更新版本。

1. 安装依赖：

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. 双击 `启动日历.bat`，或运行：

   ```powershell
   python run_local.py
   ```

浏览器会打开 `http://127.0.0.1:5055/calendar/`。服务只监听本机回环地址，不接受局域网连接。默认端口被占用时，程序会顺延查找 5055–5064 端口。

个性化节日保存在 `instance/calendar_local.sqlite3`。该文件不会提交到 Git。

## 本机 HTTPS 证书

仓库包含 `certs/localhost.crt`。它是自签名开发证书，只适用于 `localhost` 和 `127.0.0.1`，浏览器不会默认信任它。私钥不在仓库中。

如需本机 HTTPS，先运行：

```powershell
python generate_local_cert.py
$env:CALENDAR_HTTPS = "1"
python run_local.py
```

生成的私钥 `certs/localhost.key` 仅保存在本机并被 Git 忽略。未设置 `CALENDAR_HTTPS=1` 时使用 HTTP。

## 功能

- 生成 1900–2100 年的年历，查看农历日期、节日和节气。
- 查看传统建星、黄道吉日及宜忌说明。
- 添加和管理个人节日。
- 导出 HTML、PDF 和 TXT。
- 使用桌面或移动浏览器访问响应式界面。

## Sofia 集成

在 Sofia Flask 应用中注册：

```python
from calendar_module.sofia_integration import register_calendar_blueprint

register_calendar_blueprint(app)
```

Sofia 主程序继续使用其自身的 `extensions.db`。独立运行时，`run_local.py` 使用项目内 SQLite 数据库。

## API

- `GET /calendar/`：年历界面
- `POST /calendar/api/generate`：生成日历数据
- `POST /calendar/api/export/<format>`：导出 `html`、`pdf` 或 `txt`
- `GET /calendar/api/auspicious/<year>/<month>/<day>`：查询吉日信息
- `GET /calendar/api/lunar/<year>/<month>/<day>`：查询农历信息
- `GET /healthz`：本机服务状态

## 技术和检索标签

Python、Flask、SQLite、中文日历、农历、黄历、二十四节气、黄道吉日。

页面包含中文日历相关的标题、摘要和关键词元数据。GitHub 仓库主题标签也用于检索。

## 说明

黄道吉日等传统内容供文化学习参考。农历算法精度和 PDF 字体显示受已安装依赖与本机中文字体影响。第三方前端资源及其许可证见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
