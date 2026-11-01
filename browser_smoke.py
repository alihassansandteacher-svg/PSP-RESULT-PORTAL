"""Optional browser checks against synthetic records; never exposes real students."""
import csv
import logging
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.disable(logging.CRITICAL)
from app import create_app, REQUIRED, SUBJECTS
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server


def run():
    with tempfile.TemporaryDirectory() as folder:
        fields = sorted(REQUIRED | {key for key, _ in SUBJECTS[False]})
        def row(gr, name='Test Student'):
            return dict.fromkeys(fields, '') | dict(gr=gr, name=name, father='Test Parent', english='0', math='A', total='0', percentage='0%', grade='F')
        with Path(folder, 'class_7.csv').open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
            writer.writerows([row('00123', '<img src=x onerror=alert(1)> Test Student'), row('20'), row('020')])
        app = create_app(folder, {'TESTING': True})
        server = make_server('127.0.0.1', 0, app)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.firefox.launch()
                page = browser.new_page()
                errors = []; page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(f'http://127.0.0.1:{server.server_port}')
                expect(page.locator('#class')).to_be_enabled()
                assert page.locator('#class option[value="6"]').is_disabled()
                for width, height in [(320, 720), (390, 844), (768, 1024), (1440, 1000)]:
                    page.set_viewport_size({'width': width, 'height': height})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}'
                page.select_option('#class', '7'); page.fill('#gr', '000123'); page.press('#gr', 'Enter')
                page.wait_for_selector('#result:not([hidden])')
                assert '<img' in page.locator('#student-name').inner_text()
                assert page.locator('#result-card img').count() == 0
                assert page.locator('#subjects td').nth(0).inner_text() == '0'
                assert page.locator('#subjects td').nth(1).inner_text() == 'Absent'
                for width in [320, 390, 768, 1440]:
                    page.set_viewport_size({'width': width, 'height': 900})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Result overflow at {width}'
                with page.expect_download() as download:
                    page.click('#pdf-button')
                assert download.value.suggested_filename == 'Result_Class_7_00123.pdf'
                page.evaluate('window.__printed = false; window.print = () => { window.__printed = true; }')
                page.click('#print-button'); assert page.evaluate('window.__printed')
                page.emulate_media(media='print')
                assert page.locator('#result-card').is_visible()
                assert not page.locator('.hero').is_visible()
                page.emulate_media(media='screen')
                page.fill('#gr', '20'); assert page.locator('#result').is_hidden()
                page.click('#search-button'); expect(page.locator('#status')).to_contain_text('Multiple records')
                page.fill('#gr', '999'); page.click('#search-button')
                expect(page.locator('#status')).to_contain_text('No result found')
                page.select_option('#class', 'all'); page.fill('#gr', '123'); page.click('#search-button'); page.wait_for_selector('#result:not([hidden])')
                page.route('**/api/get-result/**', lambda route: route.abort())
                page.select_option('#class', '7'); page.fill('#gr', '123'); page.click('#search-button')
                expect(page.locator('#status')).to_have_class('error')
                assert page.locator('#result').is_hidden()
                assert not page.locator('#search-button').is_disabled()
                assert not errors, errors
                browser.close()
                print('PASS: browser search, Enter key, HTML injection defense, zero/absent marks, PDF download, print trigger/styles, duplicate/missing records, all-class search, network failure recovery; no JS runtime errors; no overflow at 320/390/768/1440px.')
        finally:
            server.shutdown(); thread.join(timeout=5)


if __name__ == '__main__':
    run()
