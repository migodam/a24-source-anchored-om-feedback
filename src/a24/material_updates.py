"""Shared, constrained material TV proximal steps in real mass coordinates.

The two channels are [Re chi, Im chi], each multiplied by sqrt(cell volume).
TV uses one Euclidean norm over all outgoing spatial edges and both channels
at each cell. Boundary edges vanish (forward differences / Neumann boundary).
There is no ridge term and no projection of a finished unconstrained solve.
"""
from __future__ import annotations

from contextlib import nullcontext
from numbers import Integral
import time

import numpy as np

from .contracts import NumericalFailure


def _grid_shape(grid_shape):
    shape = tuple(grid_shape)
    if (not shape or any(isinstance(n, bool) or not isinstance(n, Integral)
                         or n < 1 for n in shape)):
        raise ValueError('POSITIVE_INTEGER_GRID_SHAPE_REQUIRED')
    return tuple(int(n) for n in shape)


def _mass_vector(value, n, name):
    raw = np.asarray(value)
    if np.iscomplexobj(raw) or raw.shape != (2*n,):
        raise ValueError(name + ':REAL_MATERIAL_MASS_COORDINATES_REQUIRED')
    value = np.asarray(raw, dtype=np.float64)
    if not np.all(np.isfinite(value)):
        raise ValueError(name + ':FINITE_MATERIAL_REQUIRED')
    return value


def _cell_volume(volume):
    value = float(volume)
    if not np.isfinite(value) or value <= 0:
        raise ValueError('POSITIVE_FINITE_CELL_VOLUME_REQUIRED')
    return value


def _coefficient(shape, volume):
    return volume**((len(shape)-1)/len(shape))/np.sqrt(volume)


def _gradient(x, shape):
    n = int(np.prod(shape))
    field = np.stack((x[:n], x[n:]), axis=-1).reshape(shape+(2,))
    out = np.zeros(shape+(len(shape), 2), dtype=np.float64)
    for axis in range(len(shape)):
        lower = [slice(None)]*len(shape)
        upper = [slice(None)]*len(shape)
        lower[axis] = slice(0, -1)
        upper[axis] = slice(1, None)
        out[tuple(lower)+(axis, slice(None))] = (
            field[tuple(upper)]-field[tuple(lower)])
    return out


def _gradient_adjoint(p, shape):
    field = np.zeros(shape+(2,), dtype=np.float64)
    for axis in range(len(shape)):
        lower = [slice(None)]*len(shape)
        upper = [slice(None)]*len(shape)
        lower[axis] = slice(0, -1)
        upper[axis] = slice(1, None)
        edge = p[tuple(lower)+(axis, slice(None))]
        field[tuple(lower)] -= edge
        field[tuple(upper)] += edge
    return np.r_[field[..., 0].reshape(-1), field[..., 1].reshape(-1)]


def material_gradient(x, grid_shape):
    """Unscaled Neumann D; output has shape (*grid_shape, dimension, 2)."""
    shape = _grid_shape(grid_shape)
    return _gradient(_mass_vector(x, int(np.prod(shape)), 'x'), shape)


def material_gradient_adjoint(p, grid_shape):
    """Real Euclidean D*, including arbitrary loads on zero boundary rows."""
    shape = _grid_shape(grid_shape)
    raw = np.asarray(p)
    if np.iscomplexobj(raw) or raw.shape != shape+(len(shape), 2):
        raise ValueError('REAL_MATERIAL_GRADIENT_SHAPE_REQUIRED')
    p = np.asarray(raw, dtype=np.float64)
    if not np.all(np.isfinite(p)):
        raise ValueError('FINITE_MATERIAL_GRADIENT_REQUIRED')
    return _gradient_adjoint(p, shape)


def _cell_norm(p):
    return np.sqrt(np.sum(p*p, axis=(-2, -1)))


def tv_value(x, grid_shape, volume):
    """Physical TV integral of a delta MATERIAL MASS vector.

    With cell side h=volume**(1/d), this is h**(d-1) times
    the joint physical Re/Im forward-difference norm summed over cells.
    Pass x-background to penalize contrast relative to the declared reference.
    """
    shape = _grid_shape(grid_shape)
    volume = _cell_volume(volume)
    x = _mass_vector(x, int(np.prod(shape)), 'delta_x')
    return float(_coefficient(shape, volume)*np.sum(_cell_norm(_gradient(x, shape))))


