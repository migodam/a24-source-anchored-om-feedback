"""Fixed no-NN pilot; runtime image builder never receives evaluator truth."""
from __future__ import annotations
from pathlib import Path
import csv, json, time
import numpy as np
from scipy import linalg as la
from a20.costs import write_json, plain, BudgetExceeded
from .contracts import (OnlineObservation,NumericalFailure,pack,mass_pack,mass_unpack,
                        relative_error,online_config)
from .cases import backgrounds, material_pattern, noisy_observation

def write_csv(path,rows):
    rows=[plain(r) for r in rows]
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
        for r in rows:
            w.writerow({k:json.dumps(v) if isinstance(v,(dict,list)) else v for k,v in r.items()})

def append_failure(path,**record):
    with Path(path).open('a',encoding='utf-8') as f:
        f.write(json.dumps(plain(record),allow_nan=False)+'\n')

def prepare_background(cache,book,config):
    """Known background only; normalized Hessian spectral step, frozen rule."""
    with book.span('background_material_matrix_and_step'):
        J=cache.background_matrix()
        den=float(np.linalg.norm(cache.yb)**2)
        if den<=0: raise NumericalFailure('ZERO_BACKGROUND_DATA_SCALE')
        # Small data-space symmetric eigensolve, not a Maxwell solver change.
        largest=float(la.eigh(J@J.T,subset_by_index=(len(J)-1,len(J)-1),eigvals_only=True)[0]/den)
        if largest<=0 or not np.isfinite(largest): raise NumericalFailure('ZERO_BACKGROUND_MATERIAL_INFORMATION')
        return {'J':J,'data_norm2':den,'step':.8/largest,
                'beta':float(np.sqrt(np.mean(abs(cache.yb)**2))),
                'lambda_max_normalized_background_Hessian':largest}

def common_initialization(cache,obs,prep,config,book):
    from .material_updates import prox_tv_box
    xb=mass_pack(cache.chi_b,cache.physics.volume)
    lam=.01*(1+obs.sigma/prep['beta'])
    with book.span('common_initialization'):
        residual=pack(cache.yb-obs.data)
        gradient=prep['J'].T@residual/prep['data_norm2']
        x,meta=prox_tv_box(xb-prep['step']*gradient,xb,
                          prep['step']*lam,(config['grid'],)*2,
                          cache.physics.volume,config,book=book)
    return x,lam,meta

def loss_value(model,state,obs,prep,x,xb,lam,config):
    from .material_updates import tv_value
    residual=pack(state.data-obs.data)
    data=.5*float(residual@residual)/prep['data_norm2']
    tv=tv_value(x-xb,(config['grid'],)*2,model.cache.physics.volume)
    return data+lam*tv,data,tv

def reconstruct(model,obs,x0,lam,prep,config,book):
    """ONLY online measurement/background. Exactly three attempted blocks."""
    from .material_updates import prox_tv_box
    phys=model.cache.physics;xb=mass_pack(model.cache.chi_b,phys.volume)
    x=np.asarray(x0).copy();history=[];started=time.perf_counter()
    before=book.snapshot()
    with book.span('online_measurement_to_image'):
        state=model.forward(mass_unpack(x,phys.volume))
        for block in range(config['blocks']):
            book.check()
            old,dl,tv=loss_value(model,state,obs,prep,x,xb,lam,config)
            with book.span('material_gradient'):
                gradient=model.adjoint(state.chi,pack(state.data-obs.data),state)/prep['data_norm2']
            accepted=False;trial_log=[]
            for retry in range(config['max_half_step_retry']+1):
                step=prep['step']/(2**retry)
                candidate,prox=prox_tv_box(x-step*gradient,xb,step*lam,
                                            (config['grid'],)*2,phys.volume,config,book=book)
                trial=model.forward(mass_unpack(candidate,phys.volume))
                new,nd,nt=loss_value(model,trial,obs,prep,candidate,xb,lam,config)
                tolerance=1e-12*max(1.,abs(old))
                ok=(new<=old+tolerance)
                trial_log.append({'retry':retry,'step':step,'objective':new,
                                  'data_loss':nd,'tv':nt,'prox':prox,'accepted':ok,
                                  'margins':trial.margins})
                if ok:
                    x=candidate;state=trial;accepted=True;break
            history.append({'block':block,'old_objective':old,'old_data_loss':dl,
                            'old_tv':tv,'gradient_mass_norm':float(la.norm(gradient)),
                            'accepted':accepted,'trials':trial_log})
        chi=mass_unpack(x,phys.volume)
        phys.validate_material(chi)
    return {'chi':chi,'x':x,'state':state,'history':history,
            'online_s':time.perf_counter()-started,'cost':book.delta(before)}

