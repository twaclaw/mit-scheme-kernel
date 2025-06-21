import re
from dataclasses import dataclass

from metakernel import REPLWrapper

PROMPT_RE = re.compile(r"\d (?:\]=>|error>)")
ERROR_RE = re.compile(r"\d error>")  # Regex to match MIT Scheme error messages
CONTINUATION_PROMPT_RE = re.compile(r"")

UNBALANCED_BRACKETS_ERROR = "Unbalanced parentheses in input code."



@dataclass
class KernelConfig:
    executable: str
    auto_restart_on_error: bool
    restart_command: str
    filter_output: bool
    return_only_last_output: bool
    output_value_regex: str



class MitSchemeWrapper(REPLWrapper):
    def __init__(
        self,
        *args,
        kernel_config: KernelConfig,
        **kwargs,
    ):
        # Remove 'continuation_prompt_regex' from kwargs if present
        kwargs.pop("continuation_prompt_regex", None)
        super(MitSchemeWrapper, self).__init__(*args, **kwargs)

        self.child.delaybeforesend = 0.0
        self.bracket_balance = 0

        self.restart = kernel_config.auto_restart_on_error
        self.restart_command = kernel_config.restart_command
        self.filter_output = kernel_config.filter_output
        self.return_only_last_output = kernel_config.return_only_last_output
        self.output_value_regex = re.compile(kernel_config.output_value_regex)

    def _check_bracket_balance(self, line):
        for char in line:
            if char == "(":
                self.bracket_balance += 1
            elif char == ")":
                self.bracket_balance -= 1
        return self.bracket_balance == 0

    def _restart_bracket_balance(self):
        self.bracket_balance = 0

    def _filter_value(self, s: str) -> str:
        match = re.search(self.output_value_regex, s)
        return match.group(1) if match else s

    def run_command(self, code, timeout=-1, stream_handler=None, stdin_handler=None):
        lines = code.splitlines()
        res = []
        error: bool = False
        self._restart_bracket_balance()
        for line in lines:
            if not line.strip():
                continue

            self.sendline(line)
            if self._check_bracket_balance(line):
                self._expect_prompt(timeout=timeout)
                res.append(self.child.before)
            else:
                self.child.expect(CONTINUATION_PROMPT_RE, timeout=timeout)

            if re.match(ERROR_RE, self.child.after):
                error = True

        if error:
            if self.restart:
                self._restart_bracket_balance()
                self.sendline(self.restart_command)
                self._expect_prompt(timeout=timeout)
                res.append(self.child.before)
                res.append(f"Automatically restarted REPL with command: {self.restart_command}")


        if self.bracket_balance != 0:
            res = [s.strip() for s in res if s.strip() and s is not None]
            error_msg = UNBALANCED_BRACKETS_ERROR
            if len(res) > 0:
                error_msg += f"\nIntermediate output: {'\n'.join(res)}"
            raise ValueError(error_msg)

        if self.return_only_last_output:
            res = res[-1:]

        res = [s.strip() for s in res if s.strip() and s is not None]

        return "\n".join([self._filter_value(s) for s in res]) if self.filter_output else "\n".join(res)
