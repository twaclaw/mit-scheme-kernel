import re
from enum import StrEnum
from typing import Any

from metakernel import REPLWrapper

PROMPT_RE = re.compile(r"\d (?:\]=>|error>)")
ERROR_RE = re.compile(r"\d error>")  # Regex to match MIT Scheme error messages
CONTINUATION_PROMPT_RE = re.compile(r"")
VALUE_RE = r"^;Value:\s*([^\s]+)"


class OnError(StrEnum):
    IGNORE = "ignore"
    RAISE = "raise"
    RESTART_AND_RAISE = "restart_and_raise"


class MitSchemeWrapper(REPLWrapper):
    def __init__(
        self,
        *args,
        kernel_config: dict[str, Any] = {},
        **kwargs,
    ):
        # Remove 'continuation_prompt_regex' from kwargs if present
        kwargs.pop("continuation_prompt_regex", None)
        super(MitSchemeWrapper, self).__init__(*args, **kwargs)

        self.child.delaybeforesend = 0.0
        self.bracket_balance = 0
        self.behavior_on_error_prompt = OnError(kernel_config.get(
            "behavior_on_error_prompt", OnError.RESTART_AND_RAISE
        ))
        self.restart_command = kernel_config.get("restart_command", "(RESTART 1)")
        self.filter_output = kernel_config.get("filter_output", True)
        self.return_only_last_output = kernel_config.get(
            "return_only_last_output", False
        )

    def _check_bracket_balance(self, line):
        for char in line:
            if char == "(":
                self.bracket_balance += 1
            elif char == ")":
                self.bracket_balance -= 1
        return self.bracket_balance == 0

    def _restart_bracket_balance(self):
        self.bracket_balance = 0

    @staticmethod
    def _filter_value(s: str) -> str | None:
        match = re.search(VALUE_RE, s)
        return match.group(1) if match else None

    def run_command(self, code, timeout=-1, stream_handler=None, stdin_handler=None):
        lines = code.splitlines()
        res = []

        for line in lines:
            self.sendline(line)
            if self._check_bracket_balance(line):
                self._expect_prompt(timeout=timeout)
                res.append(self.child.before)
            else:
                self.child.expect(CONTINUATION_PROMPT_RE, timeout=timeout)

            if re.match(ERROR_RE, self.child.after):
                if self.behavior_on_error_prompt == OnError.RESTART_AND_RAISE:
                    self._restart_bracket_balance()
                    self.sendline(self.restart_command)
                    self._expect_prompt(timeout=timeout)
                    res.append(self.child.before)
                    raise ValueError(
                        f"Error detected in input line {line}. Restart command '{self.restart_command}' executed. "
                    )
                elif self.behavior_on_error_prompt == OnError.RAISE:
                    raise ValueError(
                        f"Error detected in input line {line}. You have to manually execute one of the RESTART commands."
                    )
                break

        if self.bracket_balance != 0:
            raise ValueError("Unbalanced parentheses in input code.")

        if self.return_only_last_output:
            res = res[-1:]

        res = [s.strip() for s in res if s.strip()]

        return (
            "\n".join([self._filter_value(s) for s in res])
            if self.filter_output
            else "\n".join(res)
        )