def evaluate_image(phys,truth,chi,bg,full_state,obs,clean,config):
    delta=truth-bg;error=chi-truth
    den=float(la.norm(truth));dd=float(la.norm(delta))
    support=abs(delta)>=.25*np.max(abs(delta))
    estimated_support=abs(chi-bg)>=.25*np.max(abs(delta))
    union=np.sum(support|estimated_support)
    r=full_state.data-obs.data
    relative=float(la.norm(r)/la.norm(obs.data-phys._evaluation_yb)) if la.norm(obs.data-phys._evaluation_yb)>0 else None
    noisy_white=float(np.sqrt(2)*la.norm(r)/obs.sigma) if obs.sigma>0 else None
    full_state_res=float(la.norm(full_state.L@full_state.current-phys.material_to_a(chi).repeat(getattr(phys,'components',1))[:,None]*phys.incident))
    return {'material_nrmse':float(la.norm(error)/den) if den>0 else None,
            'delta_nrmse':float(la.norm(error)/dd) if dd>0 else None,
            'real_nrmse':relative_error(chi.real,truth.real),
            'imag_nrmse':relative_error(chi.imag,truth.imag),
            'support_iou':float(np.sum(support&estimated_support)/union) if union else None,
            'full_data_relative_residual':relative,
            'full_data_white_residual':noisy_white,
            'full_data_absolute_residual':float(la.norm(r)),
            'clean_prediction_relative_error':relative_error(full_state.data,clean),
            'full_state_residual_absolute':full_state_res,
            'feasible':True}

def task_audit(model,exact,chi,obs,config,book):
    """Evaluator-only fidelity audit at SAME estimated material, never truth."""
    rng=np.random.default_rng(np.random.SeedSequence([config['master_seed'],924]))
    with book.span('offline_independent_task_audit'):
        rs=model.forward(chi);fs=exact.forward(chi)
        jf=[];jr=[];af=[];ar=[]
        for _ in range(config['independent_material_probes']):
            d=rng.standard_normal(2*model.cache.physics.N);d/=la.norm(d)
            jf.append(exact.jvp(chi,d,fs));jr.append(model.jvp(chi,d,rs))
        for _ in range(config['independent_data_loads']):
            d=rng.standard_normal(2*model.cache.physics.q*model.cache.physics.s);d/=la.norm(d)
            af.append(exact.adjoint(chi,d,fs));ar.append(model.adjoint(chi,d,rs))
        gf=exact.adjoint(chi,pack(fs.data-obs.data),fs)
        gr=model.adjoint(chi,pack(rs.data-obs.data),rs)
        den=la.norm(gf)*la.norm(gr)
        cosine=float(gf@gr/den) if den>0 else None
    return {'independent_transfer_error':relative_error(np.asarray(jr),np.asarray(jf)),
            'independent_adjoint_error':relative_error(np.asarray(ar),np.asarray(af)),
            'gradient_cosine':cosine,
            'independent_state_data_error':relative_error(rs.data,fs.data)}

