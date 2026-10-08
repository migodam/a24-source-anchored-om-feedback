"""Sequential gated CLI with charged attempts and process wall deadline."""
from __future__ import annotations
import argparse, contextlib, io, json, os, platform, runpy, shutil, signal, subprocess, sys, time, traceback, unittest
from pathlib import Path
from a20.costs import write_json, BudgetExceeded
from .contracts import Ledger,active_ledger

ROOT=Path(__file__).resolve().parents[2]

def history(stage,ignore_job=None):
    receipts=[]
    # An interrupted controller cannot grant a fresh budget or fresh labels.
    # Unknown elapsed work requires an explicit recovery audit, never zero.
    for manifest in sorted((ROOT/'results/jobs').glob('*/manifest.json')):
        if manifest.parent.name==ignore_job: continue
        d=json.loads(manifest.read_text());command=d.get('command')
        if command=='freeze': continue
        previous_stage='A' if command=='anatomy' else '3D' if command=='confirm-3d' else 'B0'
        if previous_stage==stage and not (manifest.parent/'job_receipt.json').exists():
            raise BudgetExceeded('UNRESOLVED_PREVIOUS_JOB_RECEIPT:'+manifest.parent.name)
    for p in sorted((ROOT/'results/jobs').glob('*/job_receipt.json')):
        d=json.loads(p.read_text())
        if d['stage']==stage:receipts.append(d)
    return sum(d['wall_seconds'] for d in receipts),sum(d.get('new_clean_labels',0) for d in receipts)

def alarm_handler(signum,frame):
    raise BudgetExceeded('HARD_PROCESS_STAGE_DEADLINE')

def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','anatomy','no-nn','confirm-3d','report'])
    p.add_argument('--config',default='configs/a24_frozen.json');p.add_argument('--job',required=True)
    p.add_argument('--device',default='cpu');args=p.parse_args(argv)
    if args.device!='cpu':p.error('GPU_DISABLED')
    config=json.loads((ROOT/args.config).read_text());job=ROOT/'results/jobs'/args.job
    if job.exists():raise RuntimeError('EXISTING_JOB_ID_NO_OVERWRITE')
    job.mkdir(parents=True)
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    write_json(job/'frozen_config.json',config)
    write_json(job/'manifest.json',{'command':args.command,'job':args.job,'source_commit':head,
               'python':platform.python_version(),'device':'cpu','argv':sys.argv,'protocol_id':config['protocol_id']})
    if args.command=='freeze':
        print(json.dumps({'status':'FROZEN','source_commit':head,'job':args.job}));return
    stage='A' if args.command=='anatomy' else '3D' if args.command=='confirm-3d' else 'B0'
    limits={'A':config['A_wall_seconds'],'B0':config['B0_wall_seconds'],'3D':config['confirmation_wall_seconds']}
    prior,labels=history(stage,ignore_job=args.job)
    book=Ledger(job/'COST_LEDGER.jsonl',wall_limit=limits[stage],prior_wall=prior,metadata={'job':args.job,'stage':stage})
    book.reservations['new_clean_labels']=labels
    result={'status':'FAILED'};original=signal.signal(signal.SIGALRM,alarm_handler)
    signal.setitimer(signal.ITIMER_REAL,max(.001,limits[stage]-prior))
    try:
        with active_ledger(book):
            book.check()
            if args.command=='anatomy':
                output=ROOT/'results/anatomy';output.mkdir(exist_ok=True)
                verify=job/'verification';verify.mkdir()
                source=ROOT/'theory/verification/algebra_checks.py'
                shutil.copy2(source,verify/'algebra_checks.py')
                with book.span('provided_synthetic_algebra'):
                    with contextlib.redirect_stdout(io.StringIO()):runpy.run_path(str(verify/'algebra_checks.py'),run_name='__main__')
                log=io.StringIO()
                with book.span('A24_unit_tests'):
                    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'),top_level_dir=str(ROOT))
                    tests=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
                (job/'UNIT_TESTS.log').write_text(log.getvalue())
                write_json(job/'UNIT_TESTS.json',{'tests_run':tests.testsRun,'failures':len(tests.failures),'errors':len(tests.errors),'passed':tests.wasSuccessful()})
                if not tests.wasSuccessful():
                    result={'status':'TESTS_FAILED','G1_status':'FAIL','tests':tests.testsRun}
                else:
                    from .anatomy import anatomy
                    result=anatomy(config,output,book)
                    result['tests_run']=tests.testsRun
                write_json(output/'ANATOMY.json',result)
            elif args.command=='no-nn':
                anatomy=json.loads((ROOT/'results/anatomy/ANATOMY.json').read_text())
                if anatomy.get('G1_status')!='PASS':raise RuntimeError('G1_NOT_PASSED')
                from .pilot import run_pilot
                result=run_pilot(config,ROOT/'results/b0',book)
            elif args.command=='confirm-3d':
                gate=json.loads((ROOT/'results/b0/GATE_DECISION.json').read_text())
                if gate['G1']['status']!='PASS' or not gate['G3']['F_headroom']:
                    raise RuntimeError('3D_PREREQUISITE_NOT_PASSED')
                from .confirmation import confirm
                result=confirm(config,ROOT/'results/confirmation3d',book)
            else:
                from .gates import decide
                result=decide(config,ROOT/'results/b0',ROOT/'results/anatomy/ANATOMY.json')
                from .reporting import build_report
                with book.span('report_tables_and_scientific_figures'):
                    deliverables=build_report(config,ROOT,book)
                result['report_artifacts']=deliverables
    except BaseException as exc:
        result={'status':'BUDGET_STOP' if isinstance(exc,BudgetExceeded) else 'FAILED','error':repr(exc)}
        (job/'ERROR.log').write_text(traceback.format_exc())
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,original)
        receipt=book.receipt();receipt.update(stage=stage,command=args.command,result=result,
            new_clean_labels=book.reservations.get('new_clean_labels',0)-labels)
        write_json(job/'job_receipt.json',receipt)
        write_json(job/'result.json',result)
        print(json.dumps({'job':args.job,'status':result.get('status',result.get('decision')),
                          'wall_seconds':receipt['wall_seconds'],'error':result.get('error')}))
    return 0 if result.get('status') not in ('FAILED','TESTS_FAILED','BUDGET_STOP') else 1

if __name__=='__main__':sys.exit(main())
