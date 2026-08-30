"""Kernel test helpers.

These used to come from `metakernel.tests.utils`. metakernel 1.0.0 moved its
tests to a top-level `tests/` directory that ships only in the sdist, so the
module is not importable from an installed wheel any more. The two helpers the
suite needs are small, so they live here instead.
"""

import logging
import weakref
from io import StringIO
from logging import Logger, StreamHandler

import zmq
from jupyter_client import session
from metakernel import MetaKernel


def get_log() -> Logger:
    log = logging.getLogger("test")
    log.setLevel(logging.DEBUG)

    for hdlr in log.handlers:
        log.removeHandler(hdlr)

    hdlr = StreamHandler(StringIO())
    hdlr.setLevel(logging.DEBUG)
    log.addHandler(hdlr)

    return log


def get_kernel(kernel_class: type[MetaKernel] = MetaKernel) -> MetaKernel:
    context = zmq.Context.instance()
    iopub_socket = context.socket(zmq.PUB)

    kernel = kernel_class(session=session.Session(), iopub_socket=iopub_socket, log=get_log())
    weakref.finalize(kernel, iopub_socket.close)
    return kernel


def get_log_text(obj) -> str:
    """Get the log text from a kernel or a log object."""
    log = obj.log if isinstance(obj, MetaKernel) else obj
    handler = log.handlers[0]
    assert isinstance(handler, StreamHandler)
    return handler.stream.getvalue()
