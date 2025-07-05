import importlib.resources
import os
import sys
from dataclasses import replace

import yaml
from metakernel import ProcessMetaKernel, pexpect

from .magics import MitSchemeMagic
from .repl import PROMPT_RE, KernelConfig, MitSchemeWrapper


class MitSchemeKernel(ProcessMetaKernel):
    implementation = "MIT-Scheme Kernel"
    implementation_version = "0.1"
    language = "mit-scheme"
    language_version = "12.1"
    banner = "MIT/GNU Scheme - A MIT/GNU Scheme Jupyter kernel"
    language_info = {
        "mimetype": "text/x-scheme",
        "name": "scheme",
        "codemirror_mode": {"name": "scheme"},
        "pygments_lexer": "scheme",
    }
    kernel_json = {
        "argv": [sys.executable, "-m", "mit_scheme_kernel", "-f", "{connection_file}"],
        "display_name": "MIT/GNU Scheme",
        "language": "scheme",
        "codemirror_mode": "scheme",
        "name": "mit-scheme-kernel",
    }

    def _register_custom_magics(self):
        """Register custom magics for the kernel"""
        self.register_magics(MitSchemeMagic)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._process = None
        default_config = importlib.resources.files("mit_scheme_kernel").joinpath("config.yaml")
        with open(default_config) as f:
            params = yaml.safe_load(f)
            self.mit_scheme_config = KernelConfig(**params)

        if user_config_path := os.getenv("MIT_SCHEME_KERNEL_CONFIG"):
            with open(user_config_path) as f:
                user_config = yaml.safe_load(f)
                update = {k: v for k, v in user_config.items() if hasattr(self.mit_scheme_config, k)}
                self.mit_scheme_config = replace(self.mit_scheme_config, **update)

        self._register_custom_magics()

    def makeWrapper(self):
        """Create the wrapper for the MIT Scheme process"""
        self.mit_scheme_cmd = self.mit_scheme_config.executable

        if pexpect.which(self.mit_scheme_cmd):
            program = self.mit_scheme_cmd
        else:
            raise Exception(f"{self.mit_scheme_cmd} not found in PATH. ")

        wrapper = MitSchemeWrapper(
            program,
            PROMPT_RE,
            None,
            kernel_config=self.mit_scheme_config,
        )
        return wrapper

    def do_execute_direct(self, code, silent=True, **kwargs):
        if not self._process:
            self.mit_scheme_cmd = self.mit_scheme_config.executable
            self._process = pexpect.spawn(self.mit_scheme_cmd, encoding="utf-8")
        result = super().do_execute_direct(code, silent=True)
        return result
