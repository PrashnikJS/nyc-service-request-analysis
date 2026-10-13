"""Use a fixed closure cutoff and separate open cases from closed-case times."""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).parent
CUTOFF = pd.Timestamp('2025-12-01')

def prepare(raw, cutoff=CUTOFF):
    if raw.unique_key.duplicated().any():
        raise ValueError('Service-request IDs must be unique')
    df = raw.copy()
    df['created_date'] = pd.to_datetime(df.created_date, format='ISO8601', errors='coerce')
    df['closed_date'] = pd.to_datetime(df.closed_date, format='ISO8601', errors='coerce')
    bad_created = df.created_date.isna() | (df.created_date >= cutoff)
    negative = df.closed_date.notna() & (df.closed_date < df.created_date)
    audit = {'source_rows': len(raw), 'invalid_created_rows': int(bad_created.sum()),
             'negative_closure_intervals': int((negative & ~bad_created).sum())}
    df = df.loc[~bad_created].copy()
    # Invalid closure times remain visible, but never enter speed calculations.
    df['valid_closure'] = df.closed_date.notna() & (df.closed_date >= df.created_date) & (df.closed_date < cutoff)
    df['closure_hours'] = ((df.closed_date - df.created_date).dt.total_seconds() / 3600).where(df.valid_closure)
    df['open_or_invalid_at_cutoff'] = ~df.valid_closure
    df['closed_within_48h'] = df.valid_closure & (df.closure_hours <= 48)
    df['borough'] = df.borough.fillna('Unknown').str.upper()
    df['complaint_type'] = df.complaint_type.fillna('Unknown')
    audit['accepted_rows'] = len(df)
    return df, audit

def group_summary(df, group):
    report = df.groupby(group, dropna=False).agg(
        requests=('unique_key', 'count'), closed_by_cutoff=('valid_closure', 'sum'),
        closed_within_48h=('closed_within_48h', 'sum'), median_closed_hours=('closure_hours', 'median'),
        p90_closed_hours=('closure_hours', lambda x: x.quantile(.9))).reset_index()
    report['open_or_invalid'] = report.requests - report.closed_by_cutoff
    # Denominator includes requests still open, rather than only the fast closed cases.
    report['within_48h_pct_all_requests'] = 100 * report.closed_within_48h / report.requests
    return report.sort_values('requests', ascending=False)

def save_charts(df, categories, out):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    top = categories.head(10).sort_values('requests')
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.barh(top.complaint_type, top.requests, color='#17655d')
    ax.set(title='Largest request categories: 1-7 November 2025', xlabel='Service requests')
    fig.tight_layout(); fig.savefig(out / 'request_categories.png', dpi=180); plt.close(fig)

    valid = df[df.valid_closure & df.complaint_type.isin(categories.head(6).complaint_type)]
    order = categories.head(6).complaint_type.tolist()
    groups = [valid.loc[valid.complaint_type == name, 'closure_hours'] for name in order]
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.boxplot(groups, tick_labels=order, orientation='horizontal', showfliers=False)
    ax.set(title='Closed-case duration distributions by category (outliers omitted)', xlabel='Hours until recorded closure')
    fig.tight_layout(); fig.savefig(out / 'closure_distributions.png', dpi=180); plt.close(fig)

    heat = pd.crosstab(df.borough, df.complaint_type).reindex(columns=categories.head(8).complaint_type)
    heat = heat.div(heat.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(12, 5))
    image = ax.imshow(heat, cmap='YlGnBu', aspect='auto', vmin=0, vmax=100)
    ax.set_xticks(range(len(heat.columns)), heat.columns, rotation=30, ha='right')
    ax.set_yticks(range(len(heat.index)), heat.index)
    ax.set_title('Borough request mix within the eight largest categories (%)')
    fig.colorbar(image, ax=ax, label='Share within selected categories (%)')
    fig.tight_layout(); fig.savefig(out / 'borough_category_heatmap.png', dpi=180); plt.close(fig)

def main():
    raw = pd.read_csv(ROOT / 'data/service_requests.csv', dtype={'unique_key': str})
    source = json.loads((ROOT / 'data/provenance.json').read_text())
    if len(raw) != source['expected_rows']:
        raise ValueError('Downloaded row count does not match source query')
    df, metrics = prepare(raw)
    out = ROOT / 'outputs'; out.mkdir(exist_ok=True)
    categories = group_summary(df, ['complaint_type'])
    boroughs = group_summary(df, ['borough'])
    daily = df.groupby(df.created_date.dt.date).size().rename('requests').reset_index()
    categories.round(2).to_csv(out / 'category_summary.csv', index=False)
    boroughs.round(2).to_csv(out / 'borough_summary.csv', index=False)
    daily.to_csv(out / 'daily_requests.csv', index=False)
    metrics.update({'closed_by_cutoff': int(df.valid_closure.sum()),
                    'open_or_invalid_at_cutoff': int((~df.valid_closure).sum()),
                    'request_categories': int(df.complaint_type.nunique()),
                    'median_closed_hours': float(df.closure_hours.median()),
                    'within_48h_pct_all_requests': float(df.closed_within_48h.mean() * 100),
                    'analysis_cutoff': str(CUTOFF), 'charts': 3})
    save_charts(df, categories, out)
    (out / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    note = f"Of {len(df):,} requests created during 1-7 November 2025, {metrics['closed_by_cutoff']:,} have a valid recorded closure before 1 December 2025. Closed-case median duration is {metrics['median_closed_hours']:.2f} hours. Compare request categories before interpreting borough differences. Recorded closure is not confirmed resolution, and 48 hours is a descriptive threshold, not an official SLA."
    (out / 'findings.md').write_text('# Service-request review\n\n' + note + '\n')
    (out / 'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>NYC service requests</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:35px auto;padding:20px;color:#18303e}img{width:100%;height:auto}table{border-collapse:collapse;font-size:13px}td,th{padding:8px;border:1px solid #ccc}.wide{overflow:auto}</style><h1>NYC service-request analysis</h1><p>' + note + '</p><img alt="Top request categories" src="request_categories.png"><img alt="Closure duration box plots" src="closure_distributions.png"><img alt="Borough category mix heatmap" src="borough_category_heatmap.png"><h2>Category summary</h2><div class="wide">' + categories.head(20).round(2).to_html(index=False) + '</div></html>')
    print(json.dumps(metrics, indent=2))

if __name__ == '__main__':
    main()