def _bounds(n, volume, config):
    physical = np.array([config.get('real_lower', -.5),
                         config.get('real_upper', 4.),
                         config.get('imag_lower', 0.),
                         config.get('imag_upper', .5)], dtype=np.float64)
    if (not np.all(np.isfinite(physical)) or physical[0] >= physical[1]
            or physical[2] >= physical[3]):
        raise ValueError('FINITE_ORDERED_PHYSICAL_MATERIAL_BOX_REQUIRED')
    lo = np.sqrt(volume)*np.r_[np.full(n, physical[0]), np.full(n, physical[2])]
    hi = np.sqrt(volume)*np.r_[np.full(n, physical[1]), np.full(n, physical[3])]
    return lo, hi, physical


def _count(book, name, amount=1):
    if book is not None:
        book.counts[name] += int(amount)


def _project_box(value, lo, hi, book, *, diagnostic=False):
    _count(book, 'material_box_projections')
    if diagnostic:
        _count(book, 'material_box_diagnostic_projections')
    return np.minimum(np.maximum(value, lo), hi)


def _project_dual(p, radius, book, *, diagnostic=False):
    _count(book, 'material_dual_projections')
    if diagnostic:
        _count(book, 'material_dual_diagnostic_projections')
    if radius == 0.:
        return np.zeros_like(p)
    factor = np.maximum(1., _cell_norm(p)/radius)
    return p/factor[..., None, None]


def _D(x, shape, book):
    _count(book, 'material_tv_gradient_actions')
    return _gradient(x, shape)


def _DT(p, shape, book):
    _count(book, 'material_tv_gradient_adjoint_actions')
    return _gradient_adjoint(p, shape)


def _diagnostics(x, p, v, background, shape, volume, alpha, coefficient,
                 lo, hi, tau, sigma, mass_scale, material_scale, book):
    """KKT residuals and a stable feasible primal--dual gap.

    The dual is max_{||p_i||<=alpha} min_{u in box}
    .5||u-v||^2 + <D* p,u> - <p,D background>.
    Its minimizer is clip(v-D*p), used only to evaluate the certificate.
    """
    delta_gradient = _D(x-background, shape, book)
    cell_norm = _cell_norm(delta_gradient)
    g = _DT(p, shape, book)
    stationarity = x-v+g
    normal = np.zeros_like(x)
    lower_active = x <= lo
    upper_active = x >= hi
    normal[lower_active] = np.minimum(-stationarity[lower_active], 0.)
    normal[upper_active] = np.maximum(-stationarity[upper_active], 0.)
    stationarity_residual = stationarity+normal
    primal_fixed = _project_box((x-tau*g+tau*v)/(1.+tau), lo, hi,
                                book, diagnostic=True)
    dual_fixed = _project_dual(p+sigma*delta_gradient, alpha, book, diagnostic=True)
    dual_minimizer = _project_box(v-g, lo, hi, book, diagnostic=True)
    difference = x-dual_minimizer
    dual_stationarity = dual_minimizer-v+g
    # This decomposition avoids subtraction of two large objective values.
    tv_complementarity = float(alpha*np.sum(cell_norm)-np.sum(p*delta_gradient))
    box_gap = float(np.dot(difference, dual_stationarity))
    gap = float(.5*np.dot(difference, difference)+box_gap+tv_complementarity)
    objective = float(.5*np.dot(x-v, x-v)+alpha*np.sum(cell_norm))
    dual_excess = np.maximum(_cell_norm(p)-alpha, 0.)
    box_excess = np.maximum(np.maximum(lo-x, x-hi), 0.)
    box_complementarity = float(np.sum(np.abs(normal[lower_active]*(x-lo)[lower_active]))
                                + np.sum(np.abs(normal[upper_active]*(hi-x)[upper_active])))
    components = {
        'primal_stationarity': float(np.linalg.norm(stationarity_residual)/mass_scale),
        'primal_fixed_point': float(np.linalg.norm(x-primal_fixed)/(tau*mass_scale)),
        'dual_fixed_point': float(np.linalg.norm(p-dual_fixed)/(sigma*mass_scale)),
        'dual_feasibility': float(np.linalg.norm(dual_excess)/mass_scale),
        'tv_complementarity': abs(tv_complementarity)/mass_scale**2,
        'box_complementarity': box_complementarity/mass_scale**2,
    }
    physical_feasibility = float(np.max(box_excess)/(np.sqrt(volume)*material_scale))
    return {
        'objective': objective,
        'primal_objective': objective,
        'dual_objective': objective-gap,
        'primal_dual_gap': gap,
        'normalized_gap': abs(gap)/mass_scale**2,
        'kkt_residual': max(components.values()),
        'kkt_components': components,
        'feasibility': physical_feasibility,
        'feasibility_mass_max': float(np.max(box_excess)),
        'dual_feasibility': components['dual_feasibility'],
        'dual_feasibility_max': float(np.max(dual_excess)),
        'tv_complementarity_signed': tv_complementarity,
        'box_gap_term': box_gap,
        'tv': float(coefficient*np.sum(cell_norm)),
    }


