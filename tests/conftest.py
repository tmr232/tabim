from pathlib import Path


def get_sample(*path):
    return Path(__file__).parent / "samples" / Path(*path)


def pytest_addoption(parser):
    parser.addoption(
        "--approvaltests-subdirectory",
        action="store",
        dest="approvaltests_subdirectory",
    )
