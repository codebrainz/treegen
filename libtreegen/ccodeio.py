from . import codeio
from . import nodes

class CCodeIO(codeio.CodeIO):

    def __init__(self, fn, indent='  ', cpp_indent=' '):
        super().__init__(fn, indent)
        self.cpp_indent_chr = cpp_indent
        self.cpp_indent_level = 0
        self.cpp_indent_string = ''

    def cpp_indent(self):
        self.cpp_indent_level += 1
        self.cpp_indent_string = self.cpp_indent_chr * self.cpp_indent_level

    def cpp_unindent(self):
        self.cpp_indent_level -= 1
        self.cpp_indent_string = self.cpp_indent_chr * self.cpp_indent_level

    @property
    def cpp_indentation(self):
        return self.cpp_indent_string

    @property
    def reset_location(self):
        return nodes.Location(self.fn, self.line, 0)

    def cpp_write_line(self, line_text):
        self.cpp_write_indented(line_text)
        self.write('\n')

    def cpp_write_indented(self, text):
        if self.cpp_indent_level > 0:
            self.write('#' + self.cpp_indentation + text)
        else:
            self.write('#' + text)
