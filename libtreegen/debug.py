import sys
from .nodes import *

# FIXME: use codeio.CodeIO to handle indentation and stuff
class DebugTree(NodeVisitor):

    def __init__(self, out=sys.stdout, indent='  '):
        self.out = out
        self.ind = indent
        self.level = 0
        self.indstr = ''

    def indent(self):
        self.level += 1
        self.indstr = self.ind * self.level
    def unindent(self):
        self.level -= 1
        self.indstr = self.ind * self.level
    @property
    def indentation(self):
        return self.indstr

    def write(self, txt):
        self.out.write(txt)
    def write_line(self, txt):
        self.write_indented(txt + '\n')
    def write_indented(self, txt):
        self.out.write(self.indentation + txt)

    def generic_visit(self, node):
        # if this runs, there's a problem :(
        self.write_line('<Unhandled>%s</Unhandled>' % node.__class__.__name__)

    def visit_BoolLiteral(self, node):
        self.write('%s' % node.value)

    def visit_IntLiteral(self, node):
        self.write('%s' % node.value)

    def visit_FloatLiteral(self, node):
        self.write('%s' % node.value)

    def visit_CharLiteral(self, node):
        self.write('%s' % node.value)

    def visit_StringLiteral(self, node):
        self.write('%s' % node.value)

    def visit_NullLiteral(self, node):
        self.write('%s' % node.value)

    def visit_ListLiteral(self, node):
        self.write('<List>')
        for item in node.value:
            item.accept(self)
        self.write('</List>')

    def visit_Call(self, node):
        self.write('<Construct/>')

    def visit_EmptyList(self, node):
        self.write_line('<EmptyList/>')

    def visit_PrimitiveType(self, node):
        self.write_line('<PrimitiveType>%s</PrimitiveType>' % node.name)

    def visit_ExternType(self, node):
        self.write_line('<ExternType name="%s">' % node.name)
        self.indent()
        for targ_type in node.target_types:
            self.write_line('<TargetType>')
            self.indent()
            targ_type.accept(self)
            self.unindent()
            self.write_line('</TargetType>')
        self.unindent()
        self.write_line('</ExternType>')

    def visit_ListElementType(self, node):
        self.write_line('<ListElementType weak="%s">' % node.is_weak)
        self.indent()
        node.type.accept(self)
        self.unindent()
        self.write_line('</ListElementType>')

    def visit_FieldType(self, node):
        self.write_line('<Type weak="%s">%s</Type>' % (
            node.is_weak, node.type.__class__.__name__))

    def visit_Field(self, node):
        self.write_line('<Field name="%s">' % node.name)
        self.indent()
        node.type.accept(self)
        if node.default:
            self.write_indented('<Default>')
            node.default.accept(self)
            self.write('</Default>\n')
        self.unindent()
        self.write_line('</Field>')

    def visit_Constructor(self, node):
        for arg in node.args:
            self.write_line('<Field>%s</Field>' % arg)

    def visit_Node(self, node):
        base = ' base="%s"' % node.base.name if node.base else ''
        self.write_line('<Node name="%s" abstract="%s"%s>' % (
            node.name, node.is_abstract, base))
        self.indent()
        self.write_line('<Fields>')
        self.indent()
        for fld in node.fields:
            fld.accept(self)
        self.unindent()
        self.write_line('</Fields>')
        self.write_line('<Construct>')
        self.indent()
        for ctr in node.ctrs:
            ctr.accept(self)
        self.unindent()
        self.write_line('</Construct>')
        self.unindent()
        self.write_line('</Node>')

    def visit_Visitor(self, node):
        self.write_line('<Visitor name="%s">' % node.name)
        self.indent()
        for opt in node.options:
            opt.accept(self)
        self.unindent()
        self.write_line('</Visitor>')

    def visit_ExternTypeDef(self, node):
        self.write_line('<Extern name="%s">' % node.name)
        self.indent()
        for opt in node.options:
            opt.accept(self)
        self.unindent()
        self.write_line('</Extern>')

    def visit_Option(self, node):
        self.write_indented('<Option name="%s">' % node.name)
        node.value.accept(self)
        self.write('</Option>\n')

    def visit_Target(self, node):
        self.write_line('<Target name="%s">' % node.name)
        self.indent()
        for opt in node.options:
            opt.accept(self)
        for ext in node.externs:
            ext.accept(self)
        self.unindent()
        self.write_line('</Target>')

    def visit_Epilog(self, node):
        self.write_line('<Epilog src="%s"/>' % node.filename)

    def visit_Prolog(self, node):
        self.write_line('<Prolog src="%s"/>' % node.filename)

    def visit_RootSpec(self, node):
        self.write_line('<Root>%s</Root>' % node.type.name)

    def visit_SpecFile(self, node):
        self.write_line('<Spec src="%s">' % node.filename)
        self.indent()
        if node.root:
            node.root.accept(self)
        for target in node.targets:
            target.accept(self)
        for visitor in node.visitors:
            visitor.accept(self)
        for treenode in node.nodes:
            treenode.accept(self)
        self.unindent()
        self.write_line('</Spec>')
