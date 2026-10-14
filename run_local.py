"""Run the calendar module as a local-only web application."""

from __future__ import annotations

import os
import importlib.util
from pathlib import Path
import secrets
import socket
import sys
from threading import Timer
import webbrowser

from flask import Flask, redirect, url_for


PROJECT_ROOT = Path(__file__).resolve().parent
INSTANCE_DIR = PROJECT_ROOT / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)
sys.path.insert(0, str(PROJECT_ROOT))

# The existing Blueprint expects Sofia's top-level `extensions.db`.
# Provide an isolated SQLAlchemy instance for this standalone process.
import standalone_extensions
sys.modules["extensions"] = standalone_extensions

package_spec = importlib.util.spec_from_file_location(
    "calendar_module",
    PROJECT_ROOT / "__init__.py",
    submodule_search_locations=[str(PROJECT_ROOT)],
)
if package_spec is None or package_spec.loader is None:
    raise RuntimeError("Unable to load the calendar module package")
calendar_module = importlib.util.module_from_spec(package_spec)
sys.modules["calendar_module"] = calendar_module
package_spec.loader.exec_module(calendar_module)
calendar_bp = calendar_module.calendar_bp
from calendar_module.routes import init_database


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"sqlite:///{(INSTANCE_DIR / 'calendar_local.sqlite3').as_posix()}"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    secret_path = INSTANCE_DIR / "secret_key"
    if not secret_path.exists():
        secret_path.write_text(secrets.token_hex(32), encoding="ascii")
    app.config["SECRET_KEY"] = secret_path.read_text(encoding="ascii").strip()

    standalone_extensions.db.init_app(app)
    app.register_blueprint(calendar_bp)

    @app.get("/")
    def home():
        return redirect(url_for("calendar.index"))

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "service": "calendar_module"}

    with app.app_context():
        init_database()
    return app


def choose_port() -> int:
    requested = int(os.environ.get("CALENDAR_PORT", "5055"))
    for port in range(requested, min(requested + 10, 65536)):
        with socket.socket() as probe:
            try:
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("No available local port in the requested range")


def main() -> None:
    port = choose_port()
    use_https = os.environ.get("CALENDAR_HTTPS", "").lower() in {"1", "true", "yes"}
    cert_file = PROJECT_ROOT / "certs" / "localhost.crt"
    key_file = PROJECT_ROOT / "certs" / "localhost.key"
    ssl_context = None
    scheme = "http"
    if use_https:
        if not cert_file.is_file() or not key_file.is_file():
            raise SystemExit("HTTPS certificate files are missing. Run generate_local_cert.py first.")
        ssl_context = (str(cert_file), str(key_file))
        scheme = "https"

    url = f"{scheme}://127.0.0.1:{port}/calendar/"
    print(f"Calendar is available at {url}")
    print("Listening on 127.0.0.1 only. Press Ctrl+C to stop.")
    if os.environ.get("CALENDAR_NO_BROWSER") != "1":
        Timer(1.0, webbrowser.open, args=(url,)).start()
    create_app().run(host="127.0.0.1", port=port, debug=False,
                     use_reloader=False, ssl_context=ssl_context)


if __name__ == "__main__":
    main()
