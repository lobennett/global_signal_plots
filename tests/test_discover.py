from global_signal_plots.discover import parse_bold_meta

def test_parse_bold_meta_generic_subject():
    got = parse_bold_meta("sub-s03_ses-01_task-stroop_run-1_echo-2_bold.nii.gz")
    assert got == {"subject": "s03", "session": "01", "task": "stroop",
                   "run": "1", "echo": "2"}

def test_parse_bold_meta_non_study_subject_label():
    # generic: subject label is not restricted to s<digits>
    got = parse_bold_meta("sub-CONTROL07_ses-3_task-rest_run-2_bold.nii.gz")
    assert got["subject"] == "CONTROL07" and got["session"] == "3"
    assert got["run"] == "2" and got["echo"] is None
