"""Authorized public delivery, charged to the existing B0 budget. No physics."""
from __future__ import annotations
import argparse,gzip,json,os,re,shutil,signal,subprocess,sys,time,urllib.request,zipfile,platform
from importlib.metadata import version
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from a24.cli import history,alarm_handler
from a24.contracts import Ledger,active_ledger
from a20.costs import write_json

REPO='migodam/a24-source-anchored-om-feedback'
URL='https://github.com/'+REPO
TAG='v0.1.0-no-nn-pilot'

def command(book,*args,timeout=60):
    with book.span('public_delivery_command',publication_commands=1):
        result=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
        if result.returncode: raise RuntimeError('DELIVERY_COMMAND_FAILED: '+args[0]+' '+result.stderr[:1500])
        return result.stdout.strip()

def get_public(book,url):
    with book.span('anonymous_public_read',anonymous_http_requests=1):
        request=urllib.request.Request(url,headers={'User-Agent':'A24-reproducibility-verification'})
        with urllib.request.urlopen(request,timeout=30) as r:
            data=r.read();book.counts['anonymous_read_bytes']+=len(data)
            return {'url':url,'status':r.status,'bytes':len(data),'content':data}

def prepare(book):
    archive=ROOT/'results/archive';archive.mkdir(exist_ok=True)
    rows=[]
    with book.span('archive_complete_cost_ledgers'):
        for receipt in sorted((ROOT/'results/jobs').glob('*/job_receipt.json')):
            if receipt.parent.name.startswith('a24-delivery-'):continue
            row=json.loads(receipt.read_text());row['job']=receipt.parent.name;rows.append(row)
            path=receipt.parent/'COST_LEDGER.jsonl'
            if path.exists():
                target=archive/(receipt.parent.name+'.COST_LEDGER.jsonl.gz')
                with path.open('rb') as src,target.open('wb') as dest:
                    with gzip.GzipFile(fileobj=dest,mode='wb',mtime=0) as compressed:
                        shutil.copyfileobj(src,compressed)
    # Publish a portable metadata copy; exact original local paths stay ignored.
    substitutions={str(ROOT):'.',str(ROOT.parents[1]/'.venv_nn'):'<local-python-environment>'}
    audit={'private_credentials_found':False,'path_redacted_files':[],'sha256_checks_performed':False,
           'scientific_values_modified':False,'physics_actions':0,'cost_archives':'results/archive/'}
    forbidden=re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|\bgh[pousr]_[A-Za-z0-9]{30,}|\bsk-[A-Za-z0-9_-]{32,}')
    saved=ROOT/'private/pre_publication_metadata';saved.mkdir(parents=True,exist_ok=True)
    with book.span('public_artifact_metadata_audit'):
        for directory in ('results','publication'):
            base=ROOT/directory
            if not base.exists():continue
            for p in base.rglob('*'):
                if not p.is_file() or p.suffix not in ('.json','.jsonl','.csv','.log','.md'):continue
                if p.name=='COST_LEDGER.jsonl' or 'a24-delivery-' in str(p):continue
                original=p.read_text(encoding='utf-8')
                if forbidden.search(original):raise RuntimeError('CREDENTIAL_PATTERN_IN_PUBLIC_ARTIFACT:'+str(p.relative_to(ROOT)))
                text=original
                for a,b in substitutions.items():text=text.replace(a,b)
                if text!=original:
                    backup=saved/p.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
                    if not backup.exists():backup.write_text(original,encoding='utf-8')
                    p.write_text(text,encoding='utf-8');audit['path_redacted_files'].append(str(p.relative_to(ROOT)))
    (ROOT/'publication').mkdir(exist_ok=True)
    write_json(ROOT/'publication/PUBLIC_ARTIFACT_AUDIT.json',audit)
    with (ROOT/'results/COST_LEDGER.jsonl').open('w') as f:
        for row in rows:
            line=json.dumps(row,allow_nan=False)
            for a,b in substitutions.items():line=line.replace(a,b)
            f.write(line+'\n')
    write_json(ROOT/'ENVIRONMENT.json',{'python':platform.python_version(),'platform':platform.platform(),
        'machine':platform.machine(),'packages':{p:version(p) for p in ('numpy','scipy','matplotlib')},
        'threads':{k:os.environ.get(k) for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS')},
        'device':'cpu','gpu_seconds':0,'no_new_dependency_installation':True})
    write_json(ROOT/'results/COST_SUMMARY.json',{'jobs':len(rows),
        'wall_by_stage':{stage:sum(r['wall_seconds'] for r in rows if r['stage']==stage) for stage in ('A','B0','3D')},
        'process_cpu_seconds':sum(r['process_cpu_seconds'] for r in rows),
        'new_clean_labels':sum(r.get('new_clean_labels',0) for r in rows),
        'gpu_seconds':0,'includes_failed_jobs':True,'includes_report_jobs':True,
        'publication_cost_receipt':'GitHub Release assets; separately charged to B0',
        'deployment_claim':'NOT_ESTABLISHED'})
    with book.span('archive_release_cost_assets'):
        bundle=ROOT/'publication/A24_COMPLETE_COST_LEDGERS.zip'
        with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_STORED) as z:
            for path in sorted(archive.glob('*.gz')):z.write(path,path.name)
    return audit

