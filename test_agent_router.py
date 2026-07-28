"""
Quick standalone test for your Agent Router API key.
Run this BEFORE testing the Django site — if this fails, the site will fail too,
since it's the exact same call.

Usage:
    setx AGENT_ROUTER_API_KEY "sk-your-key-here"      (Windows, then open a NEW terminal)
    -- or on the same terminal session --
    set AGENT_ROUTER_API_KEY=sk-your-key-here          (Windows cmd, current session only)
    $env:AGENT_ROUTER_API_KEY="sk-your-key-here"        (PowerShell, current session only)

    python test_agent_router.py
"""
import os
import sys
import requests

API_KEY = os.environ.get("AGENT_ROUTER_API_KEY", "")
BASE_URL = os.environ.get("AGENT_ROUTER_BASE_URL", "https://agentrouter.org/v1/chat/completions")
MODEL = os.environ.get("AGENT_ROUTER_MODEL", "gpt-5.5")

if not API_KEY:
    print("❌ AGENT_ROUTER_API_KEY is not set in this terminal session.")
    print("   Set it, then re-run this script.")
    sys.exit(1)

print(f"Using key:   {API_KEY[:10]}... (length {len(API_KEY)})")
print(f"Endpoint:    {BASE_URL}")
print(f"Model:       {MODEL}")
print("-" * 50)

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}
payload = {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Hello, just testing the connection."}],
}

try:
    response = requests.post(BASE_URL, headers=headers, json=payload, timeout=20)
except requests.exceptions.RequestException as e:
    print(f"❌ Network-level error (couldn't even reach the server): {e}")
    sys.exit(1)

print(f"Status code: {response.status_code}")
print(f"Raw body:    {response.text[:500]}")
print("-" * 50)

if response.status_code == 200:
    try:
        reply = response.json()["choices"][0]["message"]["content"]
        print(f"✅ SUCCESS — model replied: {reply}")
    except (KeyError, IndexError, ValueError):
        print("⚠️ Got a 200 OK but the response shape was unexpected — check the raw body above.")
elif response.status_code == 401:
    print("❌ 401 Invalid API Key — this is NOT a code bug. It means Agent Router itself")
    print("   is rejecting the key. Things to check on your Agent Router dashboard:")
    print("   1. Is this key still active (not revoked/expired)?")
    print("   2. Did you copy the FULL key with no missing/extra characters or spaces?")
    print("   3. Does this key belong to the account/workspace tied to co.agentrouter.org")
    print("      specifically (some routers issue separate keys per region/subdomain)?")
    print("   4. Does your account have credit/balance remaining?")
    print("   -> Regenerate a fresh key on the dashboard and try again.")
elif response.status_code == 404:
    print("❌ 404 — the model name is probably wrong or not available on your plan.")
    print(f"   You requested model='{MODEL}'. Check the exact model ID in your")
    print("   Agent Router dashboard's model list and match it exactly.")
elif response.status_code == 429:
    print("❌ 429 — rate limited or out of credits/quota.")
else:
    print(f"❌ Unexpected status {response.status_code} — see raw body above for details.")
