import io

class CodeIO(object):
    """
    Base class for code generator output.
    Supports indentation and output line-number tracking.
    """

    def __init__(self, fn, indent='  '):
        self.out = io.StringIO()
        self.fn = fn
        self.line = 1
        self.indent_chr = indent
        self.indent_level = 0
        self.indent_string = ''

    def indent(self):
        ' Increase indentation level by one. '
        self.indent_level += 1
        self.indent_string = self.indent_chr * self.indent_level

    def unindent(self):
        ' Decrease indentation level by one. '
        self.indent_level -= 1
        self.indent_string = self.indent_chr * self.indent_level

    @property
    def indentation(self):
        ' Get a string representation of the current indentation. '
        return self.indent_string

    @property
    def contents(self):
        return self.out.getvalue()

    def write(self, text):
        ' Write text as-is to the output. Keeps track of line count. '
        self.line += text.count('\n')
        self.out.write(text)

    def write_line(self, line_text):
        ' Write line_text with leading indentation and a trailing newline. '
        self.write_indented(line_text)
        self.write('\n')

    def write_indented(self, text):
        ' Write text with leading indentation. '
        self.write(self.indentation + text)
