import shutil
import json
import hashlib

from analysis.banking_followup import PROOF, verified_corrective_code
from ai_models.re2_detection import decide


def test_correction_requires_intact_recorded_evidence(tmp_path):
    assert verified_corrective_code()['verified'] is True
    folder = tmp_path / 'proof'
    shutil.copytree(PROOF, folder)
    trial = folder / 'patched-trials.json'
    trial.write_text(trial.read_text() + ' ')
    assert verified_corrective_code(folder) is None
    assert verified_corrective_code(tmp_path / 'absent') is None


def test_detector_never_uses_future_calibration_or_observations():
    calibration = {'status': 'calibrated', 'validation_end': 10, 'threshold': 5,
                   'points': [{'timestamp': 11, 'score': 2, 'has_targets': True},
                              {'timestamp': 20, 'score': 50, 'has_targets': True}]}
    assert decide(calibration, 10)['status'] == 'insufficient_evidence'
    assert decide(calibration, 15)['status'] == 'no_deviation_in_observed_metrics'
    assert decide(calibration, 20)['status'] == 'deviation_detected'


def test_unverified_repeat_summary_cannot_be_displayed_as_accuracy(tmp_path,monkeypatch):
    import analysis.banking_followup as followup
    monkeypatch.setattr(followup,'ROOT',tmp_path)
    folder=tmp_path/'results/final_validation';folder.mkdir(parents=True)
    report={'status':'evaluated','export_sha256':'archive-a'}
    (folder/'report.json').write_text(json.dumps(report))
    assert followup.verified_final_study() is None
    cleanup={'status':'terminated','root_volume_deleted':True,'final_export_sha256':'archive-a'}
    (folder/'aws-cleanup.json').write_text(json.dumps(cleanup))
    (folder/'predictions-before-label-scoring.json').write_text('[]')
    def bind():
        files={name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in ['report.json','predictions-before-label-scoring.json','aws-cleanup.json']}
        (folder/'verified-results.json').write_text(json.dumps({'files':files,'source_archive_sha256':'archive-a'}))
    bind()
    assert followup.verified_final_study()==report
    cleanup['root_volume_deleted']=False
    (folder/'aws-cleanup.json').write_text(json.dumps(cleanup));bind()
    assert followup.verified_final_study() is None
    cleanup.update(root_volume_deleted=True,final_export_sha256='different-archive')
    (folder/'aws-cleanup.json').write_text(json.dumps(cleanup));bind()
    assert followup.verified_final_study() is None
