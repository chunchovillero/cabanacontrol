"""HTTPS, session, CSRF, tenant isolation, private media and fictional mail rehearsal."""

import argparse
import json
import re
import ssl
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="cabanacontrol-pcheck")
    parser.add_argument("--reset-mail", action="store_true")
    parser.add_argument("--docker-config")
    parser.add_argument("--docker-host")
    args = parser.parse_args()
    if not re.fullmatch(r"cabanacontrol-p(?:check|restore)-?[a-z0-9]*", args.project):
        raise SystemExit("Solo proyectos ficticios P.")
    context = ssl.create_default_context(
        cafile=str(ROOT / ".local-production/tls/server.crt")
    )
    base = "https://localhost:25443"
    with httpx.Client(
        verify=context, base_url=base, timeout=15, trust_env=False
    ) as anonymous:
        assert anonymous.get("/health/").json() == {"status": "ok", "database": "ok"}
        front = anonymous.get("/reservas")
        assert front.status_code == 200 and '<div id="root">' in front.text
        assets = re.findall(r'(?:src|href)="(/assets/[^\"]+)"', front.text)
        assert assets and all(
            anonymous.get(asset).status_code == 200 for asset in assets
        )
        assert anonymous.get("/media/private.png").status_code == 404
        assert anonymous.get("/.env").status_code == 404
        assert anonymous.get("/api/v1/properties/").status_code == 403
        assert anonymous.post("/api/v1/auth/login/", json={}).status_code == 403
        spoof = anonymous.get("/health/", headers={"X-Forwarded-Proto": "http"})
        assert spoof.status_code == 200
        assert "max-age=3600" in spoof.headers["strict-transport-security"]
        assert spoof.headers["x-content-type-options"] == "nosniff"
    with httpx.Client(timeout=15, trust_env=False) as plain:
        response = plain.get("http://localhost:25080/ingresar")
        assert (
            response.status_code == 308
            and response.headers["location"] == base + "/ingresar"
        )
    clients = []
    resources = []
    try:
        for suffix in ("a", "b"):
            client = httpx.Client(
                verify=context,
                base_url=base,
                timeout=15,
                trust_env=False,
                headers={"Origin": base},
            )
            clients.append(client)
            csrf = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
            response = client.post(
                "/api/v1/auth/login/",
                headers={"X-CSRFToken": csrf},
                json={
                    "email": f"p-owner-{suffix}@example.invalid",
                    "password": "P-fictional-passphrase-2026!",
                },
            )
            assert response.status_code == 200
            cookies = response.headers.get_list("set-cookie")
            assert any(
                "sessionid=" in c and "Secure" in c and "HttpOnly" in c for c in cookies
            )
            csrf = client.cookies["csrftoken"]
            client.headers.update({"X-CSRFToken": csrf, "Origin": base})
            tenant = client.get("/api/v1/tenants/").json()["results"][0]["id"]
            assert client.post(f"/api/v1/tenants/{tenant}/select/").status_code == 200
            client.headers["X-Tenant-Context"] = tenant
            cabin = client.get("/api/v1/properties/").json()["results"][0]
            photo = client.get(f"/api/v1/properties/{cabin['id']}/photos/").json()[0]
            file_path = f"/api/v1/properties/{cabin['id']}/photos/{photo['id']}/file/"
            image = client.get(file_path)
            assert image.status_code == 200 and image.content.startswith(b"\x89PNG")
            reservations = client.get("/api/v1/reservations/").json()["results"]
            assert len(reservations) == 1
            assert str(reservations[0]["total_amount"]) == "100000.00"
            resources.append((tenant, cabin["id"], file_path))
        assert (
            clients[0].get(f"/api/v1/properties/{resources[1][1]}/").status_code == 404
        )
        assert clients[0].get(resources[1][2]).status_code == 404
        assert (
            clients[0].post(f"/api/v1/tenants/{resources[1][0]}/select/").status_code
            == 404
        )
        headers = {"X-Tenant-Context": resources[1][0]}
        assert (
            clients[0]
            .patch(
                f"/api/v1/properties/{resources[0][1]}/",
                headers=headers,
                json={"name": "Must not change"},
            )
            .status_code
            == 409
        )
        assert (
            clients[0]
            .post("/api/v1/auth/logout/", headers={"Origin": "https://evil.invalid"})
            .status_code
            == 403
        )
        if args.reset_mail:
            assert (
                clients[0]
                .post(
                    "/api/v1/auth/password-reset/",
                    json={"email": "p-owner-a@example.invalid"},
                )
                .status_code
                == 200
            )
            docker = ["docker"]
            if args.docker_config:
                docker += ["--config", args.docker_config]
            if args.docker_host:
                docker += ["--host", args.docker_host]
            command = docker + [
                "compose",
                "--env-file",
                ".local-production/rehearsal.env",
                "-p",
                args.project,
                "-f",
                "compose.production.yaml",
                "exec",
                "-T",
                "backend",
                "python",
                "-c",
                (
                    "from pathlib import Path; import json; "
                    "print(json.dumps([p.read_text() for p in Path('/tmp/p-rehearsal-emails').glob('*')]))"
                ),
            ]
            result = subprocess.run(command, cwd=ROOT, capture_output=True, check=True)
            mail = json.loads(result.stdout)[-1]
            assert "p-owner-a@example.invalid" in mail
            link = re.search(
                r"https://localhost:25443/restablecer#[^\s]+", mail
            ).group()
            params = parse_qs(urlsplit(link).fragment)
            data = {
                "uid": params["uid"][0],
                "token": params["token"][0],
                "password": "P-new-fictional-passphrase-2026!",
            }
            assert (
                clients[0]
                .post("/api/v1/auth/password-reset/confirm/", json=data)
                .status_code
                == 200
            )
            assert (
                clients[0]
                .post("/api/v1/auth/password-reset/confirm/", json=data)
                .status_code
                == 400
            )
            csrf = clients[0].get("/api/v1/auth/csrf/").json()["csrf_token"]
            assert (
                clients[0]
                .post(
                    "/api/v1/auth/login/",
                    headers={"X-CSRFToken": csrf},
                    json={
                        "email": "p-owner-a@example.invalid",
                        "password": data["password"],
                    },
                )
                .status_code
                == 200
            )
            # Only the fictional account's password changes; no real users are involved.
        print(
            json.dumps(
                {
                    "https": "verified with local certificate",
                    "csrf": "passed",
                    "tenant_isolation": "passed",
                    "private_media": "passed",
                    "mail_reset": "passed" if args.reset_mail else "not requested",
                }
            )
        )
    finally:
        for client in clients:
            client.close()


if __name__ == "__main__":
    main()
