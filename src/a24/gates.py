"""Unchanged package thresholds; failures/missing evidence cannot become PASS."""
from __future__ import annotations
import csv,json
from pathlib import Path
import numpy as np
from a20.costs import write_json

def csv_rows(path):
    if not Path(path).exists(): return []
    with Path(path).open(newline='',encoding='utf-8') as f: return list(csv.DictReader(f))

def number(row,key):
    try:
        value=float(row.get(key,''))
        return value if np.isfinite(value) else None
    except (TypeError,ValueError): return None

def parent_means(rows,method,parents,key):
    means={};counts={}
    for parent in parents:
        subset=[r for r in rows if r['method']==method and int(r['parent_id'])==parent]
        valid=[number(r,key) for r in subset if r['status']=='OK']
        valid=[v for v in valid if v is not None]
        counts[str(parent)]={'expected':8,'rows':len(subset),'valid':len(valid)}
        means[str(parent)]=float(np.mean(valid)) if len(valid)==8 else None
    return means,counts

def decide(config,out,anatomy_path=None):
    out=Path(out);rows=csv_rows(out/'CASES.csv');tasks=csv_rows(out/'TASK_AUDIT.csv')
    parents=config['parents'];g=config['gates']
    anatomy={}
    if anatomy_path and Path(anatomy_path).exists(): anatomy=json.loads(Path(anatomy_path).read_text())
    G1={'status':anatomy.get('G1_status','NOT_RUN'),'threshold':g['G1_identity_max'],
        'numerical_evidence':anatomy.get('status','NOT_RUN')}
    l,lc=parent_means(rows,'L',parents,'material_nrmse')
    f,fc=parent_means(rows,'F',parents,'material_nrmse')
    r,rc=parent_means(rows,'R16',parents,'material_nrmse')
    complete=all(v is not None for table in (l,f,r) for v in table.values())
    gains=[]
    for index,parent in enumerate(parents):
        p=str(parent);lv,fv,rv=l[p],f[p],r[p]
        improvement=(lv-fv)/lv if lv and fv is not None else None
        retention=(lv-rv)/(lv-fv) if lv is not None and fv is not None and rv is not None and lv>fv else None
        gains.append({'parent_id':parent,'family':config['parent_families'][index],
                      'L':lv,'F':fv,'R16':rv,'F_relative_improvement':improvement,
                      'R_gain_retention':retention,
                      'R_relative_degradation_vs_F':rv/fv-1 if fv and rv is not None else None})
    primary_tasks=[t for t in tasks if t.get('method')=='R16']
    counterexamples=[]
    for t in primary_tasks:
        if t.get('status')!='OK': continue
        transfer=number(t,'independent_transfer_error');adjoint=number(t,'independent_adjoint_error')
        cosine=number(t,'gradient_cosine')
        if ((transfer is not None and transfer>g['G2_task_error_max'])
            or (adjoint is not None and adjoint>g['G2_task_error_max'])
            or (cosine is not None and cosine<g['G2_gradient_cosine_min'])):
            counterexamples.append({'case_id':t['case_id'],'transfer_error':transfer,
                                    'adjoint_error':adjoint,'gradient_cosine':cosine})
    task_complete=len(primary_tasks)==32 and all(t['status']=='OK' for t in primary_tasks)
    task_pass=task_complete and all(number(t,'independent_transfer_error') is not None
        and number(t,'independent_transfer_error')<=g['G2_task_error_max']
        and number(t,'independent_adjoint_error') is not None
        and number(t,'independent_adjoint_error')<=g['G2_task_error_max']
        and number(t,'gradient_cosine') is not None
        and number(t,'gradient_cosine')>=g['G2_gradient_cosine_min'] for t in primary_tasks)
    image_pass=complete and all(t['R_relative_degradation_vs_F']<=g['G2_image_degradation_max'] for t in gains)
    G2={'status':'FAIL' if counterexamples else 'PASS' if task_pass and image_pass
        else 'FAIL' if task_complete and complete else 'HOLD',
        'thresholds':{'task_max':g['G2_task_error_max'],'cosine_min':g['G2_gradient_cosine_min'],
                      'image_degradation_max':g['G2_image_degradation_max']},
        'independent_task_rows':len(primary_tasks),'expected_task_rows':32,
        'tasks_pass':task_pass,'image_pass':image_pass,
        'observed_task_counterexamples':counterexamples,
        'coverage_complete':bool(task_complete and complete),
        'missing_conditions_cannot_erase_observed_counterexample':True,
        'interpretation':'Independent task tests at same online R estimate; no truth-state Jacobian.'}
    pairs={}
    for row in rows: pairs.setdefault(row['case_id'],{})[row['method']]=row
    case_checks=[]
    m=2*config['sources']*config['receivers']
    for case,arms in pairs.items():
        fr=arms.get('F',{});rr=arms.get('R16',{})
        if fr.get('status')!='OK' or rr.get('status')!='OK':
            case_checks.append({'case_id':case,'status':'MISSING_OR_FAILURE','closure_pass':False,'data_pass':False});continue
        rho=number(rr,'rho_closure');sigma=number(rr,'sigma') or 0.
        if sigma>0:
            fdata=number(fr,'full_data_white_residual');rdata=number(rr,'full_data_white_residual')
            data_pass=fdata is not None and rdata is not None and rdata<=fdata+np.sqrt(m)
        else:
            fdata=number(fr,'full_data_relative_residual');rdata=number(rr,'full_data_relative_residual')
            data_pass=fdata is not None and rdata is not None and rdata<=fdata+1e-10
        case_checks.append({'case_id':case,'status':'OK','rho':rho,
            'closure_pass':rho is not None and rho<=g['G3_closure_ratio_max'],
            'data_pass':bool(data_pass),'F_full_residual':fdata,'R_full_residual':rdata})
    supported=[]
    for family in dict.fromkeys(config['parent_families']):
        candidates=[t for t in gains if t['family']==family and t['F_relative_improvement'] is not None
                    and t['F_relative_improvement']>=g['G3_F_improvement_min']]
        supported.append({'family':family,'headroom_parents':[t['parent_id'] for t in candidates],
                          'retained_parents':[t['parent_id'] for t in candidates if t['R_gain_retention'] is not None
                                               and t['R_gain_retention']>=g['G3_R_gain_retention_min']]})
    F_headroom=complete and all(t['headroom_parents'] for t in supported)
    retention_pass=complete and all(t['retained_parents'] for t in supported)
    closure_pass=len(case_checks)==32 and all(t['closure_pass'] for t in case_checks)
    data_pass=len(case_checks)==32 and all(t['data_pass'] for t in case_checks)
    G3={'status':'PASS' if F_headroom and retention_pass and closure_pass and data_pass else 'FAIL' if complete else 'HOLD',
        'F_headroom':bool(F_headroom),'R_retention_pass':bool(retention_pass),
        'closure_pass':bool(closure_pass),'data_budget_pass':bool(data_pass),
        'family_support':supported,'parent_means':gains,'case_checks':case_checks,
        'complete':bool(complete),'required_parent_counts':{'L':lc,'F':fc,'R16':rc},
        'thresholds':{'F_improvement':.10,'R_gain_retention':.80,'rho_closure_max':.5}}
    quality=[]
    for row in rows:
        if row['status']!='OK': continue
        full=number(row,'material_nrmse');delta=number(row,'delta_nrmse')
        sigma=number(row,'sigma') or 0.
        data=number(row,'full_data_white_residual' if sigma>0 else 'full_data_relative_residual')
        data_limit=1.2*np.sqrt(m) if sigma>0 else .05
        ok=(full is not None and full<=.35 and delta is not None and delta<=.60
            and data is not None and data<=data_limit and row.get('feasible') in ('True',True,'true'))
        quality.append({'case_id':row['case_id'],'method':row['method'],'quality':bool(ok),
                        'cold_image_s':number(row,'cold_image_s')})
    timing=csv_rows(out/'TIMING.csv');eligible_pairs=[]
    qby={}
    for row in quality:qby.setdefault(row['case_id'],{})[row['method']]=row
    for case,arms in qby.items():
        rr=arms.get('R16',{});lr=arms.get('L',{});fr=arms.get('F',{})
        if not rr.get('quality'):continue
        for method,baseline in [('L',lr),('F',fr)]:
            if not baseline.get('quality'):continue
            rtimes=[number(t,'warm_s') for t in timing if t['case_id']==case and t['method']=='R16' and t['status']=='OK']
            btimes=[number(t,'warm_s') for t in timing if t['case_id']==case and t['method']==method and t['status']=='OK']
            if len(rtimes)==5 and len(btimes)==5:
                ratio=float(np.median(rtimes)/np.median(btimes))
                eligible_pairs.append({'case_id':case,'baseline':method,'warm_ratio':ratio,
                    'cold_ratio':rr['cold_image_s']/baseline['cold_image_s']})
    if not any(t['quality'] for t in quality): cost_status='QUALITY_TARGET_NOT_REACHED'
    elif not eligible_pairs:cost_status='HOLD_NO_MATCHED_QUALITY_TIMING'
    else:cost_status='PASS' if np.median([t['warm_ratio'] for t in eligible_pairs])<=.8 else 'FAIL'
    G5={'status':cost_status,'threshold':.20,'quality_rows':sum(t['quality'] for t in quality),
        'quality_rows_by_method':{method:sum(t['quality'] for t in quality if t['method']==method) for method in config['methods']},
        'matched_quality_timing_pairs':eligible_pairs,'reuse_counts':[1,10,100],
        'missing_baselines':config['missing_baselines'],'global_algorithm_superiority':'NOT_ESTABLISHED'}
    stop='CURRENT_COMPRESSED_FEEDBACK_NO_GO' if G2['status']=='FAIL' else 'NO_FEEDBACK_IMAGING_HEADROOM' if complete and not F_headroom else 'HOLD_INCOMPLETE' if not complete else 'FURTHER_WORK_REQUIRES_NEW_AUTHORIZATION'
    decision={'protocol_id':config['protocol_id'],'G1':G1,'G2':G2,'G3':G3,
              'G4':{'status':'NOT_RUN_TRAINING_DISABLED'},'G5':G5,'decision':stop,
              'nn_training':'NOT_RUN','expansion':'NOT_AUTHORIZED','case_rows':len(rows),
              'expected_case_rows':32*len(config['methods']),'full_reference_is_truth_state':False,
              'statistics':'four parent clusters only; no formal generalization claim'}
    write_json(out/'GATE_DECISION.json',decision)
    return decision
