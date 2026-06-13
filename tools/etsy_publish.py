#!/usr/bin/env python3
"""Create Etsy digital-download listings programmatically from our product
catalog. This is the "I do the rest" engine: after you (one time) register an
Etsy app, get an API key, and authorize via OAuth, this script creates all
listings — images + digital file + title + tags + description — via the Etsy
Open API v3.

SECURITY: credentials are read from environment variables, never hard-coded or
committed. Use a token, run, then you may revoke it.

Required env vars:
  ETSY_API_KEY     = your app's keystring (x-api-key)
  ETSY_OAUTH_TOKEN = OAuth2 access token with scopes: listings_w listings_r
  ETSY_SHOP_ID     = your numeric shop id

Usage:
  ETSY_API_KEY=... ETSY_OAUTH_TOKEN=... ETSY_SHOP_ID=... \
    python3 tools/etsy_publish.py --manifest tools/etsy_manifest.json [--live]

Without --live it does a DRY RUN (prints what it would create, no API calls
that change data). Review first, then re-run with --live.

NOTE: This follows the documented Etsy v3 endpoints (createDraftListing,
uploadListingImage, uploadListingFile). Etsy occasionally changes required
fields; run a dry run first and we'll adjust to any API error before going live.
"""
import argparse, json, os, sys, time

API = "https://api.etsy.com/v3/application"


def need(name):
    v = os.environ.get(name)
    if not v:
        sys.exit(f"Missing env var: {name}")
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--live", action="store_true", help="actually create listings")
    a = ap.parse_args()

    manifest = json.load(open(a.manifest))
    if not a.live:
        print("DRY RUN — no changes will be made. Listings that WOULD be created:\n")
        for p in manifest["products"]:
            print(f"  • {p['title']}")
            print(f"      price ${p['price']} | tags: {', '.join(p['tags'][:13])}")
            print(f"      image: {p['image']} | file: {p['file']}")
        print(f"\nTotal: {len(manifest['products'])} listings.")
        print("Re-run with --live (and credentials set) to create them.")
        return

    import requests  # only needed for live mode
    api_key = need("ETSY_API_KEY")
    token = need("ETSY_OAUTH_TOKEN")
    shop_id = need("ETSY_SHOP_ID")
    H = {"x-api-key": api_key, "Authorization": f"Bearer {token}"}

    for p in manifest["products"]:
        body = {
            "quantity": 999,
            "title": p["title"][:140],
            "description": p["description"],
            "price": float(p["price"]),
            "who_made": "i_did",
            "when_made": "2020_2025",
            "taxonomy_id": p.get("taxonomy_id", 6072),  # Digital Prints/templates area
            "type": "download",
            "tags": p["tags"][:13],
        }
        r = requests.post(f"{API}/shops/{shop_id}/listings", headers=H, data=body, timeout=30)
        if r.status_code not in (200, 201):
            print(f"✗ create failed for {p['title']}: {r.status_code} {r.text[:300]}")
            continue
        lid = r.json()["listing_id"]
        print(f"✓ created draft {lid}: {p['title']}")
        # image
        with open(p["image"], "rb") as f:
            ri = requests.post(f"{API}/shops/{shop_id}/listings/{lid}/images",
                               headers=H, files={"image": f}, timeout=60)
            print(f"   image: {ri.status_code}")
        # digital file
        with open(p["file"], "rb") as f:
            rf = requests.post(f"{API}/shops/{shop_id}/listings/{lid}/files",
                               headers=H, data={"name": os.path.basename(p["file"])},
                               files={"file": f}, timeout=120)
            print(f"   file: {rf.status_code}")
        time.sleep(1)  # be gentle on rate limits

    print("\nDone. Review your drafts in Etsy, then publish (or set state=active via API).")


if __name__ == "__main__":
    main()
