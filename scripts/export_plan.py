"""Export master plan (일별계획) to a static JSON data file using artifact_tool."""
import json
from pathlib import Path
from datetime import datetime, timedelta
from artifact_tool import Blob, SpreadsheetFile

ROOT = Path(__file__).resolve().parents[1]
source = Path(__import__('sys').argv[1])
wb = SpreadsheetFile.import_xlsx(Blob.load(str(source)))
rows = wb.worksheets.get_item('일별계획').get_range('A1:O167').values
keys = ['date', 'weekday', 'week', 'phase', 'theme', 'track', 'title', 'method', 'deliverable', 'acceptance', 'plannedHours', 'actualHours', 'status', 'evidence', 'note']
items=[]
for row in rows[1:]:
    if not row[0]: continue
    exceldate=row[0]
    iso=(datetime(1899,12,30)+timedelta(days=exceldate)).strftime('%Y-%m-%d') if isinstance(exceldate,(int,float)) else str(exceldate)[:10]
    record=dict(zip(keys,[iso]+list(row[1:15])))
    record['id']=f'day-{len(items)+1:03d}'
    items.append(record)
file = ROOT / 'web' / 'data' / 'plan.json'
file.write_text(json.dumps(items, ensure_ascii=False, indent=2),encoding='utf-8')
competency = wb.worksheets.get_item('역량평가기준').get_range('A2:D33').values
competency_list=[{'track':r[0], 'skill':r[1], 'target':r[2], 'evidence':r[3]} for r in competency if r[1]]
(ROOT / 'web' / 'data' / 'competencies.json').write_text(json.dumps(competency_list,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Exported {len(items)} days and {len(competency_list)} competency criteria')
