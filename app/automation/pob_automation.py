from playwright.sync_api import sync_playwright
from pathlib import Path
import time

POB_LOGIN_URL = "https://pob.ongc.co.in/login"


def run_pob(payload: dict) -> tuple[bool, str]:
    """
    Logs into POB portal and submits login form.
    Keeps browser open until login outcome is clear.
    """

    try:
        pob_username = payload["pob_username"]
        pob_password = payload["pob_password"]
        output_dir = Path(payload["output_dir"])
    except KeyError as e:
        return False, f"Missing required payload key: {e}"

    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,   # MUST be false for now
            slow_mo=300
        )
        context = browser.new_context()
        page = context.new_page()

        try:
            # ---------------- OPEN LOGIN PAGE ----------------
            page.goto(
                POB_LOGIN_URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(5000)

            # ---------------- FIND LOGIN FRAME ----------------
            login_frame = None
            for f in [page] + page.frames:
                try:
                    if f.locator("input[type='password']").count() > 0:
                        login_frame = f
                        break
                except Exception:
                    continue

            if not login_frame:
                raise RuntimeError("Login frame not found")

            # ---------------- USERNAME ----------------
            username = login_frame.locator(
                "input[type='text'], input[name*='cpf'], input[id*='cpf']"
            ).first

            username.wait_for(state="visible", timeout=30000)
            username.fill(pob_username)

            # ---------------- PASSWORD ----------------
            password = login_frame.locator("input[type='password']").first
            password.wait_for(state="visible", timeout=30000)
            password.fill(pob_password)

            # ---------------- SUBMIT ----------------
            submit = login_frame.locator(
                "button[type='submit'], input[type='submit'], button:has-text('Login')"
            ).first

            submit.wait_for(state="visible", timeout=30000)
            submit.click()

            # ---------------- WAIT FOR LOGIN RESULT ----------------
            # Either URL changes OR login page disappears
            try:
                page.wait_for_function(
                    "() => !window.location.href.includes('/login')",
                    timeout=20000
                )
                return True, "POB login successful (navigated away from login)"
            except Exception:
                # Still on login page → likely OTP/CAPTCHA
                return False, "Login submitted but blocked by OTP/CAPTCHA"

        except Exception as e:
            return False, f"POB automation failed: {e}"

        finally:
            # ⚠️ DO NOT close browser automatically
            # Keep it open for debugging
            pass