def publish(book,job):
    prepare(book)
    # These paths are the approved archive, not external credentials or runtime environments.
    command(book,'git','add','.gitignore','README.md','A24_RESEARCH_REPORT_ZH.md',
        'A24_EXECUTION_REPORT.md','SOURCE_MANIFEST.json','requirements.txt','ENVIRONMENT.json',
        'configs','docs','scripts','src','tests','theory','research','results','publication')
    if command(book,'git','diff','--cached','--name-only'):
        command(book,'git','commit','-m','Publish frozen A24 no-NN evidence, failures and scientific review')
    sha=command(book,'git','rev-parse','HEAD')
    if not command(book,'git','remote'):
        command(book,'gh','repo','create',REPO,'--public','--source=.','--remote=origin',
            '--description','A24 source-anchored OM and no-NN relative-feedback imaging: frozen pilot, failures and reproducibility')
    command(book,'git','push','-u','origin','HEAD:main')
    metadata=json.loads(command(book,'gh','api','repos/'+REPO))
    if metadata.get('private') or metadata.get('html_url')!=URL:raise RuntimeError('PUBLIC_REPOSITORY_IDENTITY_MISMATCH')
    remote=command(book,'git','ls-remote','origin','refs/heads/main').split()[0]
    if remote!=sha:raise RuntimeError('REMOTE_COMMIT_MISMATCH')
    report=f'https://raw.githubusercontent.com/{REPO}/{sha}/A24_RESEARCH_REPORT_ZH.md'
    entry=f'https://raw.githubusercontent.com/{REPO}/{sha}/README.md'
    checks=[]
    for url,marker in ((report,'QUALITY_TARGET_NOT_REACHED'),(entry,'Gate2')):
        result=get_public(book,url)
        if marker not in result.pop('content').decode('utf-8'):raise RuntimeError('ANONYMOUS_REPORT_MARKER_MISSING')
        checks.append(result)
    verification={'repository':URL,'commit':sha,'remote_commit':remote,
        'anonymous_reads':checks,'release':URL+'/releases/tag/'+TAG,'public':True,
        'scientific_gate_status_is_separate':True}
    write_json(job/'PUBLICATION_VERIFICATION.json',verification)
    command(book,'gh','release','create',TAG,'--repo',REPO,'--target',sha,
        '--title','A24 frozen no-NN pilot: Gate2 FAIL, imaging HOLD',
        '--notes-file',str(ROOT/'publication/RELEASE_NOTES.md'),
        str(ROOT/'publication/A24_COMPLETE_COST_LEDGERS.zip'))
    # The final receipt upload cannot include its own completion. Reserve a
    # visible bounded tail instead of advertising it as zero/free work.
    receipt=book.receipt();receipt.update(stage='B0',command='public-delivery',
        new_clean_labels=0,result={'status':'PUBLISHED','commit':sha},
        final_receipt_upload_wall_allowance_seconds=60,
        accounted_wall_bound_seconds=receipt['wall_seconds']+60)
    if book.prior_wall+receipt['wall_seconds']+60>book.wall_limit:
        raise RuntimeError('NO_BUDGET_FOR_FINAL_PUBLIC_RECEIPT_UPLOAD')
    write_json(job/'PUBLICATION_COST_RECEIPT.json',receipt)
    command(book,'gh','release','upload',TAG,'--repo',REPO,
        str(job/'PUBLICATION_VERIFICATION.json'),str(job/'PUBLICATION_COST_RECEIPT.json'))
    release=json.loads(command(book,'gh','api','repos/'+REPO+'/releases/tags/'+TAG))
    for asset in release['assets']:
        result=get_public(book,asset['browser_download_url']);result.pop('content');checks.append(result)
    return verification

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('prepare','publish'));parser.add_argument('--job',required=True)
    args=parser.parse_args();job=ROOT/'results/jobs'/args.job
    if job.exists():raise RuntimeError('EXISTING_JOB_ID')
    prior,_=history('B0');config=json.loads((ROOT/'configs/a24_frozen.json').read_text())
    job.mkdir(parents=True);write_json(job/'manifest.json',{'command':'public-delivery','job':args.job,'stage':'B0'})
    book=Ledger(job/'COST_LEDGER.jsonl',wall_limit=config['B0_wall_seconds'],prior_wall=prior,metadata={'job':args.job,'stage':'B0'})
    old=signal.signal(signal.SIGALRM,alarm_handler);signal.setitimer(signal.ITIMER_REAL,max(.001,book.wall_limit-prior))
    result={'status':'FAILED'}
    try:
        with active_ledger(book):
            result=publish(book,job) if args.mode=='publish' else prepare(book)
            result['status']='PUBLISHED' if args.mode=='publish' else 'PREPARED'
    except BaseException as exc:
        result={'status':'FAILED','error':repr(exc)}
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        receipt=book.receipt();receipt.update(stage='B0',command='public-delivery',new_clean_labels=0,result=result)
        write_json(job/'job_receipt.json',receipt)
        print(json.dumps({'result':result,'wall_seconds':receipt['wall_seconds']},allow_nan=False))

if __name__=='__main__':main()
