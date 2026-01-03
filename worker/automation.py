import os
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from app.settings import POB_USERNAME, POB_PASSWORD, DATA_DIR, HEADLESS
from app.excel_utils import read_rows_as_dicts, write_failed_rows

POB_URL = "https://pob.ongc.co.in/login"

# ---------------- SELECTORS ----------------
SEL_USERNAME = 'input#cpfno, input[name="cpfno"]'
SEL_PASSWORD = 'input#password, input[name="password"]'
SEL_LOGIN_BTN = 'button[type="submit"], button:has-text("Login"), input[type="submit"]'

SEL_VESSEL_DROPDOWN = 'select[name="location"]'

SEL_SEARCH_INPUT = 'input[placeholder="Search"]'
SEL_NO_ITEMS_TEXT = 'text=No items found. Try to broaden your search'

SEL_TABLE_ROWS = 'table tbody tr'

SEL_BULK_ACTIONS_BTN = '#table-bulkActionsDropdown'
SEL_BULK_OFF_DUTY = 'Bulk Assign OFF DUTY'
SEL_BULK_ON_DUTY = 'Bulk Assign ON DUTY'

SEL_FILTERS_DROPDOWN = 'button.dropdown-toggle:has-text("Filters")'
SEL_CURRENT_STATUS_SELECT = 'select:has(option[value="OFF DUTY"])'

SEL_USER_MENU = 'a#navbarDropdown'
SEL_LOGOUT = 'a.dropdown-item[href$="/logout"]:has-text("Logout")'
# ------------------------------------------


def _as_text(v):
    if v is None:
        return ""
    return str(v).strip()


def _first_visible_locator_in_any_frame(page, selector: str, timeout_ms: int = 60000):
    deadline = time.time() + timeout_ms / 1000
    last_err = None

    while time.time() < deadline:
        try:
            loc = page.locator(selector).first
            loc.wait_for(state="visible", timeout=500)
            return loc
        except Exception as e:
            last_err = e

        for fr in page.frames:
            try:
                loc = fr.locator(selector).first
                loc.wait_for(state="visible", timeout=500)
                return loc
            except Exception as e:
                last_err = e

        page.wait_for_timeout(200)

    raise PlaywrightTimeoutError(f"Timeout waiting for visible selector: {selector}") from last_err


def goto_with_retry(page, url: str, attempts: int = 3):
    last_err = None
    for _ in range(attempts):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            return
        except Exception as e:
            last_err = e
            page.wait_for_timeout(2000)
    raise last_err


def fill_search_input_safely(search, value: str) -> bool:
    """Fill search input - single attempt with proper clearing"""
    value = str(value).strip()
    
    print(f"  → Typing: '{value}'")
    
    try:
        # Wait for input to be ready
        search.wait_for(state="visible", timeout=60000)
        
        # Click to focus
        search.click()
        search.page.wait_for_timeout(300)
        
        # Focus the input
        try:
            search.focus()
        except Exception:
            pass
        search.page.wait_for_timeout(200)
        
        # Clear using fill (most reliable method)
        search.fill("")
        search.page.wait_for_timeout(200)
        
        # Type the value slowly
        search.type(value, delay=100)
        
        # Wait for typing to complete
        search.page.wait_for_timeout(500)
        
        # Get the actual value
        typed = (search.input_value() or "").strip()
        
        print(f"  → Input field contains: '{typed}'")
        
        # Check if it matches
        if typed == value:
            print(f"  ✓ Perfect match!")
            return True
        
        # If value is contained (might have extra whitespace), still OK
        if value in typed or typed in value:
            print(f"  ~ Close enough, accepting")
            return True
        
        print(f"  ✗ Mismatch! Expected '{value}' but got '{typed}'")
        return False
        
    except Exception as e:
        print(f"  ✗ Error typing: {e}")
        return False


def clear_search_and_wait(page):
    """Clear search input and wait for table to reset"""
    try:
        search = page.locator(SEL_SEARCH_INPUT).first
        search.wait_for(state="visible", timeout=5000)
        search.click()
        page.wait_for_timeout(200)
        search.fill("")
        search.press("Enter")
        page.wait_for_timeout(1500)
    except Exception:
        pass