def run_pilot(config,out,book):
    from .physics import Physics2D
    from .relative_feedback import ReferenceCache
    from .relative_feedback import RelativeFeedbackModel
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for directory in ['data/online','data/offline','images','timing','cache']:
        (out/directory).mkdir(parents=True,exist_ok=True)
    rows=[];tasks=[];preparations=[];timing=[];failures=out/'FAILURE_LEDGER.jsonl'
    runtime=online_config(config)
    phys=Physics2D(grid=config['grid'],book=book,config=runtime)
    for bi,(bgname,bg) in enumerate(backgrounds(phys.points,config).items()):
        book.check();before=book.snapshot();started=time.perf_counter()
        with book.scope('background_preparation'):
            cache=ReferenceCache(phys,bg,book=book,config=runtime)
            prep=prepare_background(cache,book,runtime)
        shared=time.perf_counter()-started
        method_models={};method_setups={}
        definitions={'L':('L',16,False),'F':('F',16,False),'R16':('R',16,False),
                     'R32_DIAGNOSTIC':('R',32,False),'R16_LOCAL_DIAGNOSTIC':('R',16,True),
                     'AFFINE_ROM32':('ROM',32,False),'BORN_TV':('BORN',16,False)}
        for method in config['methods']:
            kind,rank,local=definitions[method];begin=time.perf_counter();snap=book.snapshot()
            try:
                with book.scope('method_preparation'):
                    model=RelativeFeedbackModel(cache,kind=kind,rank=rank,local=local,
                                                seed=config['master_seed']+bi,config=runtime)
                method_models[method]=model
                method_setups[method]=time.perf_counter()-begin
                if model.kind=='R':
                    with book.span('feedback_cache_export'):
                        np.savez_compressed(out/'cache'/f'{bgname}_{method}.npz',
                            Ug=model.Ug,Vg=model.Vg,
                            local_indices=np.array(model.D.indices) if model.D.indices else np.empty((0,0),int),
                            local_blocks=np.array(model.D.blocks) if model.D.blocks else np.empty((0,0,0),complex))
                preparations.append({'background':bgname,'method':method,'shared_background_s':shared,
                    'specific_setup_s':method_setups[method],'independent_setup_s':shared+method_setups[method],
                    'status':'OK','cost':book.delta(snap)})
            except BudgetExceeded: raise
            except Exception as exc:
                append_failure(failures,phase='prepare',background=bgname,method=method,error=repr(exc))
                preparations.append({'background':bgname,'method':method,'status':'FAILED','error':repr(exc)})
        exact=method_models['F'];linear=method_models['L']
        np.savez_compressed(out/'cache'/f'{bgname}_background.npz',yb=cache.yb,eb=cache.eb,
                            Db=cache.Db,J=prep['J'],chi_b=bg,step=prep['step'])
        phys._evaluation_yb=cache.yb
        for pi,parent in enumerate(config['parents']):
            for ai,amplitude in enumerate(config['amplitudes']):
                book.reserve('new_clean_labels',config['clean_labels_max'])
                truth=bg+amplitude*material_pattern(phys.points,parent,config)
                with book.scope('offline_clean_label'):
                    truth_state=phys.full_state(truth)
                np.savez_compressed(out/'data/offline'/f'{bgname}_{parent}_{amplitude}.npz',
                                    truth=truth,clean=truth_state.data)
                for ni,noise_db in enumerate(config['noise_snr_db']):
                    case=f'{bgname}_{parent}_{amplitude}_{"zero" if noise_db is None else "snr20"}'
                    rng=np.random.default_rng(np.random.SeedSequence([config['master_seed'],bi,parent,ai,ni,701]))
                    measured,sigma,noise=noisy_observation(truth_state.data,cache.yb,noise_db,rng)
                    obs=OnlineObservation(measured,sigma,case)
                    np.savez_compressed(out/'data/online'/f'{case}.npz',data=measured,sigma=sigma,
                                        chi_b=bg,case_id=case,noise_seed=[config['master_seed'],bi,parent,ai,ni,701])
                    init_start=time.perf_counter()
                    with book.scope('online_shared_initialization'):
                        x0,lam,initmeta=common_initialization(cache,obs,prep,runtime,book)
                    init_s=time.perf_counter()-init_start
                    case_results={}
                    order=list(config['methods']);rotate=(pi+ai+ni+bi)%len(order);order=order[rotate:]+order[:rotate]
                    for method in order:
                        row={'case_id':case,'parent_id':parent,'family':config['parent_families'][pi],
                             'background':bgname,'amplitude':amplitude,'noise_db':noise_db,'sigma':sigma,
                             'method':method,'status':'NOT_RUN','material_nrmse':None,'delta_nrmse':None,
                             'full_data_relative_residual':None,'full_data_white_residual':None,
                             'current_rank':None,'feedback_rank':None,'feasible':False}
                        if method not in method_models:
                            row.update(status='PREPARATION_FAILED');rows.append(row);continue
                        model=method_models[method]
                        try:
                            with book.scope('online_imaging'):
                                got=reconstruct(model,obs,x0,lam,prep,runtime,book)
                            # Full validation lives here, beyond the frozen runtime image.
                            begin=time.perf_counter()
                            with book.scope('offline_full_validation'):
                                reused=(method=='F' and 'native' in got['state'].extra)
                                physical=got['state'].extra['native'] if reused else phys.full_state(got['chi'])
                                metrics=evaluate_image(phys,truth,got['chi'],bg,physical,obs,truth_state.data,config)
                                fstate=physical;lstate=linear.forward(got['chi'])
                                feedback=la.norm(fstate.data-lstate.data)
                                closure=la.norm(got['state'].data-fstate.data)
                                floor=max(float(la.norm(noise)),1e-12*la.norm(cache.yb))
                                constitutive=got['state'].w-got['state'].h[:,None]*got['state'].field
                                constitutive_scale=float(la.norm(got['state'].w))
                            audit_s=time.perf_counter()-begin
                            row.update(metrics,status='OK',online_s=got['online_s']+init_s,
                                common_initialization_s=init_s,shared_background_s=shared,
                                specific_setup_s=method_setups[method],
                                cold_image_s=shared+method_setups[method]+init_s+got['online_s'],
                                full_validation_s=audit_s,relative_feedback_signal=float(feedback),
                                closure_absolute=float(closure),rho_closure=float(closure/feedback) if feedback>floor else None,
                                closure_status='RESOLVABLE' if feedback>floor else 'NO_RESOLVABLE_FEEDBACK',
                                core_margins=got['state'].margins,online_cost=got['cost'],
                                common_material_residual_absolute=float(la.norm(constitutive)),
                                common_material_residual_relative=float(la.norm(constitutive)/constitutive_scale) if constitutive_scale>0 else None,
                                validation_reused_online_full_state=reused,
                                accepted_blocks=sum(h['accepted'] for h in got['history']))
                            if model.kind=='R': row['feedback_rank']=model.actual_rank
                            if getattr(model,'Q',None) is not None: row['current_rank']=model.Q.shape[1]
                            np.savez_compressed(out/'images'/f'{case}_{method}.npz',chi=got['chi'],x=got['x'],
                                                predicted=got['state'].data,full_prediction=physical.data)
                            write_json(out/'images'/f'{case}_{method}.json',{'history':got['history'],
                                        'initialization':initmeta,'row':row,'config_id':config['protocol_id']})
                            case_results[method]=got
                        except BudgetExceeded: raise
                        except Exception as exc:
                            row.update(status='FAILED',error=repr(exc))
                            append_failure(failures,phase='online_or_evaluation',case_id=case,method=method,error=repr(exc))
                        rows.append(row)
                        write_csv(out/'CASES.csv',rows)
                    # Independent primal/dual audit: SAME legal R estimate, no teacher.
                    for method in ['R16','R32_DIAGNOSTIC','R16_LOCAL_DIAGNOSTIC','AFFINE_ROM32']:
                        if method not in case_results: continue
                        try:
                            with book.scope('offline_tasks'):
                                audit=task_audit(method_models[method],exact,case_results[method]['chi'],obs,config,book)
                            tasks.append({'case_id':case,'parent_id':parent,'background':bgname,'method':method,
                                          'status':'OK',**audit})
                        except BudgetExceeded: raise
                        except Exception as exc:
                            tasks.append({'case_id':case,'parent_id':parent,'method':method,'status':'FAILED','error':repr(exc)})
                            append_failure(failures,phase='task_audit',case_id=case,method=method,error=repr(exc))
                    write_csv(out/'TASK_AUDIT.csv',tasks)
                    # Fixed timing matrix, never select favorable objects/methods from results.
                    if ai==0 and ni==1 and pi in (0,2):
                        for repeat in range(config['timing_repeats']):
                            methods=['L','F','R16'];rot=(repeat+bi+pi)%3;methods=methods[rot:]+methods[:rot]
                            for method in methods:
                                if method not in case_results: continue
                                try:
                                    with book.scope('runtime_audit'):
                                        begin=time.perf_counter()
                                        ix,ll,im=common_initialization(cache,obs,prep,runtime,book)
                                        value=reconstruct(method_models[method],obs,ix,ll,prep,runtime,book)
                                    timing.append({'case_id':case,'parent_id':parent,'background':bgname,
                                        'method':method,'repeat':repeat,'warm_s':time.perf_counter()-begin,
                                        'status':'OK','cost':value['cost'],'fresh_material_cache':True})
                                except BudgetExceeded: raise
                                except Exception as exc:
                                    timing.append({'case_id':case,'method':method,'repeat':repeat,'status':'FAILED','error':repr(exc)})
                    write_csv(out/'TIMING.csv',timing)
        write_csv(out/'PREPARATION.csv',preparations)
    return {'cases':len(rows),'task_rows':len(tasks),'timing_rows':len(timing),
            'status':'COMPLETE','clean_labels_reserved':book.reservations.get('new_clean_labels',0)}
