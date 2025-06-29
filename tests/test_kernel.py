import re
from pathlib import Path

import pytest
import yaml
from metakernel.tests.utils import get_kernel, get_log_text

from mit_scheme_kernel.kernel import MitSchemeKernel
from mit_scheme_kernel.repl import UNBALANCED_BRACKETS_ERROR

DELIVERATE_ERROR_COMMAND = "__ERROR__COMMAND__"


def _filter_outut(text: str) -> list[str] | None:
    matches = re.findall(r"\s*([\d\w\n]+)", text)
    if matches:
        values = matches[0].strip().split("\n")
        values = [v for v in values if v]
        return values
    return None


def get_mit_scheme_kernel(monkeypatch, tmp_path: str = "/tmp", config: dict[str, str] = {}, executable: str = "mit-scheme", output_value_regex: str = "^;Value:\s*(.+)$"):
    config_file = Path(tmp_path, "mit_scheme_kernel_config.yaml")
    with open(config_file, "w") as f:
        config["executable"] = executable
        config["output_value_regex"] = output_value_regex
        yaml.dump(config, f)

    monkeypatch.setenv("MIT_SCHEME_KERNEL_CONFIG", str(config_file))
    return get_kernel(MitSchemeKernel)


@pytest.mark.parametrize(
    ("command", "expected_output"),
    [
        ("(* 3 4)", "12"),
        ("(* 3 \n4)", "12"),
        ("(* 3 \n4\n)", "12"),
    ],
)
def test_single_line_statements(monkeypatch, command: str, expected_output: str):
    config = {"filter_output": True, "return_only_last_output": True}

    kernel = get_mit_scheme_kernel(monkeypatch, config=config)
    kernel.do_execute(code=command)
    result = get_log_text(kernel)
    assert expected_output in result

@pytest.mark.parametrize(
    "command",
    [
        "\n\n(* 3 4)"
        "\n\n\n(* 3 4)"
        "(* 3 4)\n\n"
    ],
)
def test_single_line_statements_strip_line(monkeypatch, command: str):
    config = {"filter_output": True, "return_only_last_output": True}

    kernel = get_mit_scheme_kernel(monkeypatch, config=config)
    kernel.do_execute(code=command)
    result = get_log_text(kernel)
    assert "12" in result


@pytest.mark.parametrize(
    "command",
    ["(* 3 \n4\n", ")", "((())"],
)
def test_unbalanced_brackets(monkeypatch, command: str):
    config = {"filter_output": True, "return_only_last_output": True}

    kernel = get_mit_scheme_kernel(monkeypatch, config=config)
    kernel.do_execute(code=command)
    result = get_log_text(kernel)
    assert UNBALANCED_BRACKETS_ERROR in result


@pytest.mark.parametrize(
    ("command", "expected_output"),
    [
        ("(* 3 4)\n(* 3 3)", ["12", "9"]),
        (
            "(define pi 3.14)\n(define square (lambda(x) (* x x)))\n(* 4 pi (square 5))",
            ["pi", "square", "314"],
        ),
    ],
)
def test_multi_line_statements_last_output_line(monkeypatch, command: str, expected_output: list[str]):
    config = {"filter_output": True, "return_only_last_output": False}

    kernel = get_mit_scheme_kernel(monkeypatch, config=config)
    kernel.do_execute(code=command)
    result = get_log_text(kernel)
    value = _filter_outut(result)
    assert value == expected_output


def test_errors(monkeypatch):
    config = {"filter_output": True, "return_only_last_output": False}

    kernel = get_mit_scheme_kernel(monkeypatch, config=config)
    kernel.do_execute(code=DELIVERATE_ERROR_COMMAND)
    result = get_log_text(kernel)
    assert "RESTART" in result


def test_behavior_on_error_multiline(monkeypatch):
    config = {
        "filter_output": False,
        "return_only_last_output": False,
    }
    command = f"(* 3 7.25)\n{DELIVERATE_ERROR_COMMAND}\n(* 3 3.1)"
    kernel = get_mit_scheme_kernel(monkeypatch, config=config)
    kernel.do_execute(code=command)
    result = get_log_text(kernel)

    assert ";Value: 21.75" in result
    assert ";Value: 9.3" in result

def test_restart_kernel(monkeypatch):
    config = {
        "auto_restart_on_error": True,
        "restart_command" : "(RESTART 1)",
    }
    command = f"(* 3 7.25)\n{DELIVERATE_ERROR_COMMAND}\n(* 3 3.1)"
    kernel = get_mit_scheme_kernel(monkeypatch, config=config)
    kernel.do_execute(code=command)
    result = get_log_text(kernel)
    assert "Abort" in result


def test_magic(monkeypatch):
    config = {"filter_output": True, "return_only_last_output": True}
    kernel = get_mit_scheme_kernel(monkeypatch, config=config, executable="mechanics", output_value_regex=r"^\#\|\s*(.+)\s*\|\#$")

    code = """%%show_expression
(define ((L-free-particle mass) local)
  (let ((v (velocity local)))
    (* 1/2 mass (dot-product v v))))

(show-expression ((L-free-particle 'm)
                  (up 't
                      (up 'x 'y 'z)
                      (up 'xdot 'ydot 'zdot))))
    """

    kernel.do_execute(code=code)

    magic = kernel.cell_magics['show_expression']
    assert "last-tex-string-generated" in magic.code
