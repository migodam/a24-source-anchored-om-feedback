"""Charged, tiny-grid A24 anatomy; dense matrices are evaluator-only here.

No helper in this module is used by the imaging runtime.  Bases are frozen
from the known reference, acquisition and independent probes before a passive
candidate is evaluated.  A current projection is an audit/control, not SA-RF.
"""
from __future__ import annotations

from pathlib import Path
import time
import numpy as np
from scipy import linalg as la

from .contracts import (BudgetExceeded, NumericalFailure, get_ledger,
                        guard_core, mass_unpack, pack, plain, relative_error,
                        unpack, write_json)


def norm_ratio(numerator, denominator):
    """Return None for an undefined relative metric; never manufacture a floor."""
    scale = float(la.norm(denominator))
    return float(la.norm(numerator) / scale) if scale > 0. else None


def orth_basis(bank, *, against=None, rank=None, rtol=1e-10,
               absolute_zero_scale=0., book=None, label='anatomy_QR'):
    """Rank-revealing compression, with an externally declared zero scale.

    In particular a roundoff P seed is judged against the full forcing, not
    against its own tiny norm.  Returned columns are never padded.
    """
    book = get_ledger() if book is None else book
    x = np.asarray(bank, dtype=np.complex128)
    x = x[:, None] if x.ndim == 1 else x
    if x.ndim != 2:
        raise ValueError('CURRENT_BANK_N_BY_PROBE_REQUIRED')
    with book.span(label, qr_calls=1, qr_input_columns=x.shape[1],
                   array_bytes=x.nbytes):
        if not x.shape[1]:
            return x.copy(), {'input_columns': 0, 'rank': 0, 'deflated': 0,
                              'zero_scale': float(absolute_zero_scale)}
        y = x.copy()
        if against is not None and against.shape[1]:
            for _ in range(2):
                y -= against @ (against.conj().T @ y)
        u, singular, _ = la.svd(y, full_matrices=False)
        scale = max(float(la.norm(x)), float(absolute_zero_scale),
                    float(singular[0]) if singular.size else 0.)
        threshold = rtol * scale
        available = int(np.count_nonzero(singular > threshold))
        keep = available if rank is None else min(available, max(0, int(rank)))
        return u[:, :keep], {
            'input_columns': x.shape[1], 'rank': keep,
            'available_rank': available, 'deflated': x.shape[1] - available,
            'truncated': available - keep, 'threshold': threshold,
            'zero_scale': float(absolute_zero_scale),
            'singular_values': singular.tolist(), 'padding': 0}


class SchurAudit:
    """Exact dense T/K/F_eff for A0/A1 verification, with no fallback."""
    def __init__(self, L, U, config=None, book=None):
        self.book = get_ledger() if book is None else book
        self.config = {} if config is None else config
        self.L = np.asarray(L, dtype=np.complex128)
        self.U = np.asarray(U, dtype=np.complex128)
        self.n, self.retained_rank = self.U.shape
        if self.L.shape != (self.n, self.n):
            raise ValueError('L_CURRENT_DIMENSION_MISMATCH')
        if la.norm(self.U.conj().T @ self.U - np.eye(self.retained_rank)) > 1e-9:
            raise ValueError('NONORTHONORMAL_RETAINED_BASIS')
        with self.book.span('anatomy_retained_core_assembly',
                            internal_kernel_rhs=self.retained_rank):
            self.A = self.U.conj().T @ self.L @ self.U
        self.margin = guard_core(self.A, self.config, 'anatomy_retained')
        with self.book.span('anatomy_retained_core_factor',
                            retained_factorizations=1):
            self.factor = la.lu_factor(self.A)

    def project(self, value):
        return value - self.U @ (self.U.conj().T @ value)

    def _L(self, value, adjoint=False):
        columns = 1 if value.ndim == 1 else value.shape[1]
        with self.book.span('anatomy_L_adjoint' if adjoint else 'anatomy_L',
                            internal_kernel_rhs=columns):
            return (self.L.conj().T if adjoint else self.L) @ value

    def coarse(self, value, adjoint=False):
        columns = 1 if value.ndim == 1 else value.shape[1]
        with self.book.span('anatomy_retained_solve', reduced_core_rhs=columns):
            return la.lu_solve(self.factor, value, trans=2 if adjoint else 0)

    def RU(self, value, adjoint=False):
        return self.U @ self.coarse(self.U.conj().T @ value, adjoint)

    def K(self, value, adjoint=False):
        if adjoint:
            v = self.project(value)
            return v - self.RU(self._L(v, True), True)
        return self.project(value - self._L(self.RU(value)))

    def T(self, value, adjoint=False):
        if adjoint:
            return self.project(value - self._L(self.RU(value, True), True))
        v = self.project(value)
        return v - self.RU(self._L(v))

    def feedback(self, value, adjoint=False):
        v = self.project(value)
        if adjoint:
            return self.project(v - self.T(self._L(v, True), True))
        return self.project(v - self._L(self.T(v)))

    def inverse_certificate(self):
        """Full Schur inverse solely for tiny evaluator verification."""
        with self.book.span('anatomy_schur_inverse_certificate',
                            evaluator_dense_oracles=1, qr_calls=1,
                            full_linear_rhs=self.n, array_bytes=3*self.L.nbytes):
            eye = np.eye(self.n, dtype=np.complex128)
            Q = la.qr(self.U, mode='full')[0][:, self.retained_rank:]
            R_U = self.RU(eye)
            T_Q = self.T(Q)
            K_Q = Q.conj().T @ self.K(eye)
            C_Q = Q.conj().T @ self.L @ T_Q
            margin = guard_core(C_Q, self.config, 'anatomy_complement')
            complement = T_Q @ la.solve(C_Q, K_Q)
            exact = la.solve(self.L, eye)
            reconstructed = R_U + complement
            return {
                'inverse_schur_error': relative_error(reconstructed, exact),
                'complement_core': margin,
                'retained_complement_coupling_norm': float(la.norm(
                    self.U.conj().T @ self.L @ Q)),
                'complement_retained_coupling_norm': float(la.norm(
                    Q.conj().T @ self.L @ self.U)),
                'schur_coupling_correction_norm': float(la.norm(
                    C_Q-Q.conj().T @ self.L @ Q)),
                'complement_inverse_norm': float(la.norm(complement)),
                'complement_core_not_identity_norm': float(la.norm(
                    C_Q-np.eye(C_Q.shape[0])))}, Q


