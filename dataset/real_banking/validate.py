import math
from datetime import date, timedelta

def validate(rows):
    seen = set()
    groups = {}
    for r in rows:
        day = date.fromisoformat(r['date'])
        key = (r['bank'], r['service'], r['metric'], r['date'])
        if key in seen:
            raise ValueError(f'Duplicate observation: {key}')
        seen.add(key)
        if r['unit'] not in {'milliseconds', 'percent'}:
            raise ValueError('Unsupported unit')
        v = r['value']
        if v is not None and (not math.isfinite(v) or v < 0 or (r['unit'] == 'percent' and v > 100)):
            raise ValueError(f'Invalid measurement: {key}')
        groups.setdefault(key[:3], set()).add(day)
    gaps = []
    for key, days in groups.items():
        day = min(days)
        while day <= max(days):
            if day not in days:
                gaps.append({'series': key, 'date': day.isoformat()})
            day += timedelta(days=1)
    return {'rows': len(rows), 'null_values': sum(r['value'] is None for r in rows),
            'unsupported_values':[{'date':r['date'],'service':r['service'],'raw_value':r['raw_value']} for r in rows if r['record_status']=='unsupported_value_or_unit'],
            'missing_dates': gaps, 'series': len(groups)}