def select_checkbox_via_livewire_component(page, ned_value: str) -> bool:
    """
    Select checkbox using Playwright locators - with Livewire wait
    """
    
    try:
        print(f"  → Selecting checkbox for: {ned_value}")
        
        # Wait for any Livewire loading to finish
        try:
            page.wait_for_selector('[wire\\:loading]', state='hidden', timeout=5000)
            print(f"  → Livewire loading complete")
        except Exception:
            print(f"  → No Livewire loading indicator")
        
        # Find all table rows using Playwright locator
        rows = page.locator('table tbody tr')
        row_count = rows.count()
        
        print(f"  → Found {row_count} rows in table")
        
        # Find the row containing the NED value
        for i in range(row_count):
            row = rows.nth(i)
            
            try:
                row_text = row.inner_text()
                
                if ned_value in row_text:
                    print(f"  → Found row containing '{ned_value}'")
                    
                    # Find checkbox in this row
                    checkbox = row.locator('input[type="checkbox"]').first
                    
                    # Wait for checkbox to be ready (not disabled by wire:loading)
                    print(f"  → Waiting for checkbox to be enabled...")
                    checkbox.wait_for(state="visible", timeout=5000)
                    
                    # Wait for it to NOT be disabled
                    for attempt in range(10):
                        is_disabled = checkbox.is_disabled()
                        if not is_disabled:
                            print(f"  → Checkbox is enabled")
                            break
                        print(f"  → Checkbox still disabled, waiting... (attempt {attempt+1}/10)")
                        page.wait_for_timeout(500)
                    
                    # Check if already checked
                    if checkbox.is_checked():
                        print(f"  ✓ Already checked")
                        return True
                    
                    # Scroll into view
                    checkbox.scroll_into_view_if_needed()
                    page.wait_for_timeout(500)
                    
                    # Click using Playwright
                    print(f"  → Clicking checkbox...")
                    checkbox.click()
                    page.wait_for_timeout(1500)  # Wait for Livewire to sync
                    
                    # Verify it's checked
                    if checkbox.is_checked():
                        print(f"  ✓ Checkbox checked successfully!")
                        return True
                    else:
                        print(f"  ✗ Click didn't check the checkbox, trying force click...")
                        # Try force click
                        checkbox.click(force=True)
                        page.wait_for_timeout(1500)
                        
                        if checkbox.is_checked():
                            print(f"  ✓ Force click worked!")
                            return True
                        else:
                            print(f"  ✗ Force click also failed")
                            return False
                            
            except Exception as e:
                print(f"  ⚠ Error checking row {i}: {e}")
                continue
        
        print(f"  ✗ Row containing '{ned_value}' not found")
        return False
        
    except Exception as e:
        print(f"  ✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_selected_count(page) -> int:
    """Get count of currently selected checkboxes"""
    try:
        count = page.evaluate(
            """() => {
                const checkboxes = document.querySelectorAll('input[type="checkbox"]:checked');
                return checkboxes.length;
            }"""
        )
        return count if count else 0
    except Exception:
        return 0


def select_vessel(page, vessel_name: str):
    dd = page.locator(SEL_VESSEL_DROPDOWN).first
    dd.wait_for(state="visible", timeout=60000)
    with page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
        dd.select_option(label=vessel_name)
    page.wait_for_timeout(300)


def ensure_filter_off_duty(page):
    """Apply OFF DUTY filter to show only off-duty personnel"""
    try:
        filters_btn = page.locator(SEL_FILTERS_DROPDOWN).first
        filters_btn.wait_for(state="visible", timeout=10000)
        filters_btn.click()
        page.wait_for_timeout(300)

        status_select = page.locator(SEL_CURRENT_STATUS_SELECT).first
        status_select.wait_for(state="visible", timeout=10000)
        status_select.select_option(value="OFF DUTY")
        page.wait_for_timeout(800)
    except Exception:
        pass


def search_and_select_by_row_text(page, ned_value: str) -> bool:
    """Search for NED and select checkbox - wait for actual table row to appear"""
    ned_value = _as_text(ned_value)
    if not ned_value:
        return False

    print(f"\n🔍 Searching for: {ned_value}")
    
    # Clear search first to reset table
    clear_search_and_wait(page)

    # Fill search input
    search = page.locator(SEL_SEARCH_INPUT).first
    if not fill_search_input_safely(search, ned_value):
        print(f"  ✗ Failed to fill search box properly")
        return False

    # Press Enter
    print(f"  → Pressing Enter...")
    search.press("Enter")
    
    # Wait for the actual row to appear in the table
    # This is more reliable than waiting for Livewire indicators
    print(f"  → Waiting for row to appear in table...")
    
    try:
        # Wait for a table row containing the NED value
        row_selector = f'table tbody tr:has-text("{ned_value}")'
        page.wait_for_selector(row_selector, state="visible", timeout=20000)
        print(f"  ✓ Row appeared in table")
        
        # Additional stabilization for checkbox to be ready
        page.wait_for_timeout(2000)
        
        # Try to select the checkbox
        return select_checkbox_via_livewire_component(page, ned_value)
        
    except Exception as e:
        print(f"  ✗ Row did not appear within 20 seconds")
        print(f"  ✗ Playwright wait error: {e}")
        
        # Fallback: Check if "No items found" message appeared
        try:
            no_items = page.locator(SEL_NO_ITEMS_TEXT).first
            if no_items.is_visible(timeout=1000):
                print(f"  ✗ 'No items found' message displayed")
                return False
        except Exception:
            pass
        
        print(f"  ✗ Failed to find row")
        return False


def bulk_assign_via_livewire(page, mode: str) -> bool:
    """
    Trigger bulk action using Playwright locators (same approach as filters)
    """
    try:
        # Verify we have selections
        selected_count = get_selected_count(page)
        print(f"\n📦 Bulk action: {mode}, Selected count: {selected_count}")
        
        if selected_count == 0:
            print(f"  ✗ No checkboxes selected!")
            return False
        
        # Determine which link text to look for
        if mode == "OFF":
            link_text = SEL_BULK_OFF_DUTY  # "Bulk Assign OFF DUTY"
        else:
            link_text = SEL_BULK_ON_DUTY   # "Bulk Assign ON DUTY"
        
        print(f"  → Looking for bulk action: '{link_text}'")
        
        # Click Bulk Actions dropdown using Playwright locator (same as filters!)
        bulk_btn = page.locator(SEL_BULK_ACTIONS_BTN).first
        bulk_btn.wait_for(state="visible", timeout=10000)
        
        print(f"  → Clicking Bulk Actions dropdown...")
        bulk_btn.click()
        page.wait_for_timeout(800)
        
        print(f"  → Dropdown opened, looking for '{link_text}'...")
        
        # Click the bulk action link using Playwright locator (same as filters!)
        action_link = page.locator(f'a:has-text("{link_text}")').first
        action_link.wait_for(state="visible", timeout=10000)
        
        print(f"  → Clicking '{link_text}'...")
        action_link.click()
        
        print(f"  ✓ Bulk action triggered successfully")
        
        # Wait for Livewire to process the bulk action (AJAX + server processing)
        print(f"  → Waiting for bulk action to complete...")
        page.wait_for_timeout(4000)  # Increased from 3000 to 4000
        
        # Wait for Livewire to finish
        try:
            page.wait_for_selector('[wire\\:loading]', state='hidden', timeout=5000)
            print(f"  → Bulk action processing complete")
        except Exception:
            print(f"  → Bulk action assumed complete")
        
        # Clear search to reset for next batch
        clear_search_and_wait(page)
        
        return True
        
    except Exception as e:
        print(f"  ✗ Bulk action error: {e}")
        import traceback
        traceback.print_exc()
        try:
            clear_search_and_wait(page)
        except Exception:
            pass
        return False


def process_excel_list(page, neds: list[str], rows: list[dict], header_row: list,
                       bulk_mode: str, apply_off_duty_filter: bool) -> list[dict]:
    """
    Process list of NEDs with batch bulk actions
    """
    failed_rows = []
    batch = []
    batch_indices = []

    for idx, ned in enumerate(neds):
        try:
            # Apply OFF DUTY filter if needed (for ON DUTY operations)
            if apply_off_duty_filter and len(batch) == 0:
                print(f"\n🔧 Applying OFF DUTY filter...")
                ensure_filter_off_duty(page)
                page.wait_for_timeout(500)

            ok = search_and_select_by_row_text(page, ned)
            if ok:
                print(f"  ✓ Successfully selected")
                batch.append(ned)
                batch_indices.append(idx)
                page.wait_for_timeout(500)
                
                # Perform bulk action when batch reaches 10
                if len(batch) >= 10:
                    success = bulk_assign_via_livewire(page, bulk_mode)
                    if not success:
                        print(f"  ✗ Batch failed - marking {len(batch)} rows as failed")
                        # If bulk action failed, mark all in batch as failed
                        for batch_idx in batch_indices:
                            failed_rows.append(rows[batch_idx])
                    
                    # Reset batch
                    batch = []
                    batch_indices = []
                    page.wait_for_timeout(1000)
            else:
                print(f"  ✗ Failed to select - adding to failed rows")
                failed_rows.append(rows[idx])

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            failed_rows.append(rows[idx])
            continue

    # Process remaining items in batch
    if len(batch) > 0:
        print(f"\n📦 Processing remaining batch of {len(batch)} items...")
        try:
            if apply_off_duty_filter:
                ensure_filter_off_duty(page)
                page.wait_for_timeout(500)
            
            success = bulk_assign_via_livewire(page, bulk_mode)
            if not success:
                print(f"  ✗ Final batch failed - marking {len(batch)} rows as failed")
                # If bulk action failed, mark all in batch as failed
                for batch_idx in batch_indices:
                    failed_rows.append(rows[batch_idx])
        except Exception as e:
            print(f"  ✗ Exception in final batch: {e}")
            # If bulk action failed, mark all in batch as failed
            for batch_idx in batch_indices:
                failed_rows.append(rows[batch_idx])

    print(f"\n✅ Completed. Failed rows: {len(failed_rows)}/{len(neds)}")
    return failed_rows


def run_portal_automation(job_id: str, upload1_path: str, upload2_path: str,
                          col1: str, col2: str, vessel: str):
    job_dir = os.path.join(DATA_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    header1, rows1 = read_rows_as_dicts(upload1_path)
    header2, rows2 = read_rows_as_dicts(upload2_path)

    neds1 = [_as_text(r.get(col1)) for r in rows1]
    neds2 = [_as_text(r.get(col2)) for r in rows2]

    print(f"\n📊 Excel 1: {len(neds1)} NEDs")
    print(f"📊 Excel 2: {len(neds2)} NEDs")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()

        goto_with_retry(page, POB_URL, attempts=3)

        user_input = _first_visible_locator_in_any_frame(page, SEL_USERNAME, timeout_ms=60000)
        pass_input = _first_visible_locator_in_any_frame(page, SEL_PASSWORD, timeout_ms=60000)
        login_btn = _first_visible_locator_in_any_frame(page, SEL_LOGIN_BTN, timeout_ms=60000)

        user_input.fill(POB_USERNAME)
        pass_input.fill(POB_PASSWORD)
        login_btn.click()

        try:
            page.wait_for_load_state("domcontentloaded", timeout=60000)
        except Exception:
            page.wait_for_timeout(2000)

        select_vessel(page, vessel)
        print(f"✓ Selected vessel: {vessel}")

        # Process first list (mark as OFF DUTY)
        print("\n" + "="*50)
        print("Processing Excel 1 (OFF DUTY)...")
        print("="*50)
        failed1 = process_excel_list(page, neds1, rows1, header1, bulk_mode="OFF", apply_off_duty_filter=False)
        
        page.wait_for_timeout(2000)
        
        # Process second list (mark as ON DUTY - need OFF DUTY filter)
        print("\n" + "="*50)
        print("Processing Excel 2 (ON DUTY)...")
        print("="*50)
        failed2 = process_excel_list(page, neds2, rows2, header2, bulk_mode="ON", apply_off_duty_filter=True)

        try:
            user_menu = page.locator(SEL_USER_MENU).first
            user_menu.wait_for(state="visible", timeout=60000)
            user_menu.click()
            page.wait_for_timeout(200)

            logout_link = page.locator(SEL_LOGOUT).first
            logout_link.wait_for(state="visible", timeout=60000)
            with page.expect_navigation(wait_until="domcontentloaded", timeout=60000):
                logout_link.click()
            print("\n✓ Logged out successfully")
        except Exception:
            pass

        try:
            context.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass

    out1 = os.path.join(job_dir, "excel1_failed_rows.xlsx")
    out2 = os.path.join(job_dir, "excel2_failed_rows.xlsx")
    write_failed_rows(out1, header1, failed1)
    write_failed_rows(out2, header2, failed2)
    
    print(f"\n📁 Output files created:")
    print(f"  - {out1}")
    print(f"  - {out2}")
    
    return out1, out2