def source_seed_banks(schur, forcing, eb, S, volume, material_probes,
                      measurement_probes, config=None):
    """Source axis stays explicit until [source,probe] column stacking."""
    config = {} if config is None else config
    n, s = eb.shape
    q = S.shape[0]
    m = np.asarray(material_probes, dtype=float)
    o = np.asarray(measurement_probes, dtype=float)
    if m.ndim != 2 or m.shape[0] != 2*n:
        raise ValueError('REAL_MASS_MATERIAL_PROBE_SHAPE')
    if o.ndim != 2 or o.shape[0] != 2*q*s:
        raise ValueError('PACKED_REAL_DATA_PROBE_SHAPE')
    delta = (m[:n] + 1j*m[n:]) / np.sqrt(volume)
    material_rhs = np.einsum('np,ns->nsp', delta, eb).reshape(n, -1)
    complex_loads = np.stack([unpack(o[:, i], q, s)
                              for i in range(o.shape[1])], axis=-1)
    with schur.book.span('anatomy_O_seed_injection',
                         receiver_adjoint_rhs=s*o.shape[1]):
        data_rhs = S.conj().T @ complex_loads.reshape(q, -1)
    raw = {'O': schur.T(data_rhs, adjoint=True),
           'P': schur.K(forcing), 'M': schur.K(material_rhs)}
    scale = float(la.norm(forcing))
    blocks, records = {}, {}
    for name in 'OPM':
        blocks[name], records[name] = orth_basis(
            raw[name], against=schur.U,
            rank=int(config.get('seed_rank_'+name, 4 if name != 'P' else s)),
            rtol=config.get('orthogonal_rank_rtol', 1e-10),
            absolute_zero_scale=scale if name == 'P' else 0.,
            book=schur.book, label='anatomy_seed_'+name+'_compression')
        records[name].update(
            raw_norm=float(la.norm(raw[name])), source_count=s,
            shape_before_stacking=[n, s, m.shape[1] if name == 'M' else
                                   o.shape[1] if name == 'O' else 1],
            forcing_normalized_norm=norm_ratio(raw[name], forcing),
            provenance={'O': 'independent packed-real receiver loads',
                        'M': 'independent real material mass directions at reference',
                        'P': 'all known illumination forcing'}[name],
            no_truth_or_candidate_state=True)
    return blocks, records, raw


