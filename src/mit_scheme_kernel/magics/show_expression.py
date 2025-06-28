import re

from IPython.display import Latex
from metakernel import Magic


class MitSchemeMagic(Magic):
    def __init__(self, kernel):
        super().__init__(kernel)
        self.boxit_pattern  = r"\\boxit\{\s*\$\$(.*?)\$\$\s*\}"

    def line_show_expression(self, *args):
        pass

    def cell_show_expression(self):
        """
        TODO: write documentation
        """
        if "show-expression" not in self.code:
            self.code = f"(show-expression {self.code})"

        self.code  += "\n(display last-tex-string-generated)"

    def _latexify(self, line):
        match = re.search(self.boxit_pattern, line)
        if match:
            line = match.group(1)

            if "\matrix" in line:
                line = re.sub(r'\\cr\s*\\cr', r' \\\\\n', line)
                line = f"\\renewcommand{{\\matrix}}[1]{{\\begin{{matrix}}#1\\end{{matrix}}}}\n{line}"
                line = f"$${line}$$"

        return line

    def post_process(self, retval):
        res = retval.output.split('\n')
        for line in res:
            if line.strip():
                if re.search(self.boxit_pattern, line):
                    line = self._latexify(line)
                    self.kernel.Display(Latex(line))
