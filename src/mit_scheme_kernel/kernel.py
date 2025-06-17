import importlib.resources
import os
import sys

import yaml
from metakernel import ProcessMetaKernel, pexpect

from mit_scheme_kernel.repl import PROMPT_RE, MitSchemeWrapper


class MitSchemeKernel(ProcessMetaKernel):
    implementation = "MIT-Scheme Kernel"
    implementation_version = "0.1"
    language = "mit-scheme"
    language_version = "12.1"
    banner = (
        "MIT Scheme Kernel - A kernel for running MIT-Scheme code in Jupyter notebooks."
    )
    language_info = {
        "mimetype": "text/x-scheme",
        "name": "scheme",
        "codemirror_mode": {"name": "scheme"},
        "pygments_lexer": "scheme",
    }
    kernel_json = {
        "argv": [sys.executable, "-m", "mit_scheme_kernel", "-f", "{connection_file}"],
        "display_name": "MIT Scheme",
        "language": "scheme",
        "codemirror_mode": "scheme",
        "name": "mit_scheme_kernel",
    }

    def __init__(self, *args, **kwargs):
        super(MitSchemeKernel, self).__init__(*args, **kwargs)
        self._process = None
        default_config = importlib.resources.files("mit_scheme_kernel").joinpath(
            "config.yaml"
        )
        with open(os.getenv("MIT_SCHEME_KERNEL_CONFIG", default_config)) as f:
            self.mit_scheme_config = yaml.safe_load(f)

    def do_execute(self, code, silent=True, **kwargs):
        if not self._process:
            self.mit_scheme_cmd = self.mit_scheme_config.get("executable", "mit-scheme")
            self._process = pexpect.spawn(self.mit_scheme_cmd, encoding="utf-8")
        self._process.sendline(code)
        super().do_execute_direct(code, silent=False)
        return {
            "status": "ok",
            "execution_count": self.execution_count,
        }

    def makeWrapper(self):
        """ """
        if pexpect.which(self.mit_scheme_cmd):
            program = self.mit_scheme_cmd
        else:
            raise Exception(f"{self.mit_scheme_cmd} not found in PATH. ")

        # We don't want help commands getting stuck,
        # use a non interactive PAGER

        wrapper = MitSchemeWrapper(
            program,
            PROMPT_RE,
            None,
            kernel_config=self.mit_scheme_config,
        )
        return wrapper


# Instantiate for testing
# if __name__ == "__main__":
#     kernel = MitSchemeKernel()
#     # Test if mit-scheme process is started
#     result = kernel.do_execute("(* 3 4)", silent=False)
#     if kernel._process and kernel._process.isalive():
#         print("mit-scheme process started successfully.")
#         # Execute additional Scheme code
#         commands = [
#             """(define pi 3.14159)
# (define square (lambda(x) (* x x)
# ))
# (* 4 pi (square 5))
# dfadfa
#         """,

#         ]
#         for command in commands:
#             result = kernel.do_execute(command, silent=False)
#             print(result)
#     else:
#         print("Failed to start mit-scheme process.")
