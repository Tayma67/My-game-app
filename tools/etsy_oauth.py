#!/usr/bin/env python3
"""Etsy OAuth 2.0 (PKCE) helper — does the hard part so a non-coder doesn't have to.

Two steps:

  1) START — generate the login link:
       python3 tools/etsy_oauth.py start --api-key YOUR_KEYSTRING \
           --redirect-uri https://www.google.com
     Open the printed URL, log in to Etsy, click "Allow". Your browser will
     land on the redirect URL with "?code=...&state=..." in the address bar.
     Copy that WHOLE address.

  2) FINISH — exchange it for a token:
       python3 tools/etsy_oauth.py finish --api-key YOUR_KEYSTRING \
           --redirect-uri https://www.google.com \
           --redirect-url "PASTE_THE_WHOLE_ADDRESS_HERE"
     Prints your access_token, refresh_token, and shop_id.

The PKCE code_verifier is stored in a gitignored temp file between the two
steps. Nothing secret is committed.
"""
import argparse, base64, hashlib, json, os, secrets, sys, urllib.parse

VERIFIER_FILE = "/tmp/.etsy_pkce_verifier"
SCOPES = "listings_r listings_w shops_r"


def b64url(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def start(a):
    verifier = b64url(secrets.token_bytes(48))
    challenge = b64url(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_hex(8)
    open(VERIFIER_FILE, "w").write(json.dumps({"verifier": verifier, "state": state}))
    params = {
        "response_type": "code",
        "client_id": a.api_key,
        "redirect_uri": a.redirect_uri,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    url = "https://www.etsy.com/oauth/connect?" + urllib.parse.urlencode(params)
    print("\n1) Open this URL, log in, and click Allow:\n")
    print(url)
    print("\n2) After approving, copy the FULL address bar URL and run `finish`.\n")


def finish(a):
    import requests
    saved = json.load(open(VERIFIER_FILE))
    q = urllib.parse.parse_qs(urllib.parse.urlparse(a.redirect_url).query)
    code = q.get("code", [None])[0]
    state = q.get("state", [None])[0]
    if not code:
        sys.exit("No ?code= found in the URL you pasted.")
    if state != saved["state"]:
        sys.exit("State mismatch — re-run `start` and try again.")
    r = requests.post("https://api.etsy.com/v3/public/oauth/token", data={
        "grant_type": "authorization_code",
        "client_id": a.api_key,
        "redirect_uri": a.redirect_uri,
        "code": code,
        "code_verifier": saved["verifier"],
    }, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Token exchange failed: {r.status_code} {r.text[:400]}")
    tok = r.json()
    access = tok["access_token"]
    refresh = tok.get("refresh_token", "")
    # access_token is "{user_id}.{...}" — derive shop id
    user_id = access.split(".")[0]
    H = {"x-api-key": a.api_key, "Authorization": f"Bearer {access}"}
    shop_id = ""
    try:
        s = requests.get(f"https://api.etsy.com/v3/application/users/{user_id}/shops",
                         headers=H, timeout=30)
        if s.status_code == 200:
            d = s.json()
            shop_id = d.get("shop_id") or (d.get("results", [{}])[0].get("shop_id", ""))
    except Exception:
        pass
    print("\n=== SUCCESS — credentials ===")
    print("ETSY_API_KEY     =", a.api_key)
    print("ETSY_OAUTH_TOKEN =", access)
    print("ETSY_SHOP_ID     =", shop_id or "(couldn't auto-detect — tell me your shop name)")
    print("REFRESH_TOKEN    =", refresh, "(keeps us able to refresh the 1h token)")
    print("\nAccess token expires in ~1 hour — run the publish step soon.")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("start", "finish"):
        s = sub.add_parser(name)
        s.add_argument("--api-key", required=True)
        s.add_argument("--redirect-uri", default="https://www.google.com")
        if name == "finish":
            s.add_argument("--redirect-url", required=True)
    a = ap.parse_args()
    (start if a.cmd == "start" else finish)(a)


if __name__ == "__main__":
    main()
