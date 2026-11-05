from pathlib import Path
from unittest.mock import patch
import main

def test_source_mode_record_root():
    with patch.object(main.sys, "frozen", False, create=True):
        assert main.application_directory() == Path(main.__file__).resolve().parent

def test_frozen_mode_record_root():
    with patch.object(main.sys, "frozen", True, create=True), patch.object(main.sys, "executable", r"C:\\FQC\\GRG-4361.exe"):
        assert main.application_directory() == Path(r"C:\\FQC\\GRG-4361.exe").resolve().parent

def test_records_is_relative_to_application():
    assert main.ROOT == main.application_directory() / "Records"

def test_create_logs_in_selected_directory(tmp_path):
    d=tmp_path/"Records"/"run1"
    log=main.make_logger(d)
    log.info("start")
    for h in list(log.handlers):
        h.flush();h.close();log.removeHandler(h)
    assert (d/"execution.log").exists()
    assert (d/"debug.log").exists()
