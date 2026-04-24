"""Upload locally-trained ML artifacts to the deployed backend.

Reads joblibs from ``backend/app/ml/artifacts/`` (the output of
``python -m scripts.train_ml``) and POSTs each to
``POST /ml/artifacts/{name}`` on the deployed API.

Usage:
    python -m scripts.push_ml                                    # all three
    python -m scripts.push_ml clv churn                          # subset
    API_URL=http://localhost:8000 python -m scripts.push_ml      # other target

Auth: set API_EMAIL / API_PASSWORD in the environment and the script will
log in to get a JWT. Or set ML_API_TOKEN directly to skip login.
"""

from __future__ import annotations

import argparse
import os
import sys
import urllib.parse
import urllib.request

from app.ml.persistence import artifact_path

DEFAULT_API_URL = "https://adh2-api-cecfxb.azurewebsites.net"
VALID_NAMES = ("clv", "churn", "basket")


def _api_url() -> str:
    return os.environ.get("API_URL", DEFAULT_API_URL).rstrip("/")


def _login() -> str:
    """Exchange email+password for a bearer token via /auth/login."""
    token = os.environ.get("ML_API_TOKEN")
    if token:
        return token

    email = os.environ.get("API_EMAIL")
    password = os.environ.get("API_PASSWORD")
    if not email or not password:
        print(
            "Set ML_API_TOKEN, or API_EMAIL + API_PASSWORD, in the environment.",
            file=sys.stderr,
        )
        sys.exit(2)

    import json

    body = json.dumps({"email": email, "password": password}).encode()
    req = urllib.request.Request(
        f"{_api_url()}/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read())
    return payload["access_token"]


def _push(name: str, token: str) -> None:
    path = artifact_path(name)
    if not path.exists():
        print(f"[{name}] no artifact at {path}. Run train_ml first.", file=sys.stderr)
        sys.exit(1)

    boundary = "----mlpushboundary-" + os.urandom(8).hex()
    body_head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{name}.joblib"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    body_tail = f"\r\n--{boundary}--\r\n".encode()
    body = body_head + path.read_bytes() + body_tail

    url = f"{_api_url()}/ml/artifacts/{urllib.parse.quote(name)}"
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Bearer {token}",
            "Content-Length": str(len(body)),
        },
    )
    size_mb = len(body) / (1024 * 1024)
    print(f"[{name}] uploading {size_mb:.1f} MB -> {url}")
    with urllib.request.urlopen(req, timeout=300) as resp:
        print(f"[{name}] {resp.status} {resp.read().decode()[:200]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("models", nargs="*", default=[], help="Subset; default = all")
    args = parser.parse_args()

    names = args.models or list(VALID_NAMES)
    bad = [n for n in names if n not in VALID_NAMES]
    if bad:
        print(f"Unknown model(s): {bad}. Valid: {list(VALID_NAMES)}", file=sys.stderr)
        return 2

    token = _login()
    for name in names:
        _push(name, token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
