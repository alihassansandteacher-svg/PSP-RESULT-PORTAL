"""CSV-backed school results. Run with Flask or a production WSGI server."""
import csv
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from flask import Flask, jsonify, render_template, send_file, request
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

BASE_DIR = Path(__file__).resolve().parent
pdfmetrics.registerFont(TTFont('PortalSans', str(BASE_DIR / 'fonts/DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('PortalSans-Bold', str(BASE_DIR / 'fonts/DejaVuSans-Bold.ttf')))
SUBJECTS = {
    False: [('english', 'English'), ('math', 'Mathematics'), ('urdu', 'Urdu'),
            ('science', 'Science'), ('sindhi', 'Sindhi'), ('islamiyat', 'Islamiyat'),
            ('sst', 'Social studies'), ('computer', 'Computer')],
    True: [('english', 'English'), ('bio', 'Biology'), ('urdu', 'Urdu'),
           ('chemistry', 'Chemistry'), ('islamiyat', 'Islamiyat'), ('physics', 'Physics')],
}
REQUIRED = {'gr', 'name', 'father', 'total', 'percentage', 'grade'}


def normalize_gr(value):
    value = str(value).strip()
    if not re.fullmatch(r'[0-9]{1,20}', value):
        return None
    return value.lstrip('0') or '0'


def load_data(directory):
    classes, issues = {}, []
    for number in range(6, 13):
        path = directory / f'class_{number}.csv'
        try:
            with path.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                required = REQUIRED | {key for key, _ in SUBJECTS[number >= 9]}
                if not required.issubset(reader.fieldnames or []):
                    raise ValueError('Missing required columns')
                rows = []
                for line, row in enumerate(reader, 2):
                    if None in row or any(v is None for v in row.values()):
                        issues.append(f'{path.name}:{line}: malformed row excluded')
                        continue
                    row = {key: value.strip() for key, value in row.items()}
                    if normalize_gr(row['gr']) is None:
                        issues.append(f'{path.name}:{line}: invalid GR excluded from lookup')
                        continue
                    rows.append(row)
                classes[str(number)] = rows
                counts = defaultdict(int)
                for row in rows:
                    counts[normalize_gr(row['gr'])] += 1
                if any(count > 1 for count in counts.values()):
                    issues.append(f'{path.name}: duplicate GR; lookup requires staff correction')
        except (OSError, ValueError, csv.Error) as exc:
            issues.append(f'{path.name}: unavailable ({type(exc).__name__})')
    return classes, issues


def create_app(data_dir=None, test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(DATA_DIR=str(data_dir or os.getenv('RESULT_DATA_DIR', BASE_DIR)),
                            STATS_ENABLED=os.getenv('ENABLE_CLASS_STATS', '0') == '1')
    if test_config:
        app.config.update(test_config)
    classes, issues = load_data(Path(app.config['DATA_DIR']))
    app.extensions['result_data'] = classes
    app.extensions['data_issues'] = issues
    for issue in issues:
        app.logger.warning(issue)

    def lookup(number, gr):
        key = normalize_gr(gr)
        if key is None:
            return None, ('Enter a GR number using up to 20 digits.', 400)
        if number is not None and number not in classes:
            return None, ('Class is unavailable.', 404)
        matches = [(n, r) for n, rows in classes.items() if number is None or n == number
                   for r in rows if normalize_gr(r['gr']) == key]
        if len(matches) > 1:
            return None, ('Multiple records match this GR. Select a class or contact the school office to correct the record.', 409)
        if not matches:
            return None, ('No result found. Check the class and GR number or contact the school office.', 404)
        n, row = matches[0]
        result = dict(row, **{'class': n})
        result['subjects'] = [{'name': label, 'marks': row.get(key, '')} for key, label in SUBJECTS[int(n) >= 9]]
        return result, None

    def error_response(error):
        return jsonify(error=error[0]), error[1]

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'
        return response

    @app.get('/')
    def home():
        return render_template('index.html')

    @app.get('/healthz')
    def health():
        return jsonify(status='ok')

    @app.get('/api/classes')
    def available_classes():
        return jsonify(classes=[{'id': str(n), 'name': f'Class {n}',
                                 'available': str(n) in classes,
                                 'published': bool(classes.get(str(n)))} for n in range(6, 13)])

    @app.get('/api/get-result/<class_num>/<gr>')
    def result(class_num, gr):
        data, error = lookup(class_num, gr)
        return error_response(error) if error else jsonify(data)

    @app.get('/api/search-result/<gr>')
    def search(gr):
        data, error = lookup(None, gr)
        return error_response(error) if error else jsonify(data)

    @app.get('/api/class-stats/<class_num>')
    def stats(class_num):
        # Legacy endpoint retained, but the student directory is no longer public.
        if not app.config['STATS_ENABLED']:
            return jsonify(error='Class statistics are disabled.'), 403
        if class_num not in classes:
            return jsonify(error='Class unavailable.'), 404
        percentages = []
        for row in classes[class_num]:
            try:
                value = float(row['percentage'].rstrip('%'))
                if 0 <= value <= 100:
                    percentages.append(value)
            except ValueError:
                pass
        return jsonify(**{'class': class_num}, total_students=len(classes[class_num]),
                       average_percentage=round(sum(percentages) / len(percentages), 2) if percentages else 0)

    @app.get('/api/generate-pdf/<class_num>/<gr>')
    def pdf(class_num, gr):
        data, error = lookup(class_num, gr)
        if error:
            return error_response(error)
        buffer = BytesIO()
        styles = getSampleStyleSheet()
        for style in styles.byName.values():
            style.fontName = 'PortalSans'
        styles['Title'].fontName = 'PortalSans-Bold'
        styles['Heading2'].fontSize = 12
        styles['Heading2'].leading = 17
        def paragraph(value):
            return Paragraph(escape(str(value)), styles['BodyText'])
        story = [Paragraph("People's School", styles['Title']),
                 Paragraph('Sujawal City Campus · Result card · Session 2025–26', styles['Heading2']), Spacer(1, 16)]
        info = [['Class', class_num], ['GR number', data['gr']], ['Student', data['name']], ['Father', data['father']]]
        story.append(Table([[paragraph(v) for v in row] for row in info], colWidths=[110, 380]))
        story.append(Spacer(1, 20))
        rows = [['Subject', 'Marks']] + [[s['name'], display_mark(s['marks'])] for s in data['subjects']]
        rows += [['Total', data['total'] or 'Not provided'], ['Percentage', format_percentage(data['percentage'])], ['Grade', data['grade'] or 'Not provided']]
        table = Table([[paragraph(v) for v in row] for row in rows], colWidths=[330, 160], repeatRows=1)
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f2ef')),
                                  ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f7fa')]),
                                  ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                                  ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        story += [table, Spacer(1, 20), paragraph('Generated ' + datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M UTC')),
                  paragraph('For any discrepancy, contact the school office. This is a computer-generated result.')]
        SimpleDocTemplate(buffer, pagesize=A4, title='Student result', author="People's School").build(story)
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                         download_name=f'Result_Class_{class_num}_{normalize_gr(gr)}.pdf')

    return app


def display_mark(value):
    return 'Absent' if value.upper() == 'A' else value or 'Not provided'


def format_percentage(value):
    return value.rstrip('%').strip() + '%' if value else 'Not provided'


app = create_app()
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '5000')), debug=False)
