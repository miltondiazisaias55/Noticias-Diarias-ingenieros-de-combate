import pdfplumber
import sys
import re
from datetime import date

PDF_PATH = "noticias.pdf"
OUTPUT_PATH = "index.html"

def extract_text(pdf_path):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    return "\n".join(pages)

def is_location_line(line):
    if not line:
        return False
    cp = ord(line[0])
    return 0x1F1E0 <= cp <= 0x1F1FF

def parse_content(text):
    lines = [l.strip() for l in text.split('\n')]

    date_str = ""
    for line in lines[:10]:
        if re.search(r'(lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)', line, re.I):
            date_str = line
            break

    news_start = None
    tendencias_start = None
    for i, line in enumerate(lines):
        upper = line.upper()
        if 'NOTICIAS DEL D' in upper and news_start is None:
            news_start = i + 1
        if 'TENDENCIAS DEL D' in upper:
            tendencias_start = i
            break

    if news_start is None:
        return date_str, [], []

    news_lines = lines[news_start:tendencias_start or len(lines)]
    tend_lines = lines[tendencias_start:] if tendencias_start else []

    articles = []
    current = None
    for line in news_lines:
        if not line:
            continue
        if is_location_line(line):
            if current:
                articles.append(finalize(current))
            current = {'loc': line, 'rest': []}
        elif current is not None:
            current['rest'].append(line)
    if current:
        articles.append(finalize(current))

    observations = []
    for line in tend_lines:
        stripped = line.lstrip()
        if stripped.startswith(('▸', '▶', '•', '-')):
            observations.append(stripped[1:].strip())

    return date_str, articles, observations

def finalize(raw):
    loc_line = raw['loc']
    flag_char = loc_line[0]
    location = loc_line[1:].strip()

    rest = raw['rest']
    source = ''
    content = []
    for line in rest:
        if line.startswith('Fuente:'):
            source = line[7:].strip()
        else:
            content.append(line)

    title_parts, body_parts = [], []
    in_body = False
    for i, line in enumerate(content):
        if in_body:
            body_parts.append(line)
        else:
            title_parts.append(line)
            joined = ' '.join(title_parts)
            if len(joined) > 90:
                in_body = True

    loc_upper = location.upper()
    if 'ESTADOS UNIDOS' in loc_upper or 'USA' in loc_upper:
        flag = '🇺🇸'
    elif 'URUGUAY' in loc_upper:
        flag = '🇺🇾'
    elif 'ESPA' in loc_upper:
        flag = '🇪🇸'
    elif 'EUROPA' in loc_upper or 'POLONIA' in loc_upper:
        flag = '🇵🇱'
    elif 'ISRAEL' in loc_upper:
        flag = '🇮🇱'
    elif 'UCRANIA' in loc_upper:
        flag = '🇺🇦'
    elif 'RUSIA' in loc_upper:
        flag = '🇷🇺'
    elif 'FRANCE' in loc_upper or 'FRANCIA' in loc_upper:
        flag = '🇫🇷'
    elif 'ALEMANIA' in loc_upper:
        flag = '🇩🇪'
    else:
        flag = '🌐'

    return {
        'flag': flag,
        'location': location,
        'title': ' '.join(title_parts),
        'body': ' '.join(body_parts),
        'source': source
    }

