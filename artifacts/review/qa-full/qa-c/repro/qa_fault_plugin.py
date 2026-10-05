"""Keep the upstream fault suite on the assigned QA API port."""
def pytest_collection_modifyitems(items):
    for item in items:
        if item.module.__name__.endswith('scenarios'):
            item.module.free_port = lambda: 11491
