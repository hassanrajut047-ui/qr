import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'analytics.db')

CREATE_SQL = '''
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL,
    type TEXT NOT NULL,
    item_index INTEGER,
    ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
'''


def get_conn():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DB_PATH):
        with get_conn() as conn:
            conn.executescript(CREATE_SQL)


def record_event(slug, etype, item_index=None):
    init_db()
    with get_conn() as conn:
        conn.execute('INSERT INTO events (slug, type, item_index) VALUES (?, ?, ?)', (slug, etype, item_index))


def record_scan(slug):
    record_event(slug, 'scan')


def record_click(slug, item_index=None):
    record_event(slug, 'click', item_index)


def get_monthly_summary(slug, year=None, month=None):
    init_db()
    now = datetime.utcnow()
    if year is None: year = now.year
    if month is None: month = now.month
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) as cnt FROM events WHERE slug=? AND type="scan" AND ts>=? AND ts<?', (slug, start, end))
        scans = cur.fetchone()['cnt']
        cur.execute('SELECT COUNT(*) as cnt FROM events WHERE slug=? AND type="click" AND ts>=? AND ts<?', (slug, start, end))
        clicks = cur.fetchone()['cnt']
        cur.execute('SELECT item_index, COUNT(*) as cnt FROM events WHERE slug=? AND type="click" AND ts>=? AND ts<? GROUP BY item_index ORDER BY cnt DESC LIMIT 10', (slug, start, end))
        top_items = [{ 'index': r['item_index'], 'clicks': r['cnt'] } for r in cur.fetchall()]
    return {'year': year, 'month': month, 'scans': scans, 'clicks': clicks, 'top_items': top_items}


def get_top_items(slug, since_days=30):
    init_db()
    since = datetime.utcnow() - timedelta(days=since_days)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute('SELECT item_index, COUNT(*) as cnt FROM events WHERE slug=? AND type="click" AND ts>=? GROUP BY item_index ORDER BY cnt DESC LIMIT 20', (slug, since))
        return [{ 'index': r['item_index'], 'clicks': r['cnt'] } for r in cur.fetchall()]


if __name__ == '__main__':
    init_db()
    print('Initialized analytics DB at', DB_PATH)
