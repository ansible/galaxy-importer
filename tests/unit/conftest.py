def pytest_configure(config):
    config.addinivalue_line("markers", "sha256: mark used for testing file checksums")