def prox_tv_box(v, background, weight, grid_shape, volume, config, book=None):
    """Solve .5||x-v||^2 + weight TV(x-background) + I_box(x).

    A fixed Chambolle--Pock/PDHG scheme uses ||D||<=2sqrt(d),
    tau=sigma=.99/(2sqrt(d)) and theta=1. Each primal step is the
    exact proximal map of the quadratic plus the physical box; the dual
    step is projection onto joint Euclidean TV balls. The default physical
    box is Re[-.5,4], Im[0,.5]. No parameter changes during a solve.

    ``prox_tolerance`` defaults to 1e-6, ``prox_max_iter`` to 1000 (cap
    2000), ``prox_check_every`` to 10, ``prox_raise_on_failure`` to True.
    KKT norms are divided by material_scale*sqrt(N*cell volume), where
    ``prox_material_scale`` (alias ``material_scale``) defaults to 1 physical
    chi unit. Gap and complementarity use the square of this mass scale.
    The separate box tolerance defaults to 1e-10 normalized physical units.
    A failed solve returns explicit metadata if configured not to raise;
    otherwise NumericalFailure carries the same metadata in ``.meta``.
    """
    started = time.perf_counter()
    config = {} if config is None else config
    context = (book.span('material_tv_prox', material_prox_calls=1)
               if book is not None else nullcontext({}))
    with context as row:
        shape = _grid_shape(grid_shape)
        n = int(np.prod(shape))
        volume = _cell_volume(volume)
        v = _mass_vector(v, n, 'v')
        background = _mass_vector(background, n, 'background')
        weight = float(weight)
        tolerance = float(config.get('prox_tolerance', 1e-6))
        feasibility_tolerance = float(config.get('prox_feasibility_tolerance', 1e-10))
        material_scale = float(config.get('prox_material_scale', config.get('material_scale', 1.)))
        max_iter = config.get('prox_max_iter', 1000)
        check_every = config.get('prox_check_every', 10)
        if (not isinstance(max_iter, Integral) or isinstance(max_iter, bool)
                or not 1 <= max_iter <= 2000):
            raise ValueError('PROX_MAX_ITER_MUST_BE_INTEGER_BETWEEN_1_AND_2000')
        if (not isinstance(check_every, Integral) or isinstance(check_every, bool)
                or check_every < 1):
            raise ValueError('POSITIVE_INTEGER_PROX_CHECK_INTERVAL_REQUIRED')
        if (not np.isfinite(weight) or weight < 0.
                or not np.isfinite(tolerance) or tolerance <= 0.
                or not np.isfinite(feasibility_tolerance) or feasibility_tolerance <= 0.
                or not np.isfinite(material_scale) or material_scale <= 0.):
            raise ValueError('FINITE_NONNEGATIVE_WEIGHT_AND_POSITIVE_SCALES_REQUIRED')
        lo, hi, physical_box = _bounds(n, volume, config)
        coefficient = _coefficient(shape, volume)
        alpha = weight*coefficient
        mass_scale = material_scale*np.sqrt(n*volume)
        if (not np.isfinite(alpha) or not np.isfinite(mass_scale)
                or mass_scale <= 0. or not np.isfinite(mass_scale**2)
                or mass_scale**2 <= 0.):
            raise NumericalFailure('MATERIAL_PROX_SCALE_OUTSIDE_FLOAT64_RANGE')
        operator_bound = 2.*np.sqrt(len(shape))
        tau = sigma = .99/operator_bound
        x = _project_box(v.copy(), lo, hi, book)
        p = np.zeros(shape+(len(shape), 2), dtype=np.float64)
        extrapolated = x.copy()
        iterations = 0

        def diagnose():
            return _diagnostics(x, p, v, background, shape, volume, alpha,
                                coefficient, lo, hi, tau, sigma, mass_scale,
                                material_scale, book)

        def accepted(info):
            numbers = [info['kkt_residual'], info['normalized_gap'], info['feasibility']]
            return (all(np.isfinite(value) for value in numbers)
                    and info['kkt_residual'] <= tolerance
                    and info['normalized_gap'] <= tolerance
                    and info['feasibility'] <= feasibility_tolerance)

        info = diagnose()
        converged = accepted(info)
        for iterations in range(1, int(max_iter)+1) if not converged else ():
            if book is not None:
                book.check()
            p = _project_dual(p+sigma*_D(extrapolated-background, shape, book), alpha, book)
            previous = x
            x = _project_box((previous-tau*_DT(p, shape, book)+tau*v)/(1.+tau), lo, hi, book)
            extrapolated = x+(x-previous)
            _count(book, 'material_prox_iterations')
            if iterations % int(check_every) == 0 or iterations == max_iter:
                info = diagnose()
                converged = accepted(info)
                if converged:
                    break
        elapsed = time.perf_counter()-started
        # Estimate peak live NumPy workspace; process RSS is tracked by Ledger.
        array_bytes = (8*(8*len(x)+5*p.size+5*n))
        meta = {
            **info,
            'status': 'CONVERGED' if converged else 'NOT_CONVERGED',
            'converged': bool(converged),
            'iterations': int(iterations),
            'max_iter': int(max_iter),
            'tolerance': tolerance,
            'feasibility_tolerance': feasibility_tolerance,
            'algorithm': 'fixed_chambolle_pock_pdhg',
            'difference_operator_norm_upper_bound': float(operator_bound),
            'tau': float(tau), 'sigma': float(sigma), 'theta': 1.,
            'tau_sigma_norm_bound_squared': float(tau*sigma*operator_bound**2),
            'weight': weight, 'tv_physical_coefficient': float(coefficient),
            'dual_ball_radius': float(alpha),
            'physical_material_scale': material_scale,
            'physical_mass_scale': float(mass_scale),
            'normalization': 'material_scale * sqrt(number_of_cells * cell_volume)',
            'physical_box': physical_box.tolist(),
            'grid_shape': list(shape), 'volume': volume,
            'elapsed_seconds': elapsed, 'array_bytes_estimate': int(array_bytes),
        }
        row.update(result_status=meta['status'], iterations=int(iterations),
                   kkt_residual=meta['kkt_residual'], normalized_gap=meta['normalized_gap'],
                   feasibility=meta['feasibility'], array_bytes_estimate=int(array_bytes))
        if not converged:
            _count(book, 'material_prox_failures')
            if config.get('prox_raise_on_failure', True):
                error = NumericalFailure('TV_PROX_NOT_CONVERGED:' + str(iterations))
                error.meta = meta
                raise error
        return x, meta


