"""
This module contains the tree nodes that represent the C++ code to be output.
"""

from . import ccodeio
import inspect
import os
import re
import sys

class CCodeNode(object):
    """
    The base CCodeNode that all other nodes subclass from. It adds all of
    the `_fields` from each class in the hierarchy as attributes on the
    instance.
    """
    _fields = [ ("parent", None) ]
    _all_fields = None

    def __init__(self, **ka):
        fld_list = self.__class__._all_fields
        if fld_list is None:
            fld_list = self.__class__._find_fields()
        fld_set = set()
        for field, default in fld_list:
            fld_set.add(field)
            # since lists are mutable and the fields are evaluated at class
            # creation time, prevent using the same list for each instance
            if isinstance(default, list):
                default = default[:]
            if field in ka and ka[field] is not None:
                setattr(self, field, ka[field])
            else:
                setattr(self, field, default)

    @classmethod
    def _find_fields(self_class):
        self_class._all_fields = []
        field_set = {}
        for klass in inspect.getmro(self_class):
            class_fields = getattr(klass, "_fields", [])
            fields = []
            for field, default in class_fields:
                if field not in field_set:
                    fields.append((field, default))
                    field_set[field] = klass.__name__
            self_class._all_fields.extend(fields)
        return self_class._all_fields

    def codegen(self, out):
        pass

class BlankLine(CCodeNode):
    def codegen(self, out):
        out.write_line('')

class CppMacro(CCodeNode):
    """
    All the C-Preprocessor macros subclass this. The `first` field is the
    part that comes after the preprocessor directive and `second` is the
    part that comes after that. For example, `#define <first> <second>`.
    """
    _fields = [
        ("first", None),
        ("second", None)
    ]
    def codegen(self, out, name='define', indents=False, unindents=False):
        if unindents: out.cpp_unindent()
        out.cpp_write_indented(name)
        if self.first: out.write(' ' + self.first)
        if self.second: out.write(' ' + self.second)
        out.write('\n')
        if indents: out.cpp_indent()

class CppDefine(CppMacro):
    def codegen(self, out):
        super().codegen(out, name='define')

class CppInclude(CppMacro):
    def codegen(self, out):
        super().codegen(out, name='include')

class CppIfdef(CppMacro):
    def codegen(self, out):
        super().codegen(out, name='ifdef', indents=True)

class CppIfndef(CppMacro):
    def codegen(self, out):
        super().codegen(out, name='ifndef', indents=True)

class CppIf(CppMacro):
    def codegen(self, out, name='if'):
        super().codegen(out, name='if', indents=True)

class CppElif(CppMacro):
    def codegen(self, out):
        super().codegen(out, name='elif', indents=True)

class CppElse(CppMacro):
    def codegen(self, out):
        super().codegen(out, name='else', indents=True)

class CppEndif(CppMacro):
    def codegen(self, out):
        super().codegen(out, name='endif', unindents=True)

class CppLine(CppMacro):
    def codegen(self, out):
        super().codegen(out, name='line')

class CppLineReset(CppMacro):
    def codegen(self, out):
        loc = out.reset_location
        CppLine(first='%d' % (out.reset_location.line + 1),
                second='"%s"' % out.reset_location.file
        ).codegen(out)

class TranslationUnit(CCodeNode):
    _fields = [
        ("filename", ""),
        ("includes", []),
        ("is_header", False),
        ("stmts", []),
    ]
    def codegen(self, out):
        def fn_to_ident(fn):
            return re.sub(r'[^a-zA-Z_0-9]+', '_', os.path.basename(fn))
        out.write_line('// This file is auto-generated, do not edit.')
        fn_ident = fn_to_ident(self.filename).upper()
        if self.is_header:
            CppIfndef(first=fn_ident).codegen(out)
            CppDefine(first=fn_ident, second='1').codegen(out)
        out.write('\n')
        if self.includes:
            for inc in self.includes:
                inc.codegen(out)
            out.write('\n')
        for stmt in self.stmts:
            stmt.codegen(out)
        # ...
        if self.is_header:
            out.write('\n')
            CppEndif().codegen(out)

class Namespace(CCodeNode):
    _fields = [
        ("name", ""),
        ("trailing_comment", False),
        ("stmts", []),
    ]
    def codegen(self, out):
        out.write_line('namespace ' + self.name + ' {')
        out.indent()
        for stmt in self.stmts:
            stmt.codegen(out)
        out.unindent()
        out.write_line('}')

class Include(CCodeNode):
    _fields = [ ("file", ""), ("angles", False) ]
    def codegen(self, out):
        CppInclude(
            first='<%s>' % self.file if self.angles else '"%s"' % self.file
        ).codegen(out)

class TypeDef(CCodeNode):
    _fields = [ ("src", ""), ("dst", ""), ("use_typename", False) ]
    def codegen(self, out):
        typename = 'typename ' if self.use_typename else ''
        out.write_line('typedef ' + typename + self.src + ' ' + self.dst + ';')