def degree_basis(schur, blocks, families, config=None):
    """Independent O/M/P streams; one fixed degree and no rank search."""
    config = {} if config is None else config
    rtol = config.get('orthogonal_rank_rtol', 1e-10)
    target = int(config.get('target_current_rank', 32))
    degree = int(config.get('degree', 1))
    if degree != 1:
        raise ValueError('A24_ANATOMY_DEGREE_MUST_BE_FROZEN_ONE')
    streams = {name: blocks[name].copy() for name in families}
    latest = {name: blocks[name].copy() for name in families}
    correction = np.empty((schur.n, 0), dtype=np.complex128)
    layers, steps = [], []
    for d in range(degree+1):
        if d:
            for name in families:
                action = schur.feedback(latest[name], adjoint=name == 'O')
                latest[name], rec = orth_basis(
                    action, against=streams[name], rtol=rtol,
                    book=schur.book, label='anatomy_'+name+'_own_stream_QR')
                streams[name] = np.column_stack((streams[name], latest[name]))
                steps.append({'family': name, 'degree': d, **rec})
        joined = np.column_stack([latest[name] for name in families])
        q, rec = orth_basis(
            joined, against=np.column_stack((schur.U, correction)),
            rank=max(0, target-schur.retained_rank-correction.shape[1]),
            rtol=rtol, book=schur.book, label='anatomy_joint_QR')
        correction = np.column_stack((correction, q))
        layers.extend([d]*q.shape[1])
        steps.append({'family': 'joint', 'degree': d, **rec})
    Z = np.column_stack((schur.U, correction))
    return Z, {'retained_rank': schur.retained_rank,
               'correction_rank': correction.shape[1], 'union_rank': Z.shape[1],
               'target_current_rank': target, 'rank_deficient': Z.shape[1] < target,
               'padding': 0, 'degree': degree, 'degree_layers': layers,
               'stream_records': steps,
               'orthogonality_error': float(la.norm(Z.conj().T@Z-np.eye(Z.shape[1])))}


def tsom_spaces(G, O, internal_rank=32, *, rtol=1e-10, book=None):
    """Three explicitly different spectral spaces, not a TSOM reproduction."""
    book = get_ledger() if book is None else book
    n = G.shape[1]
    with book.span('anatomy_TSOM_SVD', evaluator_dense_oracles=1,
                   svd_calls=4, array_bytes=3*np.asarray(G).nbytes):
        _, singular_g, vh = la.svd(G, full_matrices=False)
        keep_g = min(int(internal_rank), int(np.count_nonzero(
            singular_g > rtol*singular_g[0])))
        D = vh[:keep_g].conj().T
        # Null(O*D) yields A intersection D, including the dimension deficit.
        _, singular_od, vh_od = la.svd(O.conj().T@D, full_matrices=True)
        od_scale = float(singular_od[0]) if singular_od.size else 0.
        od_rank = int(np.count_nonzero(singular_od > rtol*max(1., od_scale)))
        ideal = D @ vh_od[od_rank:].conj().T
        projected_raw = D-O@(O.conj().T@D)
        projected, projected_record = orth_basis(
            projected_raw, rtol=rtol, book=book, label='anatomy_projected_TSOM_QR')
        Q_A = la.qr(O, mode='full')[0][:, O.shape[1]:]
        _, singular_restricted, vh_restricted = la.svd(G@Q_A, full_matrices=False)
        keep_restricted = min(int(internal_rank), int(np.count_nonzero(
            singular_restricted > rtol*singular_restricted[0])))
        restricted = Q_A @ vh_restricted[:keep_restricted].conj().T
        gram_direct = Q_A.conj().T @ G.conj().T @ G @ Q_A
        gram_from_svd = (vh_restricted.conj().T * singular_restricted**2) @ vh_restricted
        P_A = np.eye(n)-O@O.conj().T
        P_D = D@D.conj().T
        return {'ideal_intersection': ideal, 'projected_TSOM': projected,
                'restricted_G': restricted}, {
            'observable_rank': O.shape[1], 'internal_rank': keep_g,
            'intersection_rank': ideal.shape[1],
            'projected_rank': projected.shape[1],
            'restricted_G_rank': restricted.shape[1],
            'intersection_membership_error': float(la.norm(O.conj().T@ideal)),
            'projected_not_in_D_norm': float(la.norm(projected-P_D@projected)),
            'projector_commutator_norm': float(la.norm(P_A@P_D-P_D@P_A)),
            'restricted_gram_identity_error': relative_error(gram_from_svd, gram_direct),
            'restricted_ambiguous_membership_error': float(la.norm(O.conj().T@restricted)),
            'internal_singular_values': singular_g.tolist(),
            'restricted_singular_values': singular_restricted.tolist(),
            'projected_compression': projected_record,
            'scope': 'spectral anatomy; no reliable iterative SOM/FFT-TSOM baseline claimed'}


