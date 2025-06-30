import re

from IPython.display import Latex
from metakernel import Magic


class MitSchemeMagic(Magic):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.boxit_pattern = r"\\boxit\{\s*\$\$(.*?)\$\$\s*\}"

    def line_show_expression(self, *args):
        pass

    def cell_show_expression(self):
        """
        %%show_expression -- renders the output of the cell into LaTeX

        Requires/complements the `show-expression` function defined in the Scmutils library.

        Example usage:

        %%show_expression
        (define ((L-free-particle mass) local)
            (let ((v (velocity local)))
            (* 1/2 mass (dot-product v v))))

        (show-expression ((L-free-particle 'm)
                  (up 't
                      (up 'x 'y 'z)
                      (up 'xdot 'ydot 'zdot))))

        """
        if "show-expression" not in self.code:
            self.code = f"(show-expression {self.code})"

        self.code += "\n(display last-tex-string-generated)"

    def _expand_matrix(self, text: str):
        def find_matching_brace(text, start_pos):
            if start_pos >= len(text) or text[start_pos] != "{":
                return -1

            brace_count = 0
            pos = start_pos

            while pos < len(text):
                if text[pos] == "{":
                    brace_count += 1
                elif text[pos] == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        return pos
                pos += 1
            return -1  # No matching brace found

        result = []
        i = 0

        while i < len(text):
            if text[i : i + 8] == "\\matrix{":
                opening_brace_pos = i + 7  # Position of the '{'
                closing_brace_pos = find_matching_brace(text, opening_brace_pos)

                if closing_brace_pos != -1:
                    content = text[opening_brace_pos + 1 : closing_brace_pos]
                    replacement = f"\\begin{{matrix}}\n{content}\n\\end{{matrix}}"
                    result.append(replacement)
                    i = closing_brace_pos + 1
                else:
                    result.append(text[i])
                    i += 1
            else:
                result.append(text[i])
                i += 1
        return "".join(result)

    def _latexify(self, line):
        match = re.search(self.boxit_pattern, line)
        if match:
            line = match.group(1)

            if "\matrix" in line:
                line = self._expand_matrix(line)
                line = re.sub(r"\\cr\s*\\cr", r" \\\\\n", line)
                # TODO: handle column separators
                self.matrix_command_defined = True

            line = f"$${line}$$"

        return line

    def post_process(self, retval):
        res = retval.output.split("\n")
        for line in res:
            if line.strip():
                if re.search(self.boxit_pattern, line):
                    line = self._latexify(line)
                    self.kernel.Display(Latex(line))


def register_magics(kernel):
    kernel.register_magics(MitSchemeMagic)
