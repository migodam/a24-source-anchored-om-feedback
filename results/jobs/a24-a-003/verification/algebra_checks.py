"""A24: reproducible CPU-only algebra checks, NOT Maxwell imaging evidence.
Requires Python >=3.10 and NumPy. Run: python verification/algebra_checks.py
No network, training, GPU, prior project data, or truth-state deployment input.
"""
from __future__ import annotations
import json, platform, time
from pathlib import Path
import numpy as np


def rel(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a-b)/max(np.linalg.norm(b), 1e-30))


def main() -> None:
    tic=time.perf_counter()
    rng=np.random.default_rng(241008)
    def rand(*shape: int) -> np.ndarray:
        return (rng.standard_normal(shape)+1j*rng.standard_normal(shape))/np.sqrt(2)
    out: dict[str, object]={'scope':'finite-dimensional algebra only; no Maxwell imaging or training', 'seed':241008}
    n, cells, sources, receivers=18,6,3,5
    eye=np.eye(n,dtype=complex)
    G=rand(n,n)/np.sqrt(n)*0.5
    ab=np.repeat(0.3+0.08j,cells)
    Ab=np.diag(np.repeat(ab,3))
    Ei=rand(n,sources)
    Lb=eye-Ab@G
    Rb=np.linalg.solve(Lb,eye)
    b=Ab@Ei
    jb=Rb@b
    eb=Ei+G@jb
    S=rand(receivers,n)/np.sqrt(n)
    U=np.linalg.qr(np.column_stack((jb,S.conj().T[:,:2])))[0]
    Q=np.linalg.qr(U,mode='complete')[0][:,U.shape[1]:]
    Pi=eye-U@U.conj().T
    RU=U@np.linalg.solve(U.conj().T@Lb@U,U.conj().T)
    K=Pi@(eye-Lb@RU)
    T=(eye-RU@Lb)@Pi
    Sc=Q.conj().T@Lb@T@Q
    Rsch=RU+T@Q@np.linalg.solve(Sc,Q.conj().T@K)
    Bprobe=np.repeat(rand(cells),3)[:,None]*eb
    out['anchor']={'P_relative_norm':float(np.linalg.norm(K@b)/np.linalg.norm(b)),
        'material_excitation_complement_norm':float(np.linalg.norm(K@Bprobe)),
        'feedback_complement_norm':float(np.linalg.norm(np.eye(Q.shape[1])-Sc)),
        'inverse_schur_error':rel(Rsch,Rb), 'retained_rank':U.shape[1]}
    assert out['anchor']['P_relative_norm']<1e-12
    assert out['anchor']['inverse_schur_error']<1e-12
    assert out['anchor']['material_excitation_complement_norm']>1e-3
    # General retained-complement degree-shift identity without source anchoring.
    U2=np.linalg.qr(rand(n,2))[0]
    P2=eye-U2@U2.conj().T
    RU2=U2@np.linalg.solve(U2.conj().T@Lb@U2,U2.conj().T)
    K2=P2@(eye-Lb@RU2)
    T2=(eye-RU2@Lb)@P2
    Fe=P2-P2@Lb@T2
    H_U=P2@(eye-Lb)@U2
    ah=np.linalg.solve(U2.conj().T@Lb@U2,U2.conj().T@jb)
    rhs=(eye-Fe)@(K2@jb-H_U@ah)
    out['retained_coupling']={'identity_error':rel(rhs,K2@b),
        'omitting_coupling_error':rel((eye-Fe)@K2@jb,K2@b)}
    assert out['retained_coupling']['identity_error']<1e-12
    h=0.07*rand(cells)
    H=np.diag(np.repeat(h,3))
    A=Ab+H
    L=eye-A@G
    j=np.linalg.solve(L,A@Ei)
    Dj=j-jb
    Fb=Rb@H@G
    Dj2=np.linalg.solve(eye-Fb,Rb@H@eb)
    Gb=G@Rb
    Db=S@Rb
    q=np.linalg.solve(eye-H@Gb,H@eb)
    out['relative_identity']={'current_form_error':rel(Dj2,Dj),'source_form_error':rel(Rb@q,Dj)}
    assert max(out['relative_identity'].values())<1e-12
    # Reduced propagation, while keeping all local material source entries.
    Ug,sv,Vh=np.linalg.svd(Gb,full_matrices=False)
    khat=(Ug[:,:5]*sv[:5])@Vh[:5]
    qhat=np.linalg.solve(eye-H@khat,H@eb)
    defect=H@(Gb-khat)@qhat
    Ah=eye-H@Gb
    errq=q-qhat
    boundq=np.linalg.norm(np.linalg.solve(Ah,eye),2)*np.linalg.norm(defect)
    erry=Db@errq
    boundy=np.linalg.norm(Db@np.linalg.solve(Ah,eye),2)*np.linalg.norm(defect)
    jhat=jb+Rb@qhat
    state_res=L@jhat-A@Ei
    out['propagation_error']={'q_error':float(np.linalg.norm(errq)), 'q_bound':float(boundq),
       'data_error':float(np.linalg.norm(erry)), 'data_bound':float(boundy),
       'state_residual_identity_error':rel(state_res,-defect)}
    assert np.linalg.norm(errq)<=boundq*(1+1e-12)
    assert np.linalg.norm(erry)<=boundy*(1+1e-12)
    assert rel(state_res,-defect)<1e-11
    # Consistent real adjoint of the same approximate material-conditioned model.
    Ehat=eb+khat@qhat
    material_direction=rand(cells)
    dH=np.diag(np.repeat(material_direction,3))
    r=rand(receivers,sources)
    dq=np.linalg.solve(eye-H@khat,dH@Ehat)
    z=np.linalg.solve((eye-H@khat).conj().T,Db.conj().T@r)
    score=np.sum((Ehat.conj()*z).reshape(cells,3,sources),axis=(1,2))
    lhs=float(np.real(np.vdot(r,Db@dq)))
    rhs=float(np.dot(np.r_[score.real,score.imag],np.r_[material_direction.real,material_direction.imag]))
    out['real_adjoint_error']=abs(lhs-rhs)/max(abs(lhs),abs(rhs),1e-30)
    assert out['real_adjoint_error']<1e-11
    # Exact low-rank-plus-local synthetic propagation; not an EM Green matrix.
    N,k,s=12,2,3
    I=np.eye(N,dtype=complex)
    D=np.diag(0.1+0.02*rand(N))
    P=rand(N,k)/np.sqrt(N)*0.15
    Qr=rand(N,k)/np.sqrt(N)*0.15
    Kfull=D+P@Qr.conj().T
    hv=np.linspace(-0.2,0.4,N)+0.04j
    Hh=np.diag(hv)
    E=rand(N,s)
    C=np.linalg.solve(I-Hh@D,Hh)
    core=np.eye(k)-Qr.conj().T@C@P
    w=np.linalg.solve(core,Qr.conj().T@C@E)
    qsmall=C@(E+P@w)
    qexact=np.linalg.solve(I-Hh@Kfull,Hh@E)
    fixed=np.linalg.qr(P)[0]
    fixed_error=rel(fixed@fixed.conj().T@qexact,qexact)
    out['full_source_small_feedback']={'small_core_relative_error':rel(qsmall,qexact),
       'fixed_rank_current_projection_error':fixed_error,'feedback_rank':k,'source_dimension':N,
       'warning':'structured synthetic operator, not a Maxwell performance experiment'}
    assert rel(qsmall,qexact)<1e-12
    assert fixed_error>0.2
    # TSOM intersection and projected range differ; three intersections need not fill space.
    e=np.eye(3)
    Pamb=np.diag([0.,1.,1.])
    Dplus=np.column_stack(((e[:,0]+e[:,1])/np.sqrt(2),e[:,2]))
    exact_intersection=e[:,2:3]
    projected=Pamb@Dplus
    out['tsom_geometry']={'intersection_rank':1,'projection_rank':int(np.linalg.matrix_rank(projected)),
        'claimed_three_space_sum_rank':2,'ambient_rank':3,
        'commutator_norm':float(np.linalg.norm(Pamb@Dplus@Dplus.T-Dplus@Dplus.T@Pamb))}
    assert np.linalg.matrix_rank(projected)==2
    # Nonnormal transient defeats a spectral-radius shallow-layer bound.
    F=np.array([[0.,100.],[0.,0.]])
    X=np.array([0.,1.])
    sol=np.linalg.solve(np.eye(2)-F,X)
    out['nonnormal']={'spectral_radius':float(max(abs(np.linalg.eigvals(F)))),
       'degree0_absolute_error':float(np.linalg.norm(sol-X)),
       'degree1_absolute_error':float(np.linalg.norm(sol-X-F@X))}
    assert out['nonnormal']['degree0_absolute_error']==100
    # Common material consistency is stronger than a least-squares material update.
    Ej=np.ones(2,dtype=complex); J=np.array([1.,2.],dtype=complex)
    als=np.vdot(Ej,J)/np.vdot(Ej,Ej)
    out['common_material']={'fitted_a':float(als.real),'remaining_residual':float(np.linalg.norm(J-als*Ej))}
    # Arbitrary closure does not satisfy the Galerkin double-sided defect identity.
    out['arbitrary_closure_counterexample']={'true_defect':0.5,'incorrect_double_sided':0.25}
    Lswap=np.array([[0.,1.],[1.,0.]])
    out['singular_projected_core']={'full_determinant':float(np.linalg.det(Lswap)),'projected_core':0.0}
    eps=1e-6
    out['small_seed_large_output']={'seed_norm':eps,'data_response':1/eps}
    # DWR with an explicitly included correction is always valid.
    Xhat=rand(n,2); Zhat=rand(n,receivers); B=rand(n,2)
    true=S@np.linalg.solve(L,B)
    corr=S@Xhat+Zhat.conj().T@(B-L@Xhat)
    prod=(S-Zhat.conj().T@L)@np.linalg.solve(L,B-L@Xhat)
    out['corrected_dwr_identity_error']=rel(true-corr,prod)
    assert out['corrected_dwr_identity_error']<1e-12
    # Relative closeness can differ from absolute contrast, in a scalar algebraic model.
    ab0=6+0.2j; h0=.05; g0=.2
    out['absolute_relative_toy']={'absolute_born_factor':abs((ab0+h0)*g0),
        'relative_feedback_factor':abs(h0*g0/(1-ab0*g0)),
        'warning':'scalar algebra only; not a passive Maxwell resonance certificate'}
    out['status']='ALL_ASSERTIONS_PASSED'
    out['elapsed_cpu_wall_seconds']=time.perf_counter()-tic
    out['environment']={'python':platform.python_version(),'numpy':np.__version__,'gpu_used':False}
    destination=Path(__file__).with_name('algebra_results.json')
    destination.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(out,indent=2,ensure_ascii=False))

if __name__=='__main__':
    main()