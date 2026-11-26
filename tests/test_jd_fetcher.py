import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ats_analyzer.jd_fetcher import (  # noqa: E402
    JobFetchError,
    fetch_job_description,
    parse_job_html,
)

DESCRIPTION = (
    "<p>We need a <b>Python developer</b> to build REST APIs with Django and FastAPI. "
    "You will design PostgreSQL databases, write tests with pytest, deploy on AWS "
    "using Docker and Kubernetes, and set up CI/CD pipelines for the whole team.</p>"
)

JSON_LD_PAGE = f"""<html><head>
<script type="application/ld+json">{json.dumps({
    "@context": "https://schema.org", "@type": "JobPosting",
    "title": "Backend Engineer", "description": DESCRIPTION,
})}</script></head>
<body><nav>Home | Jobs | Login</nav><p>Cookie banner text</p></body></html>"""

PLAIN_PAGE = f"""<html><body><nav>Menu Links</nav>
<main><h1>Backend Engineer</h1>{DESCRIPTION}</main>
<footer>Copyright footer</footer></body></html>"""


def test_parse_json_ld():
    text = parse_job_html(JSON_LD_PAGE)
    assert text.startswith("Backend Engineer")
    assert "Python developer" in text
    assert "Cookie banner" not in text


def test_parse_json_ld_inside_graph():
    page = JSON_LD_PAGE.replace('"@context"', '"@graph": [{"@type": "JobPosting", "description": "x"}], "@context"')
    assert "Python developer" in parse_job_html(page)


def test_parse_plain_page_uses_main_content():
    text = parse_job_html(PLAIN_PAGE)
    assert "Python developer" in text
    assert "Menu Links" not in text
    assert "Copyright footer" not in text


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        routes = {"/job": (200, JSON_LD_PAGE), "/blocked": (403, "no"), "/empty": (200, "<p>hi</p>")}
        status, body = routes.get(self.path, (404, "missing"))
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def server():
    httpd = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def test_fetch_from_link(server):
    assert "Python developer" in fetch_job_description(f"{server}/job")


@pytest.mark.parametrize("path,message", [
    ("/blocked", "blocked"),
    ("/missing", "HTTP 404"),
    ("/empty", "Couldn't find"),
])
def test_fetch_errors(server, path, message):
    with pytest.raises(JobFetchError, match=message):
        fetch_job_description(server + path)


def test_rejects_non_http_link():
    with pytest.raises(JobFetchError, match="http"):
        fetch_job_description("file:///etc/passwd")
