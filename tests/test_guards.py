from __future__ import annotations
import tempfile,time,unittest
from pathlib import Path
import numpy as np
from a24.contracts import (OnlineObservation, ForbiddenAccess, online_config,
    load_observation, Ledger, guard_core, NumericalFailure,pack,unpack,mass_pack,mass_unpack)
from a20.costs import BudgetExceeded

class GuardTests(unittest.TestCase):
    def test_runtime_config_removes_test_geometry(self):
        out=online_config({'parent_masks':{'secret':1},'truth':1,'grid':8,'master_seed':241008})
        self.assertEqual(out,{'grid':8,'master_seed':241008})
    def test_online_view_rejects_offline_fields(self):
        obs=OnlineObservation(np.zeros((2,3),complex),0.,'tiny')
        for key in ('truth','teacher','support_mask','oracle_currents','full_J','parent_masks'):
            with self.assertRaises(ForbiddenAccess):getattr(obs,key)
    def test_mixed_npz_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'mixed.npz';np.savez(path,data=np.zeros((2,3),complex),sigma=0.,case_id='x',truth=np.ones(3))
            with self.assertRaises(ForbiddenAccess):load_observation(path)
    def test_pack_order_and_transpose(self):
        y=np.array([[1+2j,3+4j],[5+6j,7+8j]])
        np.testing.assert_array_equal(pack(y),[1,5,2,6,3,7,4,8])
        np.testing.assert_array_equal(unpack(pack(y),2,2),y)
    def test_material_mass_chart_roundtrip(self):
        c=np.array([.3+.2j,-.1+.02j]);v=.004
        np.testing.assert_allclose(mass_unpack(mass_pack(c,v),v),c,rtol=1e-14)
    def test_zero_scaled_and_singular_core(self):
        with self.assertRaises(NumericalFailure):guard_core(np.zeros((2,2)),{})
        with self.assertRaises(NumericalFailure):guard_core(np.diag([1,1e-12]),{})
    def test_budget_before_action_and_durable_cap(self):
        with tempfile.TemporaryDirectory() as d:
            book=Ledger(Path(d)/'cost.jsonl',wall_limit=30)
            book.reserve('label',1)
            with self.assertRaises(BudgetExceeded):book.reserve('label',1)
            self.assertEqual(book.reservations['label'],1)
            book.deadline=time.perf_counter()-1
            with self.assertRaises(BudgetExceeded):book.check()
    def test_failed_span_charged_without_nested_doublecount(self):
        with tempfile.TemporaryDirectory() as d:
            book=Ledger(Path(d)/'cost.jsonl',wall_limit=30)
            with self.assertRaises(RuntimeError):
                with book.span('parent'):
                    with book.span('inner',rhs=2):raise RuntimeError('expected failure')
            self.assertEqual(book.counts['rhs'],2)
            self.assertGreaterEqual(book.walls['parent'],0.)
            self.assertGreaterEqual(book.walls['inner'],0.)
            self.assertIn('FAILED',(Path(d)/'cost.jsonl').read_text())
