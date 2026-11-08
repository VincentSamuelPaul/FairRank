"""Production-build smoke test (run against the Caddy-served stack, same origin, DEBUG off, Secure cookies).

    BASE=http://localhost:8080 scripts/prod-smoke.sh

For each role, at a phone viewport: sign in through the real form (session cookie + CSRF), visit the role's pages,
and fail on any console error, CSP violation, failed API call (5xx) or horizontal scroll. Also checks the session
cookie is HttpOnly + Secure + SameSite=Lax and that error pages leak no stack trace.
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE", "http://localhost:8080")
PASSWORD = os.environ.get("FAIRRANK_DEMO_PASSWORD", "FairRank-demo-1")
ROLES = {
    "recruiter": ("recruiter1@companya.example", ["/requisitions"]),
    "delivery head": ("head@companya.example", ["/pipeline"]),
    "client A": ("manager@northwind.example", ["/portal"]),
    "client B": ("manager@meridian.example", ["/portal"]),
}
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    results.append((ok, label))
    print(("PASS " if ok else "FAIL ") + label + (f"  [{detail}]" if detail else ""))


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for role, (email, paths) in ROLES.items():
            ctx = browser.new_context(viewport={"width": 375, "height": 812}, is_mobile=True, has_touch=True)
            page = ctx.new_page()
            problems: list[str] = []
            page.on("pageerror", lambda e: problems.append("pageerror: " + str(e)[:120]))
            page.on("console", lambda m: problems.append("console: " + m.text[:120]) if m.type == "error" else None)
            page.on("response", lambda r: problems.append(f"{r.status} {r.url[-60:]}") if r.status >= 500 else None)
            page.goto(f"{BASE}/login")
            page.get_by_label("Email").fill(email)
            page.get_by_label("Password", exact=True).fill(PASSWORD)
            page.get_by_role("button", name="Sign in", exact=True).click()
            page.wait_for_url(lambda u: "/login" not in u)
            page.wait_for_load_state("networkidle")
            cookies = {c["name"]: c for c in ctx.cookies()}
            sess = cookies.get("sessionid", {})
            check(bool(sess) and sess["httpOnly"] and sess["secure"] and sess["sameSite"] == "Lax",
                  f"{role}: session cookie is HttpOnly, Secure, SameSite=Lax", str({k: sess.get(k) for k in ("httpOnly", "secure", "sameSite")}))
            check(cookies.get("csrftoken", {}).get("secure") is True, f"{role}: CSRF cookie is Secure")
            for path in paths:
                page.goto(f"{BASE}{path}")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(600)
                scroll = page.evaluate("[document.documentElement.scrollWidth, innerWidth]")
                check(scroll[0] <= scroll[1], f"{role}: {path} has no horizontal scroll at 375px", str(scroll))
                check("/login" not in page.url, f"{role}: {path} stays signed in after a full reload")
            check(not problems, f"{role}: no console errors, CSP violations or 5xx", "; ".join(problems[:3]))
            # a state-changing call needs CSRF: logout through the UI proves the cookie + header round trip
            page.goto(f"{BASE}{paths[0]}")
            page.wait_for_load_state("networkidle")
            status = page.evaluate("""async () => { const t = document.cookie.match(/csrftoken=([^;]+)/)?.[1];
                const ok = await fetch('/api/auth/logout/', {method:'POST', headers:{'X-CSRFToken': t}, credentials:'same-origin'});
                const noCsrf = await fetch('/api/auth/login/', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
                return [ok.status, noCsrf.status]; }""")
            check(status[0] in (200, 204), f"{role}: POST with the CSRF header succeeds", str(status[0]))
            check(status[1] == 403, "a POST without a CSRF token is refused (403)", str(status[1]))
            ctx.close()
        ctx = browser.new_context()
        page = ctx.new_page()
        res = page.goto(f"{BASE}/api/nope/")
        body = res.text() if res else ""
        check(res is not None and res.status == 404 and "Traceback" not in body and "django" not in body.lower(),
              "unknown API path returns a plain 404 with no stack trace or framework page")
        hdr = page.goto(f"{BASE}/login").all_headers()
        for h in ("content-security-policy", "x-frame-options", "x-content-type-options", "referrer-policy"):
            check(h in hdr, f"response header present: {h}")
        check("server" not in hdr, "no Server header")
        browser.close()
    failed = [lbl for ok, lbl in results if not ok]
    print(f"\n{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