class ClassForwardDecl(CCodeNode):
    _fields = [ ("name", ""), ("is_struct", False) ]
    def codegen(self, out):
        kind = 'struct' if self.is_struct else 'class'
        out.write_line(kind + ' ' + self.name + ';')

class Parameter(CCodeNode):
    _fields = [
        ("type", None),
        ("name", ""),
        ("default", None),
        ("is_ellipsis", False),
    ]
    def codegen(self, out):
        if self.is_ellipsis:
            out.write('...')
        else:
            self.type.codegen(out)
            out.write(' ' + self.name)
            if self.default:
                out.write('=')
                self.default.codegen(out)

class InitializerArgument(CCodeNode):
    _fields = [ ("name", ""), ("use_move", False) ]
    def codegen(self, out):
        if self.use_move:
            out.write('std::move(' + self.name + ')')
        else:
            out.write(self.name)

class Initializer(CCodeNode):
    _fields = [ ("target", ""), ("arg", ""), ("curly", False) ]
    def codegen(self, out):
        out.write(self.target)
        if self.curly: out.write('{')
        else: out.write('(')
        if self.arg:
            self.arg.codegen(out)
        if self.curly: out.write('}')
        else: out.write(')')

class ConstructorChainUp(CCodeNode):
    _fields = [ ("target", ""), ("args", []), ("curly", False) ]
    def codegen(self, out):
        out.write(self.target)
        if self.curly: out.write('{')
        else: out.write('(')
        if self.args:
            last = self.args[-1]
            for arg in self.args:
                arg.codegen(out)
                if arg is not last:
                    out.write(', ')
        if self.curly: out.write('}')
        else: out.write(')')

class AccessLevel(CCodeNode):
    _fields = [ ("name", "") ]
    def codegen(self, out, current_access=None):
        #if self.name != current_access:
        #   out.unindent()
        #   out.write_line(self.name + ':')
        #   out.unindent()
        pass

class ClassMember(CCodeNode):
    _fields = [
        ("access", AccessLevel(name="private"))
    ]

class Field(ClassMember):
    _fields = [
        ("type", None),
        ("name", ""),
        ("initializer", None)
    ]
    def codegen(self, out, current_access=None):
        self.access.codegen(out, current_access)
        out.write_indented('')
        self.type.codegen(out)
        out.write(' ' + self.name)
        if self.initializer:
            out.write('= ')
            self.initializer.codegen(out)
        out.write(';\n')

class MethodDecl(ClassMember):
    _fields = [
        ("type", None),
        ("name", ""),
        ("params", []),
        ("is_const", False),
    ]
    def codegen(self, out, current_access=None):
        self.access.codegen(out, current_access)
        out.write_indented('')
        self.type.codegen(out)
        out.write(' ' + self.name + '(')
        if self.params:
            last = self.params[-1]
            for param in self.params:
                param.codegen(out)
                if param is not last:
                    out.write(', ')
        if self.is_const:
            out.write(') const;\n')
        else:
            out.write(');\n')

class Method(ClassMember):
    _fields = [
        ("type", None),
        ("name", ""),
        ("params", []),
        ("stmts", []),
        ("is_const", False),
        ("cls", None) ]
    def codegen(self, out, current_access=None):
        self.access.codegen(out, current_access)
        out.write_indented('')
        self.type.codegen(out)
        out.write(' ' + self.cls + '::' + self.name + '(')
        if self.params:
            last = self.params[-1]
            for param in self.params:
                param.codegen(out)
                if param is not last:
                    out.write(', ')
        if self.is_const:
            out.write(') const {')
        else:
            out.write(') {')
        if len(self.stmts) == 0:
            out.write('}\n')
        else:
            out.write('\n')
            out.indent()
            for stmt in self.stmts:
                stmt.codegen(out)
            out.unindent()
            out.write_line('}')

class InlineMethod(ClassMember):
    _fields = [
        ("type", None),
        ("name", ""),
        ("params", []),
        ("stmts", []),
        ("is_const", False)
    ]
    def codegen(self, out, current_access=None):
        self.access.codegen(out, current_access)
        out.write_indented('')
        self.type.codegen(out)
        out.write(' ' + self.name + '(')
        if self.params:
            last = self.params[-1]
            for param in self.params:
                param.codegen(out)
                if param is not last:
                    out.write(', ')
        if self.is_const:
            out.write(') const {')
        else:
            out.write(') {')
        if len(self.stmts) == 0:
            out.write('}\n')
        else:
            out.write('\n')
            out.indent()
            for stmt in self.stmts:
                stmt.codegen(out)
            out.unindent()
            out.write_line('}')

