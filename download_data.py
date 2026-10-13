"""Download a complete one-week cohort; omit addresses and free text."""
from pathlib import Path
from datetime import date
import hashlib
import json
import urllib.parse
import urllib.request

ROOT = Path(__file__).parent
BASE = 'https://data.cityofnewyork.us/resource/erm2-nwe9'
WHERE = "created_date >= '2025-11-01T00:00:00' AND created_date < '2025-11-08T00:00:00'"

def download():
    folder = ROOT / 'data'; folder.mkdir(exist_ok=True)
    count_url = BASE + '.json?' + urllib.parse.urlencode({'$select': 'count(*) as records', '$where': WHERE})
    count = int(json.load(urllib.request.urlopen(count_url, timeout=90))[0]['records'])
    if count > 100000:
        raise ValueError('Cohort needs pagination; refusing a silently truncated download')
    url = BASE + '.csv?' + urllib.parse.urlencode({
        '$select': 'unique_key,created_date,closed_date,agency,complaint_type,borough,status',
        '$where': WHERE, '$order': 'created_date,unique_key', '$limit': 100000})
    blob = urllib.request.urlopen(url, timeout=120).read()
    (folder / 'service_requests.csv').write_bytes(blob)
    provenance = {'retrieved_on': str(date.today()), 'source': url, 'expected_rows': count,
                  'sha256': hashlib.sha256(blob).hexdigest(), 'cohort_start': '2025-11-01',
                  'cohort_end_exclusive': '2025-11-08', 'analysis_cutoff': '2025-12-01T00:00:00'}
    (folder / 'provenance.json').write_text(json.dumps(provenance, indent=2))

if __name__ == '__main__':
    download()
