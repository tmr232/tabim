from pathlib import Path

import approvaltests
import approvaltests.pytest.namer
import pytest


def get_sample(*path):
    return Path(__file__).parent / "samples" / Path(*path)


def pytest_addoption(parser):
    parser.addoption(
        "--approvaltests-subdirectory",
        action="store",
        dest="approvaltests_subdirectory",
    )


@pytest.fixture
def verify(request):
    namer = approvaltests.pytest.namer.PyTestNamer(request=request)

    def _verify_with_namer(*args, **kwargs):
        kwargs["namer"] = namer
        return approvaltests.verify_with_namer(*args, **kwargs)

    return _verify_with_namer
