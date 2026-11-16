from . import core

def execute(payload: dict | None = None) -> dict:
    return core.run(payload or core.SAMPLE)
