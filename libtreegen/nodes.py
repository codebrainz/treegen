"""
This module contains the Abstract Syntax Tree nodes built from parser.
"""

class BaseNode(object):
	parent = None
	children = []
	def __init__(self, parent=None, children=None):
		self.parent = parent
		self.children = [] if children is None else children
	def accept(self, visitor):
		visitor.visit(self)

class Literal(BaseNode):
	def __init__(self, value):
		self.value = value

class Call(BaseNode):
	def __init__(self, name):
		self.name = name

class EmptyList(BaseNode):
	pass

# Temp node, replaced with other type after parsing
class UnresolvedType(BaseNode):
	def __init__(self, name, is_weak=False):
		self.name = name

class PrimitiveType(BaseNode):
	def __init__(self, name):
		self.name = name

class ExternType(BaseNode):
	def __init__(self, name, target_types=None):
		self.name = name
		self.target_types = [] if target_types is None else target_types

class ListElementType(BaseNode):
	def __init__(self, type, is_weak=False):
		self.type = type
		self.is_weak = is_weak

class ListType(BaseNode):
	def __init__(self, elem_type):
		self.elem_type = elem_type

class Option(BaseNode):
	def __init__(self, name, value):
		self.name = name
		self.value = value

class ExternTypeDef(BaseNode):
	def __init__(self, name, options=None):
		self.name = name
		self.options = [] if options is None else options
	def get_option(self, name, default=None):
		for opt in self.options:
			if opt.name == name:
				return opt.value
		return default

class Target(BaseNode):
	def __init__(self, name, options=None, externs=None):
		self.name = name
		self.options = [] if options is None else options
		self.externs = [] if externs is None else externs
	def get_option(self, name, default=None):
		for opt in self.options:
			if opt.name == name:
				return opt.value
		return default

class Visitor(BaseNode):
	def __init__(self, name, options=None):
		self.name = name
		self.options = [] if options is None else options
	def get_option(self, name, default=None):
		for opt in self.options:
			if opt.name == name:
				return opt.value
		return default

class RootSpec(BaseNode):
	def __init__(self, type):
		self.type = type

class FieldType(BaseNode):
	def __init__(self, type, is_weak=False):
		self.type = type
		self.is_weak = is_weak

class Field(BaseNode):
	def __init__(self, name, type, default=None):
		self.name = name
		self.type = type
		self.default = default

class Constructor(BaseNode):
	def __init__(self, name, args=None):
		self.name = name
		self.args = [] if args is None else args

class Node(BaseNode):
	def __init__(self, name, base, fields=None, ctrs=None, is_abstract=False):
		self.name = name
		self.base = base
		self.fields = [] if fields is None else fields
		self.ctrs = [] if ctrs is None else ctrs
		self.is_abstract = is_abstract

class SpecFile(BaseNode):
	def __init__(self, targets=None, visitors=None, root=None, nodes=None):
		self.targets = [] if targets is None else targets
		self.visitors = [] if visitors is None else visitors
		self.root = root
		self.nodes = [] if nodes is None else nodes
		self.types = {}
		self.filename = None

class NodeVisitor(object):
	def generic_visit(self, node):
		pass
	def visit(self, node):
		func = 'visit_' + node.__class__.__name__
		if hasattr(self, func):
			func = getattr(self, func)
			return func(node)
		else:
			return self.generic_visit(node)
