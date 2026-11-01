'use strict';
const $ = (id) => document.getElementById(id);
let currentResult = null;
let searching = false;
function status(message, error = false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}
async function request(url) {
  const response = await fetch(url, {cache: 'no-store', signal: AbortSignal.timeout(15000)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Unable to complete this request. Please try again.');
  return data;
}
function clearResult() {
  currentResult = null;
  $('result').hidden = true;
}
function mark(value) {
  return String(value).toUpperCase() === 'A' ? 'Absent' : (value ?? '') === '' ? 'Not provided' : String(value);
}
function percentage(value) {
  return value === '' || value == null ? 'Not provided' : `${String(value).replace(/%+$/, '').trim()}%`;
}
function render(data) {
  currentResult = data;
  $('student-name').textContent = data.name || 'Name not provided';
  $('student-details').textContent = `Class ${data.class} · GR ${data.gr} · Father: ${data.father || 'Not provided'}`;
  $('summary').replaceChildren();
  for (const [label, value] of [['Total marks', data.total || 'Not provided'], ['Percentage', percentage(data.percentage)], ['Grade', data.grade || 'Not provided']]) {
    const group = document.createElement('div');
    const term = document.createElement('dt'); term.textContent = label;
    const description = document.createElement('dd'); description.textContent = value;
    group.append(term, description); $('summary').append(group);
  }
  $('subjects').replaceChildren();
  for (const subject of data.subjects) {
    const row = document.createElement('tr');
    const name = document.createElement('th'); name.scope = 'row'; name.textContent = subject.name;
    const marks = document.createElement('td'); marks.textContent = mark(subject.marks);
    row.append(name, marks); $('subjects').append(row);
  }
  $('result').hidden = false;
  $('result-heading').focus({preventScroll: true});
  $('result').scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth', block: 'start'});
}
$('search-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (searching) return;
  const gr = $('gr').value.trim();
  if (!/^[0-9]{1,20}$/.test(gr)) {status('Enter a GR number using up to 20 digits.', true); return;}
  const selected = $('class').value;
  searching = true; clearResult();
  $('search-button').disabled = true; $('class').disabled = true; $('gr').readOnly = true;
  $('search-form').setAttribute('aria-busy', 'true');
  status('Looking up your result…');
  try {
    const url = selected === 'all' ? `/api/search-result/${encodeURIComponent(gr)}` : `/api/get-result/${encodeURIComponent(selected)}/${encodeURIComponent(gr)}`;
    render(await request(url)); status('Your result is ready.');
  } catch (error) {status(error.name === 'TimeoutError' ? 'The request timed out. Please try again.' : error.message, true);}
  finally {
    searching = false; $('search-button').disabled = false; $('class').disabled = false; $('gr').readOnly = false;
    $('search-form').removeAttribute('aria-busy');
  }
});
$('gr').addEventListener('input', () => {clearResult(); status('');});
$('class').addEventListener('change', () => {clearResult(); status('');});
$('print-button').addEventListener('click', () => {if (currentResult) window.print();});
$('pdf-button').addEventListener('click', async () => {
  if (!currentResult) return;
  const {class: classNum, gr} = currentResult;
  const button = $('pdf-button'); button.disabled = true; button.textContent = 'Preparing PDF…';
  try {
    const response = await fetch(`/api/generate-pdf/${encodeURIComponent(classNum)}/${encodeURIComponent(gr)}`, {cache: 'no-store', signal: AbortSignal.timeout(20000)});
    if (!response.ok) {const data = await response.json(); throw new Error(data.error || 'PDF download failed.');}
    if (!response.headers.get('content-type')?.includes('application/pdf')) throw new Error('The server did not return a PDF.');
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = `Result_Class_${classNum}_${gr}.pdf`;
    document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000);
    status('Your PDF download is ready.');
  } catch (error) {status(`Unable to download PDF. ${error.message}`, true); $('status').scrollIntoView({block: 'center'});}
  finally {button.disabled = false; button.textContent = 'Download PDF ↓';}
});
async function loadClasses() {
  try {
    const data = await request('/api/classes');
    const select = $('class'); select.replaceChildren();
    const prompt = new Option('Select your class', ''); prompt.disabled = true; prompt.selected = true; select.add(prompt);
    for (const item of data.classes) {
      const option = new Option(`${item.name}${!item.available ? ' — unavailable' : !item.published ? ' — not published' : ''}`, item.id);
      option.disabled = !item.available || !item.published; select.add(option);
    }
    select.add(new Option('Search all published classes', 'all'));
    select.disabled = false; $('search-button').disabled = false;
  } catch {status('Unable to load classes. Check your connection and reload this page.', true);}
}
loadClasses();
