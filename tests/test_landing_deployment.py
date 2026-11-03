"""Exercise the production landing routing rules without TLS or an API."""

import getpass
import http.client
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def landing_server(tmp_path_factory):
    if not shutil.which("nginx"):
        pytest.skip("nginx is required for deployment checks")
    if not (ROOT / "frontend/dist/sitemap.xml").exists():
        pytest.skip("Run the production frontend build first")
    directory = tmp_path_factory.mktemp("landing-nginx")
    dist = directory / "dist"
    shutil.copytree(ROOT / "frontend/dist", dist)
    source = (ROOT / "scripts/castle-celestial.nginx.conf").read_text()
    source = source.split("\n# ─── HTTP to HTTPS Redirect")[0]
    source = re.sub(
        r"^\s*(?:listen|ssl_\w+|resolver|resolver_timeout|access_log|error_log)\s+.*?;\s*$",
        "", source, flags=re.M,
    )
    source = source.replace("root /home/deployuser/dist;", f"root {dist};")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    source = source.replace("server {", f"server {{\nlisten 127.0.0.1:{port};", 1)
    configuration = directory / "nginx.conf"
    configuration.write_text(f"""
user {getpass.getuser()};
error_log stderr;
pid {directory}/nginx.pid;
events {{}}
http {{
include /etc/nginx/mime.types;
access_log off;
{source}
}}
""")
    subprocess.run(["nginx", "-t", "-c", str(configuration)], check=True)
    process = subprocess.Popen(["nginx", "-c", str(configuration), "-g", "daemon off;"])

    def request(path, host="castlecelestialview.net"):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            connection.request("GET", path, headers={"Host": host})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    try:
        for _ in range(50):
            if process.poll() is not None:
                raise RuntimeError("nginx exited during startup")
            try:
                assert request("/en-GB/")[0] == 200
                break
            except ConnectionRefusedError:
                time.sleep(0.1)
        else:
            raise RuntimeError("nginx startup timed out")
        yield request, dist
    finally:
        process.terminate()
        process.wait(timeout=10)


def assert_security_headers(headers):
    for name in (
        "Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options",
        "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy",
    ):
        assert name in headers


@pytest.mark.parametrize("locale", ["en-GB", "en-US"])
@pytest.mark.parametrize("route", ["/", "/events", "/about"])
def test_regional_documents(landing_server, locale, route):
    request, _ = landing_server
    path = f"/{locale}{route}"
    status, headers, body = request(f"{path}?source=search")
    assert status == 200
    assert headers["Content-Type"] == "text/html"
    assert headers["Cache-Control"] == "public, max-age=0, must-revalidate"
    assert_security_headers(headers)
    html = body.decode()
    assert f'<html lang="{locale}">' in html
    assert f'<link rel="canonical" href="https://castlecelestialview.net{path}">' in html
    assert f'<meta property="og:url" content="https://castlecelestialview.net{path}">' in html
    assert '<meta name="twitter:card" content="summary_large_image">' in html


@pytest.mark.parametrize(("path", "target"), [
    ("/", "/en-GB/"),
    ("/index.html", "/en-GB/"),
    ("/en-GB", "/en-GB/"),
    ("/en-gb/", "/en-GB/"),
    ("/en-us", "/en-US/"),
    ("/EN-us/index.html", "/en-US/"),
    ("/en-UK/events", "/en-GB/events"),
    ("/en-uk/events/", "/en-GB/events"),
    ("/EN-gb/EVENTS", "/en-GB/events"),
    ("/en-US/events/", "/en-US/events"),
    ("/en-US/events.html", "/en-US/events"),
    ("/en-GB/about/", "/en-GB/about"),
    ("/en-US/ABOUT.html", "/en-US/about"),
    ("/en-UK/saved/path", "/en-GB/saved/path"),
])
def test_canonical_redirects_preserve_queries(landing_server, path, target):
    request, _ = landing_server
    status, headers, _ = request(f"{path}?source=search&date=2026-11-03")
    assert status == 301
    assert headers["Location"] == f"https://castlecelestialview.net{target}?source=search&date=2026-11-03"


def test_https_www_redirect(landing_server):
    request, _ = landing_server
    status, headers, _ = request("/en-US/events?source=share", "www.castlecelestialview.net")
    assert status == 301
    assert headers["Location"] == "https://castlecelestialview.net/en-US/events?source=share"


def test_real_discovery_files_and_images(landing_server):
    request, _ = landing_server
    status, headers, body = request("/robots.txt")
    assert status == 200
    assert headers["Content-Type"] == "text/plain"
    assert "no-cache" in headers["Cache-Control"]
    assert_security_headers(headers)
    assert b"Sitemap: https://castlecelestialview.net/sitemap.xml" in body
    status, headers, body = request("/sitemap.xml")
    assert status == 200
    assert "xml" in headers["Content-Type"]
    assert "no-cache" in headers["Cache-Control"]
    assert_security_headers(headers)
    entries = ET.fromstring(body).findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url")
    assert len(entries) == 4
    for name in ("home", "events"):
        status, headers, body = request(f"/social/{name}-v1.png")
        assert status == 200
        assert headers["Content-Type"] == "image/png"
        assert "max-age=31536000" in headers["Cache-Control"]
        assert_security_headers(headers)
        assert body[:8] == b"\x89PNG\r\n\x1a\n"
        assert int.from_bytes(body[16:20], "big") == 1200
        assert int.from_bytes(body[20:24], "big") == 630


def test_missing_discovery_assets_never_return_spa_html(landing_server):
    request, dist = landing_server
    for path in ("/robots.txt", "/sitemap.xml"):
        asset = dist / path.lstrip("/")
        content = asset.read_bytes()
        try:
            asset.unlink()
            status, headers, body = request(path)
            assert status == 404
            assert b"static-landing" not in body
            assert_security_headers(headers)
        finally:
            asset.write_bytes(content)
    status, headers, body = request("/social/missing.png")
    assert status == 404
    assert b"static-landing" not in body
    assert_security_headers(headers)
