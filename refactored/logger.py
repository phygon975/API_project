import builtins
import config

_verbosity_level = getattr(config, 'DEFAULT_VERBOSITY', 1)

def set_verbosity(level: int) -> None:
    global _verbosity_level
    try:
        lvl = int(level)
    except Exception:
        lvl = 1
    _verbosity_level = max(0, min(3, lvl))

def get_verbosity() -> int:
    return _verbosity_level

def _should_log(level: int) -> bool:
    if not getattr(config, 'ENABLE_DEBUG_OUTPUT', True):
        return False
    return level <= _verbosity_level

def log(level: int, *args, **kwargs) -> None:
    if _should_log(level):
        builtins.print(*args, **kwargs)

def info(*args, **kwargs) -> None:
    log(1, *args, **kwargs)

def debug(*args, **kwargs) -> None:
    log(2, *args, **kwargs)

def trace(*args, **kwargs) -> None:
    log(3, *args, **kwargs)



