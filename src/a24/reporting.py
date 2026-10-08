"""Descriptive, evaluator-only A24 reports; no physics or gate computation.

Call build_report only from the parent under its active B0 ledger. Plotting
imports, summaries, file reads and writes occur inside that charged call.
Every gate status comes from the saved decision, including HOLD/NOT_RUN.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import time

from a20.costs import BudgetExceeded, write_json


def _number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def _read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def _read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline='', encoding='utf-8') as handle:
        return list(csv.DictReader(handle))


def _read_jsonl(path):
    path = Path(path)
    if not path.exists():
        return []
    records = []
    with path.open(encoding='utf-8') as handle:
        for index, line in enumerate(handle, 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    records.append({'status': 'UNREADABLE_LEDGER_RECORD', 'line': index,
                                    'source_path': str(path)})
    return records


def _write_csv(path, rows, fields=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(key for row in rows for key in row)) or ['status']
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False)
                             if isinstance(value, (dict, list)) else value
                             for key, value in row.items()})


def _format(value):
    if value is None or value == '':
        return '—'
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    number = _number(value)
    if number is not None and not isinstance(value, (str, bool)):
        return f'{number:.6g}'
    return str(value).replace('|', '\\|').replace('\n', ' ')


def _table(rows, columns):
    header = '| ' + ' | '.join(label for _, label in columns) + ' |'
    separator = '| ' + ' | '.join('---' for _ in columns) + ' |'
    if not rows:
        rows = [{}]
    return '\n'.join([header, separator] +
                     ['| ' + ' | '.join(_format(row.get(key)) for key, _ in columns) + ' |'
                      for row in rows])


def _case_id(background, parent, amplitude, noise):
    return f'{background}_{parent}_{amplitude}_{"zero" if noise is None else "snr20"}'


def _conditions(config, raw):
    index = defaultdict(list)
    for row in raw:
        index[(row.get('case_id'), row.get('method'))].append(row)
    matrix = []
    for background in ('weak', 'ring'):
        for parent, family in zip(config['parents'], config['parent_families']):
            for amplitude in config['amplitudes']:
                for noise in config['noise_snr_db']:
                    case = _case_id(background, parent, amplitude, noise)
                    for method in config['methods']:
                        found = index[(case, method)]
                        base = {'case_id': case, 'parent_id': parent, 'family': family,
                                'background': background, 'amplitude': amplitude,
                                'noise_db': noise, 'method': method, 'recorded_rows': len(found)}
                        if len(found) == 1:
                            matrix.append({**base, **found[0]})
                        elif not found:
                            matrix.append({**base, 'status': 'NOT_RUN_MISSING_RECORD'})
                        else:
                            matrix.append({**base, 'status': 'DUPLICATE_RECORDED_CONDITION',
                                           'error': 'See all raw rows; no favorable duplicate selected'})
    return matrix


def _parent_summary(config, matrix):
    expected = 2*len(config['amplitudes'])*len(config['noise_snr_db'])
    rows = []
    for parent, family in zip(config['parents'], config['parent_families']):
        for method in config['methods']:
            subset = [r for r in matrix if str(r['parent_id']) == str(parent)
                      and r['method'] == method]
            for metric in ('material_nrmse', 'delta_nrmse', 'real_nrmse', 'imag_nrmse'):
                values = [_number(r.get(metric)) for r in subset if r.get('status') == 'OK']
                values = [v for v in values if v is not None]
                complete = len(subset) == expected and len(values) == expected
                rows.append({'parent_id': parent, 'family': family, 'method': method,
                             'metric': metric, 'expected_conditions': expected,
                             'valid_conditions': len(values), 'complete': complete,
                             'official_parent_mean': statistics.mean(values) if complete else None,
                             'available_only_descriptive_mean': statistics.mean(values) if values else None,
                             'scope': 'four exposed synthetic parents; incomplete means excluded from gates'})
    return rows


def _jobs(root, book):
    jobs = []
    for directory in sorted((root/'results/jobs').glob('*'), key=lambda p: p.stat().st_mtime):
        if not directory.is_dir():
            continue
        manifest = _read_json(directory/'manifest.json', {})
        receipt = _read_json(directory/'job_receipt.json', {})
        result = _read_json(directory/'result.json', {})
        if not receipt and manifest.get('job') == book.metadata.get('job'):
            receipt = {**book.receipt(), 'stage': book.metadata.get('stage'),
                       'command': manifest.get('command')}
        if not receipt:
            continue
        ledger = _read_jsonl(directory/'COST_LEDGER.jsonl')
        jobs.append({'directory': directory, 'manifest': manifest, 'receipt': receipt,
                     'result': result, 'ledger': ledger,
                     'row': {'job': directory.name, 'command': receipt.get('command', manifest.get('command')),
                             'stage': receipt.get('stage'),
                             'status': result.get('status', result.get('decision', 'ACTIVE_SNAPSHOT')),
                             'wall_seconds': receipt.get('wall_seconds'),
                             'process_cpu_seconds': receipt.get('process_cpu_seconds'),
                             'new_clean_labels': receipt.get('new_clean_labels'),
                             'geometry_setup_s': receipt.get('exclusive_walls', {}).get('tm2d_geometry_setup'),
                             'peak_cpu_rss_bytes': receipt.get('peak_cpu_rss_bytes'),
                             'source_commit': manifest.get('source_commit')}})
    return jobs


def _runtime(config, matrix, preparations, timing, jobs):
    """Measured warm samples plus transparent one-setup accounting projections.

    This frozen pilot has a recorded recovery boundary: job001 delivered every
    weak condition and the two ring/2401/amplitude .3 conditions; job002 filled
    the remaining checkpoint rows. Successful image components are matched to
    that source job's measured geometry span. No failed image is assigned an
    invented deployment time. Archive export is included in total science job
    wall, but is not a required step in in-memory deployment setup.
    """
    recorded_jobs = {job['row']['job']: job for job in jobs}
    image_index = {(r['case_id'], r['method']): r for r in matrix}
    first_by_family = list(dict.fromkeys(config['parent_families']))
    parents = [config['parents'][config['parent_families'].index(f)] for f in first_by_family]
    expected_repeats = config['timing_repeats']
    output = []
    for background in ('weak', 'ring'):
        for parent in parents:
            case = _case_id(background, parent, config['amplitudes'][0], 20)
            for method in ('L', 'F', 'R16'):
                samples = [r for r in timing if r.get('case_id') == case and r.get('method') == method]
                valid = [_number(r.get('warm_s')) for r in samples if r.get('status') == 'OK']
                valid = [v for v in valid if v is not None]
                complete = len(samples) == expected_repeats and len(valid) == expected_repeats
                warm = statistics.median(valid) if complete else None
                image = image_index.get((case, method), {})
                matches = []
                for index, prep in enumerate(preparations):
                    if prep.get('background') != background or prep.get('method') != method or prep.get('status') != 'OK':
                        continue
                    shared, specific = _number(prep.get('shared_background_s')), _number(prep.get('specific_setup_s'))
                    if (shared is not None and specific is not None
                            and shared == _number(image.get('shared_background_s'))
                            and specific == _number(image.get('specific_setup_s'))):
                        matches.append((index, prep))
                chosen = matches[0] if len(matches) == 1 else None
                prep = chosen[1] if chosen else {}
                source = None
                if (config['protocol_id'] == 'A24-NO-NN-20261008-v1'
                        and image.get('status') == 'OK'):
                    first_checkpoint = (background == 'weak' or
                                        (background == 'ring' and parent == 2401
                                         and _number(image.get('amplitude')) == .3))
                    source = recorded_jobs.get('a24-b0-001' if first_checkpoint else 'a24-b0-002')
                geometry = _number(source['row']['geometry_setup_s']) if source else None
                shared = _number(image.get('shared_background_s'))
                specific = _number(image.get('specific_setup_s'))
                cost = json.loads(prep.get('cost') or '{}')
                export = _number(cost.get('exclusive_walls', {}).get('feedback_cache_export', 0.))
                setup = (geometry+shared+specific
                         if all(v is not None for v in (geometry, shared, specific)) else None)
                raw_cold = _number(image.get('cold_image_s'))
                for reuse in (1, 10, 100):
                    output.append({'case_id': case, 'parent_id': parent, 'background': background,
                                   'method': method, 'N': reuse, 'valid_repeats': len(valid),
                                   'expected_repeats': expected_repeats,
                                   'timing_status': 'COMPLETE' if complete else 'INCOMPLETE_OR_FAILED',
                                   'geometry_setup_s': geometry, 'shared_background_s': shared,
                                   'specific_setup_s': specific, 'archive_cache_export_span_s': export,
                                   'setup_including_geometry_s': setup,
                                   'setup_source_row': chosen[0] if chosen else None,
                                   'setup_source_job': source['row']['job'] if source else None,
                                   'setup_association': 'RECORDED_RECOVERY_BOUNDARY_AND_IMAGE_COMPONENTS'
                                   if source else 'UNRESOLVED_NO_COLD_CLAIM',
                                   'setup_provenance': 'job001: weak16 + ring2401/.3/zero,snr20; job002: checkpoint recovery',
                                   'warm_median_s': warm,
                                   'warm_min_s': min(valid) if valid else None,
                                   'warm_max_s': max(valid) if valid else None,
                                   'driver_cold_image_excluding_geometry_s': raw_cold,
                                   'cold_in_memory_image_s': raw_cold+geometry
                                   if raw_cold is not None and geometry is not None else None,
                                   'disk_loaded_cache_cold_s': None,
                                   'disk_loaded_cache_status': 'NOT_RUN',
                                   'cold_components_plus_warm_s': setup+warm if setup is not None and warm is not None else None,
                                   'amortized_per_image_s': warm+setup/reuse if setup is not None and warm is not None else None,
                                   'projected_total_s': setup+reuse*warm if setup is not None and warm is not None else None,
                                   'evidence': 'accounting projection of measured components; N deployments NOT_RUN',
                                   'unsegmented_io': 'remaining cache/data I/O is in full job wall; not individually allocated'})
    return output


def _descriptive_pairs(config, matrix):
    """Same-condition pairs and complete weak-background parent descriptions.

    These are never official full-eight-condition parent means or gates.
    Percent gains are calculated within each parent before equal weighting.
    """
    index = {(r['case_id'], r['method']): r for r in matrix}
    per_parent = []
    expected = len(config['amplitudes'])*len(config['noise_snr_db'])
    for background in ('weak', 'ring'):
        for parent, family in zip(config['parents'], config['parent_families']):
            pairs = []
            for amplitude in config['amplitudes']:
                for noise in config['noise_snr_db']:
                    case = _case_id(background, parent, amplitude, noise)
                    arms = [index.get((case, method), {}) for method in ('L', 'F', 'R16')]
                    if all(r.get('status') == 'OK' and _number(r.get('material_nrmse')) is not None
                           for r in arms):
                        pairs.append([_number(r['material_nrmse']) for r in arms])
            means = [statistics.mean(p[i] for p in pairs) for i in range(3)] if pairs else [None]*3
            l, f, r = means
            per_parent.append({'background': background, 'parent_id': parent, 'family': family,
                               'paired_conditions': len(pairs), 'expected_background_conditions': expected,
                               'complete_background_subgroup': len(pairs) == expected,
                               'L_available_paired_mean': l, 'F_available_paired_mean': f,
                               'R16_available_paired_mean': r,
                               'F_gain_percent': 100*(l-f)/l if l is not None and l > 0 else None,
                               'R_gain_percent': 100*(l-r)/l if l is not None and l > 0 else None,
                               'R_gain_retention': (l-r)/(l-f) if l is not None and l > f else None,
                               'scope': 'descriptive same-condition background subgroup; not full8 gate mean'})
    summaries = []
    for background in ('weak', 'ring'):
        subset = [r for r in per_parent if r['background'] == background]
        permitted = background == 'weak' and all(r['complete_background_subgroup'] for r in subset)
        summary = {'background': background, 'parents': len(subset),
                   'complete_background_parents': sum(r['complete_background_subgroup'] for r in subset),
                   'status': 'COMPLETE_WEAK_SUBGROUP_DESCRIPTION' if permitted else 'NO_EQUAL_PARENT_SUBGROUP_AGGREGATE',
                   'scope': 'equal weight across four exposed parents; NOT official full8/gate statistic'}
        for key in ('L_available_paired_mean','F_available_paired_mean','R16_available_paired_mean',
                    'F_gain_percent','R_gain_percent','R_gain_retention'):
            values = [r[key] for r in subset if r[key] is not None]
            summary[key] = statistics.mean(values) if permitted and len(values) == len(subset) else None
        summaries.append(summary)
    return per_parent, summaries


def _task_ranges(tasks):
    primary = [r for r in tasks if r.get('method') == 'R16' and r.get('status') == 'OK']
    rows = []
    for key in ('independent_transfer_error','independent_adjoint_error','gradient_cosine',
                'independent_state_data_error'):
        values = [_number(r.get(key)) for r in primary]
        values = [v for v in values if v is not None]
        rows.append({'metric': key, 'available_same_estimate_conditions': len(values),
                     'expected_conditions': 32, 'minimum': min(values) if values else None,
                     'median': statistics.median(values) if values else None,
                     'maximum': max(values) if values else None,
                     'scope': 'available R16 legal-estimate evaluator tasks; missing12 not replaced'})
    return rows


def _save_figure(fig, stem, directory, book, plt):
    book.check()
    with book.span('report_figure_export', reporting_figures=1):
        fig.savefig(directory/(stem+'.png'), dpi=180, bbox_inches='tight')
        fig.savefig(directory/(stem+'.pdf'), bbox_inches='tight')
    plt.close(fig)
    return {'name': stem, 'png': str(directory/(stem+'.png')), 'pdf': str(directory/(stem+'.pdf'))}


def _plot_anatomy(records, config, directory, book, plt):
    fig, axes = plt.subplots(1, 3, figsize=(16, 5), constrained_layout=True)
    methods = list(dict.fromkeys(r.get('method') for r in records))
    for background, marker in (('weak', 'o'), ('ring', 's')):
        subset = [r for r in records if r.get('background') == background and r.get('status') == 'OK']
        for ax, key in zip(axes, ('material_to_data_transfer_error', 'adjoint_pullback_error', 'actual_rank')):
            points = [(methods.index(r['method']), _number(r.get(key))) for r in subset]
            points = [(x, y) for x, y in points if y is not None]
            if points:
                ax.plot([p[0] for p in points], [p[1] for p in points], marker, label=background)
            ax.set_xticks(range(len(methods)), methods, rotation=75, ha='right', fontsize=7)
            ax.set_title(key.replace('_', ' '))
        axes[0].axhline(config['gates']['G2_task_error_max'], color='.5', ls='--', lw=.7)
        axes[1].axhline(config['gates']['G2_task_error_max'], color='.5', ls='--', lw=.7)
    axes[0].legend()
    fig.suptitle('A1 tiny 2-D physical anatomy; no reconstructed images or imaging gate')
    return _save_figure(fig, 'anatomy_task_errors_and_rank', directory, book, plt)


def _plot_parent(parent_rows, config, directory, book, plt):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    for ax, metric in zip(axes, ('material_nrmse', 'delta_nrmse')):
        drawn = False
        for method in config['methods']:
            subset = [r for r in parent_rows if r['metric'] == metric and r['method'] == method]
            valid = [(r['parent_id'], r['official_parent_mean']) for r in subset if r['complete']]
            if valid:
                ax.plot([v[0] for v in valid], [v[1] for v in valid], 'o-', label=method)
                drawn = True
        if not drawn:
            ax.text(.5, .5, 'NO COMPLETE PARENT MEAN\nFailed conditions retained', ha='center',
                    va='center', transform=ax.transAxes)
        ax.set_xticks(config['parents'])
        ax.set_title(metric.replace('_', ' ')); ax.set_xlabel('Exposed synthetic parent')
        if drawn:
            ax.legend(fontsize=7)
    fig.suptitle('Official parent aggregation requires every frozen condition; no success-only fill')
    return _save_figure(fig, 'parent_metrics_complete_only', directory, book, plt)


def _plot_descriptive(matrix, config, directory, book, plt):
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    for row_index, background in enumerate(('weak', 'ring')):
        for col_index, metric in enumerate(('material_nrmse', 'delta_nrmse')):
            ax = axes[row_index, col_index]
            for method in ('L', 'F', 'R16'):
                subset = [r for r in matrix if r['background'] == background and r['method'] == method
                          and r.get('status') == 'OK' and _number(r.get(metric)) is not None]
                for parent in config['parents']:
                    selected = [r for r in subset if str(r['parent_id']) == str(parent)]
                    if selected:
                        ax.scatter([parent]*len(selected), [_number(r[metric]) for r in selected],
                                   s=18, alpha=.65, label=method if parent == config['parents'][0] else None)
            ax.set_xticks(config['parents']); ax.set_title(background+'; '+metric)
            ax.set_ylabel('Per-condition NRMSE'); ax.legend(fontsize=8)
    fig.suptitle('Available per-condition values only: descriptive, not parent means or gate evidence')
    return _save_figure(fig, 'descriptive_background_conditions', directory, book, plt)


def _plot_closure(matrix, tasks, config, directory, book, plt):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for background, marker in (('weak', 'o'), ('ring', 's')):
        rows = [r for r in matrix if r['background'] == background and r['method'] == 'R16'
                and r.get('status') == 'OK' and _number(r.get('rho_closure')) is not None]
        axes[0].scatter([_number(r.get('relative_feedback_signal')) for r in rows],
                        [_number(r['rho_closure']) for r in rows], marker=marker, label=background)
    axes[0].axhline(config['gates']['G3_closure_ratio_max'], color='k', ls='--', lw=.8)
    axes[0].set(xlabel='Full-minus-linear data signal (absolute norm)', ylabel='Closure ratio')
    rows = [r for r in tasks if r.get('method') == 'R16' and r.get('status') == 'OK'
            and _number(r.get('independent_transfer_error')) is not None
            and _number(r.get('independent_adjoint_error')) is not None]
    axes[1].scatter([_number(r['independent_transfer_error']) for r in rows],
                    [_number(r['independent_adjoint_error']) for r in rows], s=24)
    limit = config['gates']['G2_task_error_max']
    axes[1].axvline(limit, color='k', ls='--', lw=.8); axes[1].axhline(limit, color='k', ls='--', lw=.8)
    axes[1].set(xlabel='Independent material-to-data error', ylabel='Independent adjoint error')
    axes[0].legend()
    fig.suptitle('R16 available diagnostics; undefined/no-resolvable ratios omitted only from axes, retained in CSV')
    return _save_figure(fig, 'closure_and_independent_tasks', directory, book, plt)


def _plot_runtime(runtime, directory, book, plt):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), constrained_layout=True)
    for ax, background in zip(axes, ('weak', 'ring')):
        for method in ('L', 'F', 'R16'):
            for parent in dict.fromkeys(r['parent_id'] for r in runtime if r['background'] == background):
                subset = [r for r in runtime if r['background'] == background and r['method'] == method
                          and r['parent_id'] == parent and r['amortized_per_image_s'] is not None]
                if subset:
                    ax.plot([r['N'] for r in subset], [r['amortized_per_image_s'] for r in subset],
                            'o-', label=f'{method}; p{parent}')
        ax.set_xscale('log'); ax.set_xticks([1, 10, 100], ['1', '10', '100'])
        ax.set(xlabel='Declared reuse count N', ylabel='Accounted seconds per image', title=background)
        if ax.lines:
            ax.legend(fontsize=7)
        else:
            ax.text(.5, .5, 'NO COMPLETE MATCHED TIMING', ha='center', transform=ax.transAxes)
    fig.suptitle('Measured setup incl. geometry + warm median; N=10/100 are accounting projections')
    return _save_figure(fig, 'runtime_reuse_accounting', directory, book, plt)


def _montages(root, config, matrix, directory, data_directory, book, plt):
    import numpy as np
    figures = []
    pixels = []
    parents = [config['parents'][config['parent_families'].index(f)]
               for f in dict.fromkeys(config['parent_families'])]
    amplitude = config['amplitudes'][-1]
    index = {(r['case_id'], r['method']): r for r in matrix}
    for background in ('weak', 'ring'):
        cache_path = root/'results/b0/cache'/f'{background}_background.npz'
        if not cache_path.exists():
            continue
        with np.load(cache_path, allow_pickle=False) as archive:
            chi_b = archive['chi_b'].copy()
        for parent in parents:
            book.check()
            case = _case_id(background, parent, amplitude, 20)
            truth_path = root/'results/b0/data/offline'/f'{background}_{parent}_{amplitude}.npz'
            series = [('Truth (exposed)', None, 'NOT_RUN_MISSING_ARRAY')]
            if truth_path.exists():
                with np.load(truth_path, allow_pickle=False) as archive:
                    series[0] = ('Truth (exposed)', archive['truth'].copy(), 'EVALUATOR_TRUTH')
            for method in ('L', 'F', 'R16'):
                row = index.get((case, method), {})
                path = root/'results/b0/images'/f'{case}_{method}.npz'
                value = None
                if row.get('status') == 'OK' and path.exists():
                    with np.load(path, allow_pickle=False) as archive:
                        value = archive['chi'].copy()
                series.append((method, value, row.get('status', 'NOT_RUN_MISSING_RECORD')))
            fig, axes = plt.subplots(2, 4, figsize=(12, 5.3), constrained_layout=True)
            delta = [value-chi_b for _, value, _ in series if value is not None]
            limits = [max((float(np.max(np.abs(v.real if channel == 0 else v.imag)))
                           for v in delta), default=1.) for channel in (0, 1)]
            for column, (label, value, status) in enumerate(series):
                if value is None:
                    pixels.append({'case_id': case, 'series': label, 'status': status})
                else:
                    d = value-chi_b
                    for cell, item in enumerate(d):
                        pixels.append({'case_id': case, 'series': label, 'status': status,
                                       'cell': cell, 'row': cell//config['grid'], 'column': cell%config['grid'],
                                       'real_delta_chi': float(item.real), 'imag_delta_chi': float(item.imag)})
                for channel in (0, 1):
                    ax = axes[channel, column]
                    ax.set_title(label + (' Re(delta chi)' if channel == 0 else ' Im(delta chi)'), fontsize=9)
                    if value is None:
                        ax.text(.5, .5, status.replace('_', '\n'), ha='center', va='center', fontsize=7)
                        ax.set_axis_off()
                        continue
                    image = (value-chi_b).reshape((config['grid'],)*2)
                    image = image.real if channel == 0 else image.imag
                    bound = limits[channel] or 1.
                    artist = ax.imshow(image, origin='lower', extent=(-.5, .5, -.5, .5),
                                       cmap='coolwarm', vmin=-bound, vmax=bound)
                    fig.colorbar(artist, ax=ax, shrink=.75)
            fig.suptitle(case+'; fixed first parent/family, max frozen amplitude, 20 dB; shared scales per channel')
            figures.append(_save_figure(fig, 'image_'+case, directory, book, plt))
    _write_csv(data_directory/'image_pixels.csv', pixels)
    return figures


def _reports(config, root, anatomy, gate, matrix, parents, tasks, timing, runtime,
             preparations, failures, jobs, confirmation, confirmation_rows, figures, manifest,
             paired_background, background_summary, task_summary):
    statuses = Counter(r.get('status', 'UNKNOWN') for r in matrix)
    expected = len(matrix)
    unit = []
    for job in jobs:
        tests = _read_json(job['directory']/'UNIT_TESTS.json', {})
        if tests:
            unit.append({'job': job['row']['job'], **tests})
    gates = [{'gate': key, 'status': gate.get(key, {}).get('status', 'NOT_RUN'),
              'threshold': gate.get(key, {}).get('threshold', gate.get(key, {}).get('thresholds'))}
             for key in ('G1', 'G2', 'G3', 'G4', 'G5')]
    parent_table = [r for r in parents if r['metric'] == 'material_nrmse']
    case_table = [{**r, 'rho_display': r.get('rho_closure') or
                   ('UNDEFINED_NO_RESOLVABLE_FEEDBACK' if r.get('closure_status') == 'NO_RESOLVABLE_FEEDBACK' else None)}
                  for r in matrix if r['method'] in ('L', 'F', 'R16')]
    no_image = [r for r in matrix if r.get('status') != 'OK']
    method_status = [{'method': method, 'statuses': dict(Counter(r.get('status') for r in matrix if r['method'] == method)),
                      'joint_quality_rows': gate.get('G5', {}).get('quality_rows_by_method', {}).get(method)}
                     for method in config['methods']]
    baseline = [{'method': key, 'status': value} for key, value in config.get('equivalent_methods', {}).items()]
    baseline += [{'method': key, 'status': value} for key, value in config.get('missing_baselines', {}).items()]
    runtime_columns = [('case_id', 'condition'), ('method', 'method'), ('N', 'N'), ('valid_repeats', '有效重复'),
                       ('geometry_setup_s', 'geometry s'), ('setup_including_geometry_s', '一次setup s'),
                       ('warm_median_s', 'warm median s'), ('cold_in_memory_image_s', '实测组成cold s'),
                       ('amortized_per_image_s', '摊销/image s'), ('timing_status', 'status')]
    pair_columns = [('background','背景'),('parent_id','parent'),('paired_conditions','成对条件'),
                    ('expected_background_conditions','应有'),('L_available_paired_mean','L NRMSE'),
                    ('F_available_paired_mean','F NRMSE'),('R16_available_paired_mean','R16 NRMSE'),
                    ('F_gain_percent','F改善%'),('R_gain_percent','R改善%'),('R_gain_retention','R保留比')]
    counterexamples = gate.get('G2', {}).get('observed_task_counterexamples', [])
    evidence = [{'level': '理论', 'status': 'FORMULAS_AND_COUNTEREXAMPLES_ONLY', 'limit': '来源 theory/；不产生图像或速度结论'},
                {'level': 'A0/unit', 'status': 'PASS' if unit and all(r.get('passed') for r in unit) else 'NOT_RUN_OR_FAILED',
                 'limit': '离散代数与实现核验；不能替代成像'},
                {'level': 'A1 tiny 2D', 'status': anatomy.get('status', 'NOT_RUN'),
                 'limit': '8×8空间剖析；无材料重建图像'},
                {'level': 'B0 2D imaging', 'status': dict(statuses), 'limit': '四个已公开合成parent，失败条件全部保留'},
                {'level': '3D dyadic DDA', 'status': confirmation.get('status', 'NOT_RUN'),
                 'limit': '有条件最多4状态；不能将2D解释成3D'},
                {'level': '时间/成本', 'status': gate.get('G5', {}).get('status', 'NOT_RUN'),
                 'limit': '实测warm与组成计费；N=10/100未实际重复部署'},
                {'level': 'NN训练', 'status': 'NOT_RUN_TRAINING_DISABLED', 'limit': 'C/D保持关闭'}]
    figure_lines = '\n'.join(f"![{f['name']}](results/report/figures/{Path(f['png']).name})\n\n"
                             f"[PDF](results/report/figures/{Path(f['pdf']).name})" for f in figures)
    report = f'''# A24：source-anchored OM 与 relative feedback 研究报告

协议：`{config['protocol_id']}`。生成时间：{manifest['generated_utc']}。
本报告整理已记录证据，最终科学解释与新颖性判断由父 Codex 审阅。
当前冻结 Gate decision：`{gate.get('decision', 'NOT_RUN')}`。

## 1. 从最开始最基础的 literature review 和 background

逆散射由外部电磁观测恢复材料。材料改变内部场，内部场又决定材料诱导电流，
因此一次线性回投不能自动保留多重散射。SOM/TSOM处理数据可确定与模糊电流；
内部传播谱截断与已知照明forcing的种子分解是不同操作。
已有背景、prior、affine lifting及低秩消元构成这里的比较基础。
closest prior与原文取得层级见 [来源与阅读账本](theory/SOURCES_AND_READING_LEDGER.md)；
这些背景解释不等于本实验建立新的理论结论。

固定参考材料给出已知场 e_b 和数据 y_b。相对材料源 w 汇集材料变化引起的新响应，
反馈算子把这个响应再次传播回材料内部。完整关系是
`w=(I-H G_b)^(-1) H e_b`、`y=y_b+D_b w`，其中 `H=diag(a(chi)-a(chi_b))`。
L保持完整本构转换但去掉相对反馈；F在当前合法估计处使用完整物理反馈及伴随；
R16仅将内部传播替换成预注册低秩近似。F没有读取truth-state Jacobian。
共同TV和共同初始化用于避免把不同材料先验的收益算成反馈收益。

当同一U包含全部参考source currents时，可删的是已为零的forcing-P。
它不允许在换U或换receiver方向后宣称“P本身无效”。TSOM的intersection、projection
与restricted-G空间也不能混写。相应边界见
[代数审计](theory/TSOM_SOMNET_ALGEBRA_AUDIT.md)、
[理论与反例](theory/THEOREMS_AND_COUNTEREXAMPLES.md)、
[relative架构](theory/RELATIVE_FEEDBACK_OM_ARCHITECTURE.md)。

## 2. 证据层级与冻结范围

{_table(evidence, [('level','层级'),('status','实测状态'),('limit','解释范围')])}

二维主平台为{config['grid']}×{config['grid']} TM Helmholtz VIE，
{config['sources']} sources、{config['receivers']} receivers，完整材料mass坐标，
双背景、四parent、双幅度与无噪/20 dB，共32观测条件。
{expected}个方法条件记录中状态分布为 `{dict(statuses)}`。
32个观测条件共享四个几何parent；不能当作32个独立对象。
这些parent及其生成配置已暴露，无blind holdout或泛化统计证据。

2D使用原A2离散核，时间约定exp(-i omega t)、outgoing i H0^(1)/4 Green，
off-diagonal包含k² cell area，self cell沿用等面积圆盘积分。
其本构a(chi)=chi、a'=1。因此2D的linear-a加exact conversion与L相同，
不能声称检验了3D非线性极化率。三维分支沿用冻结A20/A23 dyadic DDA、
原polarizability/a'及absorbed self-term；不同质量归一与三分量电流合同独立实现。
物理源版本见 [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json)，不新增SHA256检查。

全部方法使用同一mass度量、Re/Im联合各向同性TV、物理box
Re[{config['real_lower']},{config['real_upper']}]、Im[{config['imag_lower']},{config['imag_upper']}]，
同一K={config['blocks']}更新和最多一次half-step retry。
TV rule：`{config['tv_rule']}`。step rule：`{config['step_rule']}`。
prox固定上限{config['prox_max_iter']}，KKT tolerance={config['prox_tolerance']}；
没有事后放宽容差、加迭代、改rank或换先验。

## 3. 实现核验与tiny anatomy

{_table(unit, [('job','job'),('tests_run','tests'),('failures','failures'),('errors','errors'),('passed','passed')])}

Anatomy身份判据：`{anatomy.get('G1_status', 'NOT_RUN')}`，
scope：`{anatomy.get('scope', 'NOT_RUN')}`；共{len(anatomy.get('records', []))}条空间诊断。
同U anchor pair与Schur/adjoint一致性来自这些核验；它们没有重建图像。
剖析原始plot data保留actual ranks、材料→数据与adjoint任务误差、负向control与失败。
`offline_s`中共享setup可在多条记录描述性重复，不能直接把这些行求和当总成本。

## 4. 二维成像、完整parent与失败

{_table(method_status, [('method','方法'),('statuses','全部状态'),('joint_quality_rows','达到联合quality数量')])}

下面只在每个parent全部8个条件都有效时给出official mean；缺少或失败的条件
不填零、不做success-only主均值。其余已获得的单条件图像仅作描述性检查。

{_table(parent_table, [('parent_id','parent'),('family','family'),('method','方法'),('valid_conditions','valid'),('expected_conditions','expected'),('official_parent_mean','official full-chi NRMSE')])}

共同初始化的TV prox未达到冻结KKT阈值会使所有方法标记
`COMMON_INITIALIZATION_FAILED`。这些是共同优化入口的瓶颈，不能解释为Maxwell
恒等式或G1失败，也不能从主比较移除。单方法的`FAILED`另行保留。
failure ledger：{len(failures)}条；未输出材料的条件：{len(no_image)}条。
raw condition矩阵见 [condition_plot_data.csv](results/report/plot_data/condition_plot_data.csv)，
完整失败行见 [condition_failures.csv](results/report/plot_data/condition_failures.csv)。

closure分母低于实际noise norm或数值floor时为NO_RESOLVABLE_FEEDBACK：
rho未定义，不填0，也不将小ratio当证据。此状态与未运行、预测失败分别保存。
独立task audit在同一在线R估计处使用固定material probes/data loads，
其已获诊断不能补足缺失条件。普通adjoint与F使用同一完整离散forward/adjoint合同。

### 4.1 同条件配对的描述性background子组

下表只比较同一条件的L/F/R16，按每个parent先计算平均与百分比gain。
weak背景每个parent四条件完整，因此允许四parent等权的weak子组描述；
它不等于预注册跨两背景的full-eight official parent mean。
ring的部分配对值保留，但不组成完整四parent背景均值，不用于Gate3。

{_table(paired_background, pair_columns)}

{_table(background_summary, [('background','背景'),('complete_background_parents','完整parent数'),('L_available_paired_mean','等权L'),('F_available_paired_mean','等权F'),('R16_available_paired_mean','等权R16'),('F_gain_percent','parent等权F改善%'),('R_gain_percent','parent等权R改善%'),('status','范围')])}

同一合法R16估计处的已获task范围如下；20个可用估计不替换应有32个条件。
范围是已观测值的描述，不给缺失条件赋值。

{_table(task_summary, [('metric','任务量'),('available_same_estimate_conditions','可用条件'),('expected_conditions','应有条件'),('minimum','min'),('median','median'),('maximum','max')])}

## 5. 缺失与等价基线

{_table(baseline, [('method','baseline'),('status','合同或缺失原因')])}

可靠迭代SOM/FFT-TSOM、CIE-I/WT-TSOM的缺失仍限制全算法优越性判断。
已实现的空间anatomy或Gaussian参数拟合不能替代同full-grid prior的这些基线。
R32和local R16为预注册diagnostic arms，不能在test后择优替代primary R16。

## 6. Gate原样记录与科学范围

{_table(gates, [('gate','Gate'),('status','保存状态'),('threshold','冻结阈值')])}

G2保存状态为`{gate.get('G2', {}).get('status', 'NOT_RUN')}`；
已观测独立任务反例数为{len(counterexamples)}。任何有效条件超过冻结5%任务误差
或低于0.99方向cosine即可否定“所有条件均满足”的当前R16充分性要求，
缺失条件不能擦除这个反例。因此observed-task FAIL与image coverage不足分开记录。
G3保存状态为`{gate.get('G3', {}).get('status', 'NOT_RUN')}`；HOLD来自完整parent图像比较不足，
不是由R16任务反例自动判定F反馈headroom不存在。G1身份核验的PASS也不抵消任务反例。
F headroom、R gain retention与两家族支持只按保存的完整parent合同判断。
G5保存joint-quality命中数为{gate.get('G5', {}).get('quality_rows', 'NOT_RUN')}；
`{gate.get('G5', {}).get('status', 'NOT_RUN')}`下不能从较差图像的时间称更快成像算法。
最终结论需同时审阅失败、完整full-data验证及缺失baseline。

{_table(counterexamples, [('case_id','已观测反例'),('transfer_error','material-transfer error'),('adjoint_error','adjoint error'),('gradient_cosine','gradient cosine')])}

首次controller缺失优先的历史结果保存在
[GATE_DECISION_INITIAL_CONTROLLER.json](results/b0/GATE_DECISION_INITIAL_CONTROLLER.json)。
父线程修正了已观测反例与覆盖不足的判定优先级；阈值、数值结果与冻结协议未改，
未为此重跑物理或成像。本报告只读取修正后保存决策。

## 7. 成本、cold/warm与N=1/10/100

计时只报告预注册矩阵中的实际重复，warm包含共同初始化与三步重建。
一次内存中部署setup包括image记录的shared background、method setup及对应job实测
`tm2d_geometry_setup`。cache export是科学存档I/O，计入inclusive science job time，
不强加给内存中部署setup。job001完成全部weak16条件及ring/2401/幅度.3的两条件；
job002从checkpoint补齐其它记录。成功image使用这一透明恢复边界关联几何成本。
原`cold_image_s`没有geometry，`cold_in_memory_image_s=raw cold_image_s+实际job geometry`。
表中另给`setup+warm median`的计费组成；不将它假称新测cold deployment。
restart的setup全部进入实际job总wall；表中的同一setup仅重复展示给不同N，不能求和。
无法关联setup与job时cold为空，不假定geometry免费。

N=1的cold组成=`setup+warm`，N=10/100的每图摊销=`warm+setup/N`，
total=`setup+N*warm`。它们是实测组成的计费投影，N次完整部署未执行。
剩余cache/data I/O、失败、独立评价与reporting都在inclusive job wall内，
未单独分段I/O不按0隐藏，也不虚构每次重新setup。
必须从磁盘加载保存cache的cold部署未计时，保持`disk_loaded_cache_status=NOT_RUN`。
这里的cold为内存中setup与重建组成，不包含完整程序启动或磁盘cache加载的实测。

{_table(runtime, runtime_columns)}

{_table([j['row'] for j in jobs], [('job','job'),('command','命令'),('stage','stage'),('status','结果'),('wall_seconds','inclusive wall s'),('process_cpu_seconds','CPU s'),('new_clean_labels','new labels'),('geometry_setup_s','geometry s')])}

## 8. 三维与训练状态

3D保存状态：`{confirmation.get('status', 'NOT_RUN')}`，已记录{len(confirmation_rows)}条件。
仅当先决Gate允许才运行最多4个6³ dyadic states；若未运行，任何3D图像、
headroom、quality或速度均为NOT_RUN。2D数据不得补成3D证据。
3D repeated timing状态：`{confirmation.get('repeated_timing', 'NOT_RUN')}`。
NN C/D：`{gate.get('G4', {}).get('status', 'NOT_RUN_TRAINING_DISABLED')}`。
不据此报告训练收益、自动扩数据或更高分辨率验证。

## 9. 图与完整单条件主臂记录

图像选取固定每家族第一个parent、冻结最大幅度、20 dB及两个背景；没有按结果选优。
Re/Im各通道在truth与全部可用方法间共享色标；失败panel明确显示状态。
所有科学图同时保存PNG、PDF与raw plot-data CSV。

{figure_lines}

{_table(case_table, [('case_id','condition'),('method','方法'),('status','状态'),('material_nrmse','full chi NRMSE'),('delta_nrmse','delta NRMSE'),('full_data_relative_residual','无噪relative residual'),('full_data_white_residual','noise-white residual'),('rho_display','rho / undefined')])}

原始决策：[GATE_DECISION.json](results/b0/GATE_DECISION.json)。
阈值、失败、缺失和NOT_RUN保留；本自动汇总不会授予新的GO或新颖性结论。
'''
    execution = f'''# A24 execution report

Protocol `{config['protocol_id']}`; generated {manifest['generated_utc']}.
Report generation is evaluator-only and charged to the caller's B0 ledger.
Gate decisions are copied from saved evidence; no experiment or numerical setting is changed.

## Evidence and failures

{_table(evidence, [('level','Level'),('status','Recorded status'),('limit','Scope')])}

Condition records: {expected}; statuses `{dict(statuses)}`. All {len(no_image)} non-OK
conditions are retained. COMMON_INITIALIZATION_FAILED identifies the frozen TV-prox
KKT cap at the shared initializer; it does not override the passing Maxwell identity tests.
Four exposed synthetic parents are the statistical units. Official parent means require
all eight conditions, and unavailable metrics remain null.

{_table(gates, [('gate','Gate'),('status','Status'),('threshold','Frozen threshold')])}

G2 observed-task counterexamples are failures of the frozen universal R16 task
criterion, even with missing image conditions. G3 image/headroom coverage remains
separate. Missing observations cannot erase an observed valid counterexample;
passing G1 identities cannot substitute for G2 accuracy.

{_table(counterexamples, [('case_id','Observed counterexample'),('transfer_error','Transfer error'),('adjoint_error','Adjoint error'),('gradient_cosine','Gradient cosine')])}

Descriptive paired background subgroups (not full-eight official parent means):

{_table(paired_background, pair_columns)}

{_table(background_summary, [('background','Background'),('complete_background_parents','Complete parents'),('F_gain_percent','Equal-parent F gain %'),('R_gain_percent','Equal-parent R gain %'),('status','Scope')])}

Available legal-estimate R16 task ranges; missing conditions remain missing:

{_table(task_summary, [('metric','Metric'),('available_same_estimate_conditions','Available'),('expected_conditions','Expected'),('minimum','Min'),('median','Median'),('maximum','Max')])}

## Actual inclusive costs and provenance

{_table([j['row'] for j in jobs], [('job','Job'),('command','Command'),('stage','Stage'),('status','Status'),('wall_seconds','Wall s'),('process_cpu_seconds','CPU s'),('new_clean_labels','New labels'),('geometry_setup_s','Geometry s'),('source_commit','Source commit')])}

Both failed and resumed jobs are charged. Sum inclusive job receipts, never nested span
walls. The current report job snapshot ends before this report's final export; its final
job_receipt.json is authoritative for total reporting cost.

Cold accounting adds the actual per-job tm2d_geometry_setup omitted by the driver's
original cold_image_s: cold_in_memory_image_s = raw cold_image_s + source-job geometry.
The recorded recovery boundary assigns all weak conditions plus ring2401/.3 zero/20dB
to job001 and successful remaining checkpoint images to job002. Actual image shared
and method setup components are used; unresolved/failed associations stay null.
Archive cache export is science I/O in full job wall, not mandatory in-memory setup.
Disk-loaded-cache deployment cold is NOT_RUN. Remaining unsegmented cache/data I/O
stays in full job wall overhead. N=10/100 values are accounting
projections from a single setup and measured warm medians, not measured N deployments.
No time-to-image superiority is asserted outside the joint quality region.

{_table(runtime, runtime_columns)}

## Preserved missing baselines and condition failures

{_table(baseline, [('method','Baseline'),('status','Status or equivalence')])}

{_table(no_image, [('case_id','Condition'),('method','Method'),('status','Failure/missing status'),('error','Recorded reason')])}

## Deliverables and reproduction

- [Chinese research report](A24_RESEARCH_REPORT_ZH.md)
- [Report manifest](results/report/REPORT_MANIFEST.json)
- `results/report/figures/`: scientific PNG and PDF exports.
- `results/report/plot_data/`: all plotted condition, parent, task, timing, preparation,
  anatomy, failure and image-pixel data, with nulls/failure statuses retained.
- Frozen sources: [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json),
  [config](configs/a24_frozen.json), job manifests and receipts under `results/jobs/`.

Parent invocation: `build_report(config, repo_root, book)` within the active B0 ledger.
Report generation reads recorded evaluator outputs only; it does not invoke a physical
adapter, generate clean labels, run tests, train, recompute gates or publish anything.
Scientific interpretation and any public release remain with the parent reviewer.
'''
    (root/'A24_RESEARCH_REPORT_ZH.md').write_text(report, encoding='utf-8')
    (root/'A24_EXECUTION_REPORT.md').write_text(execution, encoding='utf-8')


def build_report(config, repo_root, book):
    """Generate reports/figures/CSV from existing outputs under B0 accounting."""
    started = time.perf_counter()
    root = Path(repo_root).resolve()
    output = root/'results/report'
    figures_dir, data_dir = output/'figures', output/'plot_data'
    figures_dir.mkdir(parents=True, exist_ok=True); data_dir.mkdir(parents=True, exist_ok=True)
    with book.scope('offline_reporting'), book.span('report_generation', reporting_calls=1) as span:
        book.check()
        anatomy_path = root/'results/anatomy/ANATOMY.json'
        if not anatomy_path.exists():
            anatomy_path = root/'results/anatomy/anatomy.json'
        anatomy = _read_json(anatomy_path, {})
        gate = _read_json(root/'results/b0/GATE_DECISION.json', {})
        raw = _read_csv(root/'results/b0/CASES.csv')
        tasks = _read_csv(root/'results/b0/TASK_AUDIT.csv')
        timing = _read_csv(root/'results/b0/TIMING.csv')
        preparations = _read_csv(root/'results/b0/PREPARATION.csv')
        failures = _read_jsonl(root/'results/b0/FAILURE_LEDGER.jsonl')
        jobs = _jobs(root, book)
        matrix = _conditions(config, raw)
        parents = _parent_summary(config, matrix)
        runtime = _runtime(config, matrix, preparations, timing, jobs)
        paired_background, background_summary = _descriptive_pairs(config, matrix)
        task_summary = _task_ranges(tasks)
        confirmation = _read_json(root/'results/confirmation3d/SUMMARY.json', {})
        confirmation_rows = _read_csv(root/'results/confirmation3d/CASES.csv')
        anatomy_fields = ('case_id','background','method','status','reason','actual_rank','retained_rank',
                          'correction_rank','union_rank','full_data_residual','state_residual',
                          'material_to_data_transfer_error','adjoint_pullback_error','gradient_cosine',
                          'adjoint_error','offline_s','online_s','core_margins')
        tables = {'condition_plot_data': matrix, 'condition_raw_records': raw,
                  'condition_failures': [r for r in matrix if r.get('status') != 'OK'],
                  'parent_metrics': parents, 'task_plot_data': tasks, 'timing_raw': timing,
                  'paired_background_parent_description': paired_background,
                  'weak_equal_parent_description': background_summary,
                  'R16_same_estimate_task_ranges': task_summary,
                  'runtime_N1_N10_N100': runtime, 'preparation_raw': preparations,
                  'failure_ledger': failures, 'job_costs': [j['row'] for j in jobs],
                  'confirmation3d_conditions': confirmation_rows,
                  'anatomy_plot_data': [{k:r.get(k) for k in anatomy_fields}
                                        for r in anatomy.get('records', [])]}
        for name, rows in tables.items():
            book.check(); _write_csv(data_dir/(name+'.csv'), rows)
        manifest = {'protocol_id': config['protocol_id'],
                    'generated_utc': datetime.now(timezone.utc).isoformat(),
                    'status': 'REPORT_GENERATED_PENDING_PARENT_SCIENTIFIC_REVIEW',
                    'gate_decision': gate.get('decision', 'NOT_RUN'),
                    'gate_statuses': {key:gate.get(key,{}).get('status','NOT_RUN')
                                      for key in ('G1','G2','G3','G4','G5')},
                    'condition_statuses': dict(Counter(r.get('status') for r in matrix)),
                    'gate_thresholds_changed': False, 'physics_actions': 0, 'new_labels': 0,
                    'plots_scope': 'descriptive scientific figures from recorded evaluator outputs',
                    'reuse_timing_scope': 'measured components; N repeated deployments NOT_RUN',
                    'read_failures': [], 'figures': [], 'plot_data_csvs': list(tables)}
        figures = []
        try:
            book.check()
            import matplotlib
            matplotlib.use('Agg')
            from matplotlib import pyplot as plt
            with plt.rc_context({'font.size': 9, 'axes.spines.top': False,
                                 'axes.spines.right': False, 'pdf.fonttype': 42}):
                calls = [lambda: _plot_anatomy(anatomy.get('records', []), config, figures_dir, book, plt),
                         lambda: _plot_parent(parents, config, figures_dir, book, plt),
                         lambda: _plot_descriptive(matrix, config, figures_dir, book, plt),
                         lambda: _plot_closure(matrix, tasks, config, figures_dir, book, plt),
                         lambda: _plot_runtime(runtime, figures_dir, book, plt)]
                for call in calls:
                    book.check()
                    try:
                        figures.append(call())
                    except BudgetExceeded:
                        raise
                    except Exception as error:
                        manifest['read_failures'].append({'phase':'plot','error':repr(error)})
                        plt.close('all')
                try:
                    figures.extend(_montages(root, config, matrix, figures_dir, data_dir, book, plt))
                except BudgetExceeded:
                    raise
                except Exception as error:
                    manifest['read_failures'].append({'phase':'montage','error':repr(error)})
                    plt.close('all')
        except ImportError as error:
            manifest['read_failures'].append({'phase':'plot_import','error':repr(error)})
        manifest['figures'] = figures
        manifest['elapsed_seconds_before_final_export'] = time.perf_counter()-started
        _reports(config, root, anatomy, gate, matrix, parents, tasks, timing, runtime,
                 preparations, failures, jobs, confirmation, confirmation_rows, figures, manifest,
                 paired_background, background_summary, task_summary)
        write_json(output/'REPORT_MANIFEST.json', manifest)
        span.update(report_root=str(output), figures=len(figures), condition_rows=len(matrix),
                    plot_failures=len(manifest['read_failures']))
        book.check()
    return {'status': 'REPORT_GENERATED', 'scientific_review': 'PARENT_REVIEW_REQUIRED',
            'research_report': str(root/'A24_RESEARCH_REPORT_ZH.md'),
            'execution_report': str(root/'A24_EXECUTION_REPORT.md'),
            'manifest': str(output/'REPORT_MANIFEST.json'), 'figures': len(figures),
            'plot_failures': manifest['read_failures'], 'elapsed_seconds': time.perf_counter()-started}
