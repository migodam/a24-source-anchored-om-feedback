import json,tempfile,unittest
from pathlib import Path
from a24.gates import decide
from a24.pilot import write_csv

class GateAggregationTests(unittest.TestCase):
    def test_observed_universal_threshold_violation_is_fail_despite_missing_cases(self):
        root=Path(__file__).resolve().parents[1]
        config=json.loads((root/'configs/a24_frozen.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            write_csv(out/'TASK_AUDIT.csv',[{'method':'R16','case_id':'fixed_independent_probe',
                'status':'OK','independent_transfer_error':.06,
                'independent_adjoint_error':.02,'gradient_cosine':.999}])
            result=decide(config,out)
            self.assertEqual(result['G2']['status'],'FAIL')
            self.assertFalse(result['G2']['coverage_complete'])
            self.assertEqual(len(result['G2']['observed_task_counterexamples']),1)
            self.assertEqual(result['G3']['status'],'HOLD')
    def test_missing_cases_without_counterexample_remain_hold(self):
        root=Path(__file__).resolve().parents[1]
        config=json.loads((root/'configs/a24_frozen.json').read_text())
        with tempfile.TemporaryDirectory() as d:
            result=decide(config,Path(d))
            self.assertEqual(result['G2']['status'],'HOLD')