def _combine(retained, correction, target, rtol, book):
    Q, rec = orth_basis(correction, against=retained,
                        rank=max(0, target-retained.shape[1]), rtol=rtol, book=book)
    Z = np.column_stack((retained, Q))
    return Z, {'retained_rank': retained.shape[1], 'correction_rank': Q.shape[1],
               'union_rank': Z.shape[1], 'target_current_rank': target,
               'rank_deficient': Z.shape[1] < target, 'padding': 0,
               'correction_compression': rec}


def _normal_probes(rng, rows, columns):
    p = rng.standard_normal((rows, columns))
    return p / la.norm(p, axis=0)


def _cost_snapshot(book):
    return {'counts': dict(book.counts), 'exclusive_walls': dict(book.walls)}


def _base_record(background, method):
    return {'case_id': 'anatomy_'+background+'_'+method, 'parent_id': None,
            'background': background, 'amplitude': None, 'noise': None,
            'method': method, 'status': 'NOT_RUN', 'reason': None,
            'actual_rank': None, 'material_nrmse': None, 'delta_nrmse': None,
            'full_data_residual': None, 'state_residual': None,
            'material_to_data_transfer_error': None, 'adjoint_pullback_error': None,
            'gradient_cosine': None, 'core_margins': None,
            'offline_s': None, 'online_s': None, 'rhs_counts': None,
            'scope': 'A1 tiny physical anatomy; no reconstructed image'}


def _candidate(chi_b, points):
    """Independent fixed passive hypothesis, unrelated to four B0 parent masks."""
    x, y = points[:, :2].T
    return chi_b + .12*np.cos(2*np.pi*x)*np.sin(2*np.pi*y) + .01j*np.cos(2*np.pi*y)


class _ProjectionEvaluator:
    """Tiny fixed-current audit with the same native material map a=chi."""
    def __init__(self, physics, cache, Z, chi, affine, config):
        self.physics, self.cache, self.Z = physics, cache, Z
        self.chi, self.affine, self.book = chi, affine, physics.book
        with self.book.span('anatomy_projected_core_assembly',
                            internal_kernel_rhs=Z.shape[1],
                            projected_factorizations=1):
            self.L = np.eye(physics.n)-chi[:, None]*physics.G
            self.A = Z.conj().T@self.L@Z
            self.margin = guard_core(self.A, config, 'anatomy_projection')
            self.factor = la.lu_factor(self.A)
        forcing = ((chi-cache.chi_b)[:, None]*cache.eb if affine else
                   chi[:, None]*physics.incident)
        self.current = self.apply(forcing)
        if affine:
            self.current += cache.state_b.current
        self.field = physics.incident+physics.green(self.current)
        self.data = physics.observe(self.current)

    def apply(self, rhs, adjoint=False):
        columns = 1 if rhs.ndim == 1 else rhs.shape[1]
        with self.book.span('anatomy_projection_adjoint' if adjoint else 'anatomy_projection',
                            reduced_core_rhs=columns):
            return self.Z@la.lu_solve(self.factor, self.Z.conj().T@rhs,
                                       trans=2 if adjoint else 0)

    def jvp(self, delta_mass):
        delta = mass_unpack(delta_mass, self.physics.volume)
        return pack(self.physics.observe(self.apply(delta[:, None]*self.field)))

    def adjoint(self, load):
        r = unpack(load, self.physics.q, self.physics.s)
        z = self.apply(self.physics.observe(r, adjoint=True), adjoint=True)
        return self.physics.material_pullback(self.field, z)


def _task_metrics(subject, full, physics, eval_material, eval_loads,
                  exact_transfer, exact_pullback):
    predicted_transfer = np.column_stack([subject.jvp(v) for v in eval_material.T])
    predicted_pullback = np.column_stack([subject.adjoint(v) for v in eval_loads.T])
    cosines = []
    duality_errors = []
    for a, b in zip(predicted_pullback.T, exact_pullback.T):
        den = float(la.norm(a)*la.norm(b))
        if den > 0.:
            cosines.append(float(np.dot(a, b)/den))
    for v, load, jv, gradient in zip(eval_material.T, eval_loads.T,
                                    predicted_transfer.T, predicted_pullback.T):
        scale = float(la.norm(load)*la.norm(jv)+la.norm(v)*la.norm(gradient))
        if scale > 0.:
            duality_errors.append(abs(float(np.dot(load, jv)-np.dot(v, gradient)))/scale)
    return {'full_data_residual': relative_error(subject.data, full.data),
            'material_to_data_transfer_error': relative_error(predicted_transfer, exact_transfer),
            'adjoint_pullback_error': relative_error(predicted_pullback, exact_pullback),
            'adjoint_error': max(duality_errors) if duality_errors else None,
            'gradient_cosine': min(cosines) if cosines else None,
            'gradient_cosine_nonzero_loads': len(cosines),
            'data_error_absolute': float(la.norm(subject.data-full.data))}, {
            'transfer': predicted_transfer, 'pullback': predicted_pullback}