def normalized_backprojection(background, residual, forward, adjoint, *,
                              weight, grid_shape, volume, config, book=None):
    """One normalized Born/BP step, followed by the same constrained TV prox.

    ``forward``/``adjoint`` must be the same frozen REAL whitened linear
    data map in material mass coordinates. ``residual`` is measured-minus-
    reference data. The standard one-dimensional least-squares step is
    ||J*residual||^2/||J J*residual||^2. Physics actions must be charged by
    the supplied callbacks; this wrapper also counts its callback calls.
    This function does not construct a Jacobian or select a new prior.
    """
    started = time.perf_counter()
    context = (book.span('material_normalized_backprojection', material_bp_calls=1)
               if book is not None else nullcontext({}))
    with context as row:
        shape = _grid_shape(grid_shape)
        n = int(np.prod(shape))
        background = _mass_vector(background, n, 'background')
        raw = np.asarray(residual)
        if (np.iscomplexobj(raw) or raw.ndim != 1
                or not np.all(np.isfinite(raw))):
            raise ValueError('FINITE_REAL_PACKED_BP_RESIDUAL_REQUIRED')
        residual = np.asarray(raw, dtype=np.float64)
        if book is not None:
            book.check()
        _count(book, 'material_bp_adjoint_calls')
        direction = _mass_vector(adjoint(residual), n, 'backprojection')
        numerator = float(np.dot(direction, direction))
        denominator = None
        step = 0.
        if numerator > 0.:
            if book is not None:
                book.check()
            _count(book, 'material_bp_forward_calls')
            response = np.asarray(forward(direction))
            if (np.iscomplexobj(response) or response.shape != residual.shape
                    or not np.all(np.isfinite(response))):
                raise ValueError('FINITE_REAL_PACKED_BP_RESPONSE_REQUIRED')
            denominator = float(np.dot(response, response))
            if not np.isfinite(denominator) or denominator <= 0.:
                raise NumericalFailure('BP_ZERO_RESPONSE_WITH_NONZERO_ADJOINT')
            step = numerator/denominator
            if not np.isfinite(step):
                raise NumericalFailure('BP_NONFINITE_NORMALIZED_STEP')
        x, prox_meta = prox_tv_box(background+step*direction, background, weight,
                                   shape, volume, config, book=book)
        meta = {'method': 'one_shot_normalized_backprojection',
                'step_size': step, 'adjoint_norm_squared': numerator,
                'response_norm_squared': denominator,
                'zero_adjoint': numerator == 0., 'prox': prox_meta,
                'elapsed_seconds': time.perf_counter()-started}
        row.update(step_size=step, result_status=prox_meta['status'])
        return x, meta
