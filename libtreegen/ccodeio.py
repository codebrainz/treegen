import io
import textwrap
from . import nodes

class CCodeIO(object):

    def __init__(self, fn, indent='  ', cpp_indent=' '):
        super().__init__()
        self.out = io.StringIO()
        self.fn = fn
        self.line = 1
        self.indent_chr = indent
        self.indent_level = 0
        self.indent_string = ''
        self.cpp_indent_chr = cpp_indent
        self.cpp_indent_level = 0
        self.cpp_indent_string = ''

    def indent(self):
        ' Increase indentation level by one. '
        self.indent_level += 1
        self.indent_string = self.indent_chr * self.indent_level

    def cpp_indent(self):
        self.cpp_indent_level += 1
        self.cpp_indent_string = self.cpp_indent_chr * self.cpp_indent_level

    def cpp_unindent(self):
        self.cpp_indent_level -= 1
        self.cpp_indent_string = self.cpp_indent_chr * self.cpp_indent_level

    def unindent(self):
        ' Decrease indentation level by one. '
        self.indent_level -= 1
        self.indent_string = self.indent_chr * self.indent_level

    @property
    def indentation(self):
        ' Get a string representation of the current indentation. '
        return self.indent_string

    @property
    def cpp_indentation(self):
        return self.cpp_indent_string

    @property
    def reset_location(self):
        return nodes.Location(self.fn, self.line, 0)

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

    def cpp_write_line(self, line_text):
        self.cpp_write_indented(line_text)
        self.write('\n')

    def write_indented(self, text):
        ' Write text with leading indentation. '
        self.write(self.indentation + text)

    def cpp_write_indented(self, text):
        if self.cpp_indent_level > 0:
            self.write('#' + self.cpp_indentation + text)
        else:
            self.write('#' + text)

    # TODO: move this to a Comment node
    def write_comment(self, text, wrap=0, force_single_line_comment=False):
        ' Pretty-print a comment. '
        if wrap > 0:
            text = textwrap.wrap(text, width)
        lines = text.split('\n')
        num_lines = len(lines)
        if num_lines > 1: # multi-line comment
            if not force_single_line_comment:
                first_pfx = '/* '
                rest_pfx = ' * '
            else:
                first_pfx = '// '
                rest_pfx = '// '
            for num, line in enumerate(lines):
                if num == 0:
                    self.write_indented(first_pfx + line)
                else:
                    self.write_indented(rest_pfx + line)
                if num == (num_lines - 1):
                    self.write(' */\n')
                else:
                    self.write('\n')
        elif num_lines == 1: # single-line comment
            self.write_line('// ' + lines[0])
