import csv
import logging
import tempfile
import unittest
from pathlib import Path
from app import create_app, normalize_gr, SUBJECTS, REQUIRED


class PortalTests(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.CRITICAL)
        self.temp = tempfile.TemporaryDirectory()
        directory = Path(self.temp.name)
        self.fields = sorted(REQUIRED | {k for k, _ in SUBJECTS[False]})
        def row(gr, name='Test Student'):
            return dict.fromkeys(self.fields, '') | dict(gr=gr, name=name, father='Test Parent', english='0', math='A', total='0', percentage='0%', grade='F')
        with (directory / 'class_7.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fields); writer.writeheader()
            writer.writerows([row('00123', '<b>Student & Test</b>'), row('20'), row('020'), row('A'), row('')])
        with (directory / 'class_6.csv').open('w', newline='') as f:
            csv.DictWriter(f, fieldnames=self.fields).writeheader()
        self.app = create_app(directory, {'TESTING': True})
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def test_home_and_static(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        for path in ['/static/script.js', '/static/style.css', '/static/favicon.svg', '/healthz']:
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)

    def test_normalization(self):
        self.assertEqual(normalize_gr(' 000 '), '0')
        for invalid in ['A', '', '1.0', '-1', '١٢', '1' * 21]:
            self.assertIsNone(normalize_gr(invalid))

    def test_result_preserves_zero_and_absent(self):
        response = self.client.get('/api/get-result/7/123')
        self.assertEqual(response.status_code, 200)
        data = response.json
        self.assertEqual(data['gr'], '00123')
        self.assertEqual(data['subjects'][0]['marks'], '0')
        self.assertEqual(data['subjects'][1]['marks'], 'A')
        self.assertEqual(data['name'], '<b>Student & Test</b>')

    def test_invalid_missing_and_duplicate(self):
        for path, code in [('/api/get-result/7/abc', 400), ('/api/get-result/7/999', 404),
                           ('/api/get-result/12/123', 404), ('/api/get-result/7/20', 409),
                           ('/api/search-result/020', 409), ('/api/generate-pdf/7/20', 409)]:
            self.assertEqual(self.client.get(path).status_code, code, path)

    def test_search(self):
        self.assertEqual(self.client.get('/api/search-result/000123').json['class'], '7')

    def test_class_publication(self):
        classes = {c['id']: c for c in self.client.get('/api/classes').json['classes']}
        self.assertFalse(classes['6']['published'])
        self.assertTrue(classes['7']['published'])
        self.assertFalse(classes['12']['available'])

    def test_statistics_privacy_and_empty(self):
        self.assertEqual(self.client.get('/api/class-stats/7').status_code, 403)
        self.app.config['STATS_ENABLED'] = True
        self.assertEqual(self.client.get('/api/class-stats/6').json['average_percentage'], 0)
        self.assertNotIn('students', self.client.get('/api/class-stats/7').json)

    def test_security_headers(self):
        response = self.client.get('/api/get-result/7/123')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn("script-src 'self'", response.headers['Content-Security-Policy'])

    def test_pdf(self):
        response = self.client.get('/api/generate-pdf/7/123')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'application/pdf')
        self.assertTrue(response.data.startswith(b'%PDF-'))
        self.assertIn('attachment', response.headers['Content-Disposition'])


if __name__ == '__main__':
    unittest.main()