class Constructor(ClassMember):
    _fields = [
        ("name", ""),
        ("params", []),
        ("initializers", []),
        ("stmts", [])
    ]
    def codegen(self, out, current_access=None):
        self.access.codegen(out, current_access)
        out.write_indented('')
        out.write(self.name + '(')
        if self.params:
            last = self.params[-1]
            for param in self.params:
                param.codegen(out)
                if param is not last:
                    out.write(', ')
        out.write(')')
        out.indent()
        out.indent()
        if len(self.initializers) > 0:
            out.write('\n')
            out.write_indented(': ')
            if self.initializers:
                first = self.initializers[0]
                last = self.initializers[-1]
                for init in self.initializers:
                    if init is not first:
                        out.write_indented('  ')
                    init.codegen(out)
                    if init is not last:
                        out.write(', \n')
        out.unindent()
        out.write(' {')
        if len(self.stmts) > 0:
            out.write('\n')
            for stmt in self.stmts:
                stmt.codegen(out)
            out.write_line('}')
        else:
            out.write('}\n')
        out.unindent()

class Destructor(ClassMember):
    _fields = [
        ("name", ""),
        ("stmts", []),
        ("is_virtual", False),
        ("is_inline", False) ]
    def codegen(self, out, current_access=None):
        self.access.codegen(out, current_access)
        out.write_indented('')
        if self.is_virtual:
            out.write('virtual ')
        if self.is_inline:
            out.write('inline ')
        out.write(self.name +'::~' + self.name + '() {')
        if len(self.stmts) > 0:
            out.write('\n')
            out.indent()
            for stmt in self.stmts:
                stmt.codegen(out)
            out.unindent()
            out.write_line('}')
        else:
            out.write('}\n')

class DestructorDecl(ClassMember):
    _fields = [ ("name", ""), ("is_virtual", False) ]
    def codegen(self, out, current_access=None):
        self.access.codegen(out, current_access)
        out.write_indented('')
        if self.is_virtual:
            out.write('virtual ')
        out.write('~' + self.name + '();\n')

class DeleteStmt(CCodeNode):
    _fields = [ ("target", ""), ("is_array", False) ]
    def codegen(self, out):
        if self.is_array:
            out.write_line('delete[] ' + self.target + ';')
        else:
            out.write_line('delete ' + self.target + ';')

class Stmt(CCodeNode):
    _fields = [ ("code", "") ]
    def codegen(self, out):
        if self.code:
            out.write_indented(self.code)
            if not self.code.endswith(';') and len(self.code) > 0:
                out.write(';')
            if len(self.code) > 0:
                out.write('\n')

class DataType(CCodeNode):
    _fields = [
        ("name", ""),
        ("namespace", "")
    ]
    def codegen(self, out):
        if self.namespace:
            if self.namespace == '::':
                out.write('::')
            elif not self.namespace.endswith('::'):
                out.write(self.namespace + '::')
            else:
                out.write(self.namespace)
        out.write(self.name)

class TemplateArgument(CCodeNode):
    _fields = [
        ("typename", "typename"),
        ("name", ""),
        ("initializer", ""),
        ("is_variadic", False)
    ]
    def codegen(self, out):
        out.write(self.typename)
        if self.is_variadic:
            out.write('...')
        out.write(' ' + self.name)
        if self.initializer:
            out.write(' = ' + self.initializer)

class TemplatedType(DataType):
    _fields = [ ("template_args", []) ]
    def codegen(self, out):
        super().codegen(out) # generate the data-type part
        out.write('<')
        if self.template_args:
            last = self.template_args[-1]
            for arg in self.template_args:
                arg.codegen(out)
                if arg == last:
                    out.write(', ')
        out.write('>')

class ClassDecl(CCodeNode):
    _fields = [
        ("name", ""),
        ("bases", []),
        ("fields", []),
        ("methods", []),
        ("constructors", []),
        ("destructor", None),
        ("is_struct", True),
        ("extra_stmts", []),
    ]
    def codegen(self, out):
        if self.is_struct:
            out.write_indented('struct ' + self.name)
        else:
            out.write_indented('class ' + self.name)
        if len(self.bases) > 0:
            out.write(' : ')
            last = self.bases[-1]
            for base in self.bases:
                if base is not last:
                    out.write('public ' + base.name + ', ')
                else:
                    out.write('public ' + base.name)
        out.write(' {\n')
        out.indent()
        for field in self.fields:
            field.codegen(out)
        for ctor in self.constructors:
            ctor.codegen(out)
        if self.destructor:
            self.destructor.codegen(out)
        for method in self.methods:
            method.codegen(out)
        for extra in self.extra_stmts:
            extra.codegen(out)
        out.unindent()
        out.write_line('};')

class CCodeVisitor(object):
    """
    Simple CCodeNode base visitor class.
    """
    def generic_visit(self, node):
        pass
    def visit(self, node):
        for cls in inspect.getmro(node.__class__):
            func_name = 'visit_' + cls.__name__
            if hasattr(self, func_name):
                func = getattr(self, func_name)
                return func(node)
        return self.generic_visit(node)