def anatomy(config, out, book=None):
    """Return JSON-serializable records; budget stops retain all planned rows."""
    from .physics import Physics2D
    from .relative_feedback import ReferenceCache, RelativeFeedbackModel
    from .cases import backgrounds
    book = get_ledger() if book is None else book
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    methods = ['classical_observable', 'ideal_tsom_intersection', 'projected_tsom',
               'restricted_G', 'original_OPM_receiver', 'nonanchor_dropP_negative',
               'source_anchored_OPM', 'source_anchored_OM', 'affine_source_OM',
               'affine_current_ROM', 'A23_style_source_replace',
               'relative_L', 'exact_adjoint_control_F', 'relative_R16',
               'relative_R32_diagnostic', 'relative_R16_local_diagnostic']
    records = [_base_record(bg, method) for bg in ('weak', 'ring') for method in methods]
    lookup = {(r['background'], r['method']): r for r in records}
    checks, failures, vectors = {}, [], {}
    current_background, current_method = None, None
    started = time.perf_counter()
    try:
        physics = Physics2D(grid=int(config.get('anatomy_grid', 8)), book=book, config=config)
        if physics.n > 64:
            raise ValueError('ANATOMY_DENSE_ORACLE_LIMIT_64_CURRENT_COORDINATES')
        rtol = config.get('orthogonal_rank_rtol', 1e-10)
        target = int(config.get('target_current_rank', 32))
        master = int(config.get('master_seed', 241008))
        probe_count = int(config.get('independent_material_probes', 8))
        load_count = int(config.get('independent_data_loads', 8))
        # O/M seeds and held-out task directions have disjoint fixed seed domains.
        mp = _normal_probes(np.random.default_rng([master, 1101]), 2*physics.N, probe_count)
        op = _normal_probes(np.random.default_rng([master, 2202]), 2*physics.q*physics.s, load_count)
        ep = _normal_probes(np.random.default_rng([master, 3303]), 2*physics.N, probe_count)
        el = _normal_probes(np.random.default_rng([master, 4404]), 2*physics.q*physics.s, load_count)
        vectors.update(material_seed_probes=mp, data_seed_probes=op,
                       independent_material_tasks=ep, independent_data_loads=el)
        with book.span('anatomy_observable_SVD', svd_calls=1, array_bytes=physics.S.nbytes):
            _, singular_s, vh_s = la.svd(physics.S, full_matrices=False)
            available = int(np.count_nonzero(singular_s > rtol*singular_s[0]))
            receiver = vh_s[:min(int(config.get('receiver_retained_rank', 8)), available)].conj().T
            observable = vh_s[:min(int(config.get('observable_rank', 16)), available)].conj().T
        spectral, spectral_record = tsom_spaces(physics.G, observable, target, rtol=rtol, book=book)
        for background, chi_b in backgrounds(physics.points, config).items():
            book.check()
            current_background = background
            setup_started = time.perf_counter()
            cache = ReferenceCache(physics, chi_b, book=book, config=config)
            forcing = chi_b[:, None]*physics.incident
            source_basis, source_rank_record = orth_basis(cache.state_b.current, book=book, rtol=rtol)
            U_anchor, anchor_rank = orth_basis(np.column_stack((cache.state_b.current, receiver)),
                                               book=book, rtol=rtol)
            source_replace, replace_source_record = orth_basis(
                cache.state_b.current, rank=receiver.shape[1], book=book, rtol=rtol)
            remaining_receiver, replace_receiver_record = orth_basis(
                receiver, against=source_replace,
                rank=max(0, receiver.shape[1]-source_replace.shape[1]), book=book, rtol=rtol)
            U_replace = np.column_stack((source_replace, remaining_receiver))
            schurs = {name: SchurAudit(cache.state_b.L, U, config, book)
                      for name, U in (('anchor', U_anchor), ('receiver', receiver),
                                      ('source_replace', U_replace))}
            seed_sets = {name: source_seed_banks(schur, forcing, cache.eb, physics.S,
                                                  physics.volume, mp, op, config)
                         for name, schur in schurs.items()}
            bases = {}
            basis_records = {}
            for method, name, families in (
                    ('original_OPM_receiver', 'receiver', 'OPM'),
                    ('nonanchor_dropP_negative', 'receiver', 'OM'),
                    ('source_anchored_OPM', 'anchor', 'OPM'),
                    ('source_anchored_OM', 'anchor', 'OM'),
                    ('affine_source_OM', 'receiver', 'OM'),
                    ('A23_style_source_replace', 'source_replace', 'OM')):
                bases[method], basis_records[method] = degree_basis(
                    schurs[name], seed_sets[name][0], families, config)
            bases['classical_observable'] = observable
            basis_records['classical_observable'] = {
                'retained_rank': observable.shape[1], 'correction_rank': 0,
                'union_rank': observable.shape[1], 'target_current_rank': target,
                'rank_deficient': observable.shape[1] < target, 'padding': 0}
            for method, spectral_name in (('ideal_tsom_intersection', 'ideal_intersection'),
                                          ('projected_tsom', 'projected_TSOM'),
                                          ('restricted_G', 'restricted_G')):
                bases[method], basis_records[method] = _combine(
                    observable, spectral[spectral_name], target, rtol, book)
            # Strong ordinary affine ROM shares the same offset and receiver budget.
            material_rhs = np.einsum('np,ns->nsp',
                (mp[:physics.N]+1j*mp[physics.N:])/np.sqrt(physics.volume), cache.eb).reshape(physics.n, -1)
            loads = np.stack([unpack(v, physics.q, physics.s) for v in op.T], axis=-1)
            primal = cache.solve_ref(material_rhs)
            dual = cache.solve_ref(physics.observe(loads.reshape(physics.q, -1), adjoint=True), adjoint=True)
            bases['affine_current_ROM'], basis_records['affine_current_ROM'] = _combine(
                receiver, np.column_stack((primal, dual)), target, rtol, book)
            schur_cert, Q_complement = schurs['anchor'].inverse_certificate()
            P_raw = seed_sets['anchor'][2]['P']
            Pi_source = schurs['anchor'].project(cache.state_b.current)
            left, right = bases['source_anchored_OPM'], bases['source_anchored_OM']
            same_projector = relative_error(left@left.conj().T, right@right.conj().T)
            neg_left, neg_right = bases['original_OPM_receiver'], bases['nonanchor_dropP_negative']
            same_rank = left.shape[1] == right.shape[1]
            non = schurs['receiver']
            HU = non.project((np.eye(physics.n)-cache.state_b.L)@non.U)
            a_star = non.coarse(non.U.conj().T@cache.state_b.current)
            coupled_input = non.K(cache.state_b.current)-HU@a_star
            coupled = coupled_input-non.feedback(coupled_input)
            uncoupled_input = non.K(cache.state_b.current)
            uncoupled = uncoupled_input-non.feedback(uncoupled_input)
            source_checks = {
                'P_forcing_normalized_norm': norm_ratio(P_raw, forcing),
                'source_projection_error': norm_ratio(Pi_source, cache.state_b.current),
                'same_U_basis_projector_error': same_projector,
                'same_U_same_probe_equal_rank': same_rank,
                'nonanchor_P_forcing_normalized_norm': norm_ratio(seed_sets['receiver'][2]['P'], forcing),
                'nonanchor_dropP_projector_difference': relative_error(
                    neg_left@neg_left.conj().T, neg_right@neg_right.conj().T),
                'retained_coupling_identity_error': relative_error(coupled, non.K(forcing)),
                'omitted_retained_coupling_error': relative_error(uncoupled, non.K(forcing)),
                'material_complement_excitation_norm': float(la.norm(seed_sets['anchor'][2]['M'])),
                'forcing_scale': float(la.norm(forcing)),
                'source_rank': source_basis.shape[1], 'anchor_retained_rank': U_anchor.shape[1],
                'source_rank_record': source_rank_record, 'anchor_rank_record': anchor_rank,
                'source_replace_source_record': replace_source_record,
                'source_replace_receiver_record': replace_receiver_record,
                'same_U_seed_records': seed_sets['anchor'][1],
                'spectral': spectral_record, **schur_cert}
            source_checks['identity_status'] = 'PASS' if (
                same_rank and all(source_checks[k] is not None and source_checks[k] <=
                                  config.get('identity_tolerance', 1e-10) for k in
                                  ('P_forcing_normalized_norm', 'source_projection_error',
                                   'same_U_basis_projector_error', 'inverse_schur_error',
                                   'retained_coupling_identity_error'))) else 'FAIL'
            checks[background] = source_checks
            vectors.update({background+'_reference_currents': cache.state_b.current,
                            background+'_anchor_U': U_anchor,
                            background+'_receiver_U': receiver,
                            background+'_source_replace_U': U_replace,
                            background+'_P_raw': P_raw,
                            background+'_anchor_complement': Q_complement})
            shared_setup_s = time.perf_counter()-setup_started
            source_checks['shared_background_and_current_basis_setup_seconds'] = shared_setup_s
            # The candidate/full state is first accessed after all current bases freeze.
            chi = _candidate(chi_b, physics.points)
            full = physics.full_state(chi)
            with book.scope('anatomy_evaluator'):
                exact_transfer = np.column_stack([pack(physics.observe(
                    physics.solve_factor(full.factor, mass_unpack(v, physics.volume)[:, None]*full.field,
                                         role='anatomy_exact_material_tangent'))) for v in ep.T])
                exact_pullback = np.column_stack([physics.material_pullback(full.field,
                    physics.solve_factor(full.factor, physics.observe(
                        unpack(v, physics.q, physics.s), adjoint=True), adjoint=True,
                        role='anatomy_exact_adjoint')) for v in el.T])
            vectors.update({background+'_candidate': chi,
                            background+'_exact_transfer': exact_transfer,
                            background+'_exact_pullback': exact_pullback})
            for method in methods:
                book.check()
                current_method = method
                record = lookup[(background, method)]
                before = _cost_snapshot(book)
                case_started = time.perf_counter()
                try:
                    if method in bases:
                        affine = method in ('affine_source_OM', 'affine_current_ROM')
                        subject = _ProjectionEvaluator(physics, cache, bases[method], chi, affine, config)
                        metrics, detail = _task_metrics(subject, full, physics, ep, el,
                                                         exact_transfer, exact_pullback)
                        record.update(metrics, **basis_records[method],
                            actual_rank=bases[method].shape[1], core_margins=subject.margin,
                            affine_offset=affine,
                            offset_storage_bytes=cache.state_b.current.nbytes if affine else 0,
                            source_reconstruction_error=norm_ratio(
                                cache.state_b.current-bases[method]@(bases[method].conj().T@cache.state_b.current),
                                cache.state_b.current),
                            current_reconstruction_error=relative_error(subject.current, full.current),
                            projection_data_error=metrics['full_data_residual'],
                            delta_data_error=norm_ratio(subject.data-full.data, full.data-cache.yb),
                            state_residual=norm_ratio(subject.L@subject.current-chi[:, None]*physics.incident,
                                                     chi[:, None]*physics.incident))
                        record['offline_s'] = shared_setup_s
                        vectors[background+'_'+method+'_basis'] = bases[method]
                    else:
                        kind = 'L' if method == 'relative_L' else 'F' if method == 'exact_adjoint_control_F' else 'R'
                        rank = int(config.get('diagnostic_return_rank', 32)) if 'R32' in method else int(config.get('primary_return_rank', 16))
                        local = method == 'relative_R16_local_diagnostic'
                        feedback_setup_started = time.perf_counter()
                        with book.scope('anatomy_offline_feedback_setup'):
                            model = RelativeFeedbackModel(cache, kind=kind, rank=rank, local=local,
                                                          seed=master, config=config)
                        feedback_setup_s = time.perf_counter()-feedback_setup_started
                        state = model.forward(chi)
                        class ModelTasks:
                            data = state.data
                            def jvp(self, v):
                                return model.jvp(chi, v, state)
                            def adjoint(self, v):
                                return model.adjoint(chi, v, state)
                        metrics, detail = _task_metrics(ModelTasks(), full, physics, ep, el,
                                                         exact_transfer, exact_pullback)
                        record.update(metrics, actual_rank=model.actual_rank if kind == 'R' else None,
                                      material_dimension=2*physics.N, source_dimension=physics.n,
                                      core_margins=state.margins, affine_offset=True,
                                      offset_storage_bytes=cache.state_b.current.nbytes,
                                      feedback_rank=model.actual_rank if kind == 'R' else 0 if kind == 'L' else physics.n)
                        record['offline_s'] = shared_setup_s+feedback_setup_s
                        record['additional_feedback_setup_seconds'] = feedback_setup_s
                        if kind == 'R':
                            wprobe = np.stack([mass_unpack(v, physics.volume) for v in ep.T], axis=1)
                            exact_return = cache.gb(wprobe)
                            approximate_return = model.feedback_apply(wprobe)
                            record['feedback_action_error'] = relative_error(approximate_return, exact_return)
                            defect = (chi-chi_b)[:, None]*(cache.gb(state.w)-model.feedback_apply(state.w))
                            implicit = cache.state_b.current+cache.solve_ref(state.w)
                            native_residual = full.L@implicit-chi[:, None]*physics.incident
                            record['state_residual'] = norm_ratio(native_residual, chi[:, None]*physics.incident)
                            # Normalize this near-zero identity by full forcing, not the defect itself.
                            record['state_defect_identity_error'] = norm_ratio(native_residual+defect,
                                                                              chi[:, None]*physics.incident)
                            vectors[background+'_'+method+'_defect'] = defect
                    record.update(status='OK', reason=None,
                                  online_s=time.perf_counter()-case_started,
                                  rhs_counts=book.delta(before)['counts'],
                                  peak_bytes=book.receipt()['peak_cpu_rss_bytes'],
                                  costs=book.delta(before))
                    vectors[background+'_'+method+'_transfer'] = detail['transfer']
                    vectors[background+'_'+method+'_pullback'] = detail['pullback']
                except NumericalFailure as exc:
                    record.update(status='FAIL', reason=str(exc),
                                  online_s=time.perf_counter()-case_started,
                                  rhs_counts=book.delta(before)['counts'])
                    failures.append({'case_id': record['case_id'], 'status': 'FAIL', 'reason': str(exc)})
            checks[background]['same_U_material_transfer_error'] = relative_error(
                vectors[background+'_source_anchored_OPM_transfer'],
                vectors[background+'_source_anchored_OM_transfer']) if (
                background+'_source_anchored_OPM_transfer' in vectors and
                background+'_source_anchored_OM_transfer' in vectors) else None
            checks[background]['same_U_adjoint_pullback_error'] = relative_error(
                vectors[background+'_source_anchored_OPM_pullback'],
                vectors[background+'_source_anchored_OM_pullback']) if (
                background+'_source_anchored_OPM_pullback' in vectors and
                background+'_source_anchored_OM_pullback' in vectors) else None
            for field in ('same_U_material_transfer_error', 'same_U_adjoint_pullback_error'):
                if checks[background][field] is None or checks[background][field] > config.get('identity_tolerance', 1e-10):
                    checks[background]['identity_status'] = 'FAIL'
    except BudgetExceeded as exc:
        failures.append({'background': current_background, 'method': current_method,
                         'status': 'BUDGET_STOP', 'reason': str(exc)})
        if current_background is not None and current_method is not None:
            record = lookup[(current_background, current_method)]
            if record['status'] == 'NOT_RUN':
                record.update(status='BUDGET_STOP', reason=str(exc))
        for record in records:
            if record['status'] == 'NOT_RUN':
                record['reason'] = 'NOT_RUN_AFTER_BUDGET_STOP'
    except (NumericalFailure, ValueError) as exc:
        failures.append({'background': current_background, 'method': current_method,
                         'status': 'FAIL', 'reason': str(exc)})
        for record in records:
            if record['status'] == 'NOT_RUN':
                record['reason'] = 'NOT_RUN_AFTER_SETUP_FAILURE'
    status = 'COMPLETE' if all(r['status'] == 'OK' for r in records) else 'PARTIAL'
    result = {'status': status, 'scope': 'A0/A1 algebra and tiny 2D physical anatomy only',
              'records': records, 'checks': checks, 'failures': failures,
              'elapsed_wall_seconds': time.perf_counter()-started,
              'G1_identity_status': 'PASS' if len(checks) == 2 and all(
                  c['identity_status'] == 'PASS' for c in checks.values()) else 'NOT_RUN' if not checks else 'FAIL',
              'G2_image_condition': 'NOT_RUN_ANATOMY_HAS_NO_IMAGES',
              'training': 'DISABLED', 'dense_oracle_runtime_use': False,
              'independent_probe_seed_domains': {'M': 1101, 'O': 2202, 'task_material': 3303, 'task_load': 4404},
              'source_replace_scope': 'A23-style allocation confound: all eight A24 sources replace receiver8; historical A23 used six sources plus two receivers',
              'ledger': book.receipt()}
    # The CLI's binary gate key is FAIL when verification is incomplete; the
    # detailed alias and NOT_RUN rows retain the reason for that decision.
    result['G1_status'] = 'PASS' if result['G1_identity_status'] == 'PASS' else 'FAIL'
    result['offline_time_definition'] = 'shared setup repeated descriptively per record; do not sum rows; add each incremental feedback setup once'
    # Durable epilogue is charged by inclusive elapsed time even after a stop.
    io_started = time.perf_counter()
    np.savez_compressed(out/'anatomy_vectors.npz', **vectors)
    book.append({'event': 'anatomy_diagnostic_cache_write', 'status': 'OK',
                 'phase': 'anatomy_evaluator', 'array_bytes': sum(v.nbytes for v in vectors.values()),
                 'wall_seconds': time.perf_counter()-io_started,
                 'reason': 'durable epilogue; inclusive ledger elapsed includes I/O'})
    result['vectors_path'] = str((out/'anatomy_vectors.npz').resolve())
    result['ledger'] = book.receipt()
    write_json(out/'ANATOMY.json', result)
    return plain(result)
