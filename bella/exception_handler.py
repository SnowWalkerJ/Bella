import sys
import functools
import logging


def handle_exceptions(logger=None, ignore=True):
    if logger is None:
        logger = logging.getLogger("exception_handler")

    def decorater(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                _, exception, trace = sys.exc_info()
                trace = trace.tb_next
                filename = trace.tb_frame.f_code.co_filename
                lineno = trace.tb_lineno
                funcname = fn.__name__
                logger.error(f"{filename}({funcname}) {exception} on line {lineno}")
                if not ignore:
                    raise
        return wrapper
    return decorater
