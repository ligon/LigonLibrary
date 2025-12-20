def pytest_addoption(parser):
    parser.addoption(
        "--show-tables",
        action="store_true",
        default=False,
        help="Print org tables generated in df_to_orgtbl tests.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "show_tables: prints generated org tables when --show-tables is passed",
    )


import pytest


@pytest.fixture
def show_tables(request):
    return request.config.getoption("--show-tables")
