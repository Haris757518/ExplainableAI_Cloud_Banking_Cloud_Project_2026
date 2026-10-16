"""Keep all test fixture records out of the observed-results database."""
import os
from pathlib import Path
import tempfile

_test_storage = tempfile.TemporaryDirectory(prefix='xai_pytest_')
os.environ['OBSERVED_DATABASE_URL'] = 'sqlite:///' + str(Path(_test_storage.name)/'isolated_tests.db').replace('\\','/')


def pytest_sessionfinish(session, exitstatus):
    from database.db import engine
    engine.dispose()
    _test_storage.cleanup()
