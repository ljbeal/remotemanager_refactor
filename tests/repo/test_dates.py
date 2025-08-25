from remoref.engine.repo import Manifest, date_format
import datetime


def test_utc():
    repo = Manifest(manifest_path="foo")

    assert repo.now() == datetime.datetime.strftime(datetime.datetime.now(datetime.timezone.utc), date_format)