def esc(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def generate_html(date_str, articles, observations):
    today = date.today()
    months = ['enero','febrero','marzo','abril','mayo','junio',
              'julio','agosto','septiembre','octubre','noviembre','diciembre']
    days_es = ['lunes','martes','miércoles','jueves','viernes','sábado','domingo']
    date_display = date_str or f"{days_es[today.weekday()]}, {today.day} de {months[today.month-1]} de {today.year}"
    update_str = f"Actualizado el {today.day} de {months[today.month-1]} de {today.year}, 07:00"

    cards = ""
    for a in articles:
        cards += f"""
      <div class="news-card">
        <div class="news-meta"><span>{a['flag']}</span> {esc(a['location'])}</div>
        <div class="news-title">{esc(a['title'])}</div>
        <div class="news-body">{esc(a['body'])}</div>
        <div class="news-source">Fuente: <span>{esc(a['source'])}</span></div>
      </div>"""

    obs_html = "".join(f"        <li>{esc(o)}</li>\n" for o in observations)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Ingenieros Militares — Diario</title>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f0ee;color:#1a1a1a;min-height:100vh}}
    header{{background:#1b2a3b;color:#fff;padding:1rem 2rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.5rem}}
    .badge{{background:#c0392b;color:#fff;font-size:.65rem;font-weight:700;letter-spacing:.08em;padding:2px 8px;border-radius:3px;text-transform:uppercase}}
    .sub{{font-size:.78rem;color:#a0b0c0;margin-top:2px}}
    .hdate{{font-size:.85rem;color:#a0b0c0}}
    main{{max-width:860px;margin:0 auto;padding:1.5rem 1rem 3rem}}
    .status{{background:#fff;border:1px solid #e0e0dc;border-radius:8px;padding:.6rem 1rem;font-size:.82rem;color:#555;display:flex;align-items:center;gap:.5rem;margin-bottom:1.5rem}}
    .dot{{width:8px;height:8px;background:#27ae60;border-radius:50%;flex-shrink:0}}
    .label{{font-size:.7rem;font-weight:700;letter-spacing:.12em;color:#888;text-transform:uppercase;margin-bottom:.75rem}}
    .list{{display:flex;flex-direction:column;gap:.75rem;margin-bottom:2rem}}
    .news-card{{background:#fff;border:1px solid #e0e0dc;border-radius:10px;padding:1rem 1.25rem}}
    .news-meta{{font-size:.68rem;font-weight:700;letter-spacing:.1em;color:#888;text-transform:uppercase;margin-bottom:.4rem}}
    .news-title{{font-size:.97rem;font-weight:600;color:#1a1a1a;line-height:1.4;margin-bottom:.55rem}}
    .news-body{{font-size:.85rem;color:#444;line-height:1.65;margin-bottom:.6rem}}
    .news-source{{font-size:.78rem;color:#777}}
    .tend{{background:#1e3248;border-radius:10px;padding:1.25rem 1.5rem;color:#d0dde8}}
    .tend-title{{font-size:.75rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#90aac0;margin-bottom:.75rem}}
    .tend ul{{list-style:none;display:flex;flex-direction:column;gap:.65rem}}
    .tend li{{font-size:.86rem;line-height:1.6;padding-left:1.2rem;position:relative}}
    .tend li::before{{content:'▸';position:absolute;left:0;color:#5a8aaa}}
    footer{{text-align:center;font-size:.75rem;color:#aaa;padding:1.5rem 1rem;border-top:1px solid #ddd;margin-top:2rem}}
  </style>
</head>
<body>
  <header>
    <div>
      <div style="display:flex;align-items:center;gap:.5rem">
        <span style="font-size:1.2rem">⚔️</span>
        <span style="font-size:1.2rem;font-weight:600">Ingenieros Militares</span>
        <span class="badge">Diario</span>
      </div>
      <div class="sub">Noticias de ingenieros de combate · Actualizado cada mañana a las 7am</div>
    </div>
    <div class="hdate">{date_display}</div>
  </header>
  <main>
    <div class="status"><span class="dot"></span>{update_str}</div>
    <div class="label">Noticias del día</div>
    <div class="list">{cards}
    </div>
    <div class="label">Tendencias del día</div>
    <div class="tend">
      <div class="tend-title">📊 Observaciones</div>
      <ul>
{obs_html}      </ul>
    </div>
  </main>
  <footer>Ingenieros Militares Diario · Edición del {date_display}</footer>
</body>
</html>"""

if __name__ == "__main__":
    pdf = sys.argv[1] if len(sys.argv) > 1 else PDF_PATH
    print(f"Procesando {pdf}...")
    text = extract_text(pdf)
    date_str, articles, observations = parse_content(text)
    print(f"Fecha: {date_str} | Artículos: {len(articles)} | Obs: {len(observations)}")
    html = generate_html(date_str, articles, observations)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Generado: {OUTPUT_PATH}")
