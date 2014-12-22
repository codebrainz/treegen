from . import ccode
from . import ccodeio
from . import nodes

class CPlusPlusTarget(object):

	def __init__(self, spec):
		self.spec = spec
		self.pstack = []
		for target in spec.targets:
			if target.name == "CPlusPlus":
				self.target = target
				break
		else:
			raise ValueError("spec contains no 'CPlusPlus' target")
		self.externs = {}
		for extern in self.target.externs:
			if extern in self.externs:
				raise ValueError("duplicate extern types '%s' in target '%s'" % (
					extern.name, self.target.name))
			self.externs[extern.name] = extern

	def extern_type(self, name):
		extern = self.externs[name]
		type = extern.get_option("type").value
		if type.startswith('"') and type.endswith('"'):
			type = type[1:-1]
		return type

	def extern_destructor(self, name):
		extern = self.externs[name]
		opt = extern.get_option("destruct")
		if opt:
			type = opt.value
			if type.startswith('"') and type.endswith('"'):
				type = type[1:-1]
			return type
		return ""

	def primitive_type(self, name):
		d = {
			"bool": "bool",
			"float": "float",
			"int": "int",
			"string": "std::string",
		}
		return d[name]

	@property
	def top(self):
		return self.pstack[-1]

	def codegen(self, out_filename, indent='  ', cpp_indent=' '):
		"""
		First builds a CCodeNode tree from the spec file and then calls the
		codegen method to generate output code.
		"""

		self.tu = ccode.TranslationUnit(filename=out_filename, is_header=True)
		self.pstack.append(self.tu)

		self.tu.includes.extend([
			ccode.CppInclude(first="<string>"),
			ccode.CppInclude(first="<vector>")
		])

		ns_name = self.target.get_option("namespace")
		if ns_name:
			ns_name = ns_name.value.strip('"')
			ns = ccode.Namespace(name=ns_name)
			self.top.stmts.append(ns)
			self.pstack.append(ns)
			self.top.stmts.append(ccode.BlankLine())

		# forward declare all the node types
		for node in self.spec.nodes:
			fd = ccode.ClassForwardDecl(name=node.name, is_struct=True)
			self.top.stmts.append(fd)

		self.top.stmts.append(ccode.BlankLine())

		# create a class for each visitor
		for visitor in self.spec.visitors:
			cls = ccode.ClassDecl(name=visitor.name)
			self.top.stmts.append(cls)
			self.pstack.append(cls)
			for node in self.spec.nodes:
				meth_type = ccode.DataType(name="void")
				param_type = ccode.DataType(name=node.name + "&")
				meth_param = ccode.Parameter(type=param_type, name="node")
				meth = ccode.Method(
						type=meth_type,
						name="visit",
						params=[meth_param])
				cls.methods.append(meth)
			self.pstack.pop()

		self.top.stmts.append(ccode.BlankLine())

		# create all the node classes
		for node in self.spec.nodes:
			bases = [node.base] if node.base else []
			cls = ccode.ClassDecl(name=node.name, bases=bases)
			self.top.stmts.append(cls)
			self.pstack.append(cls)
			self.add_fields(node)
			self.add_constructors(node)
			self.add_destructor(node)
			self.add_methods(node)
			extra = self.target.get_option("class_extra", None)
			if extra:
				extra = extra.value
				if extra.startswith('"') and extra.endswith('"'):
					extra = extra[1:-1]
				cls.extra_stmts.append(ccode.Stmt(code=extra))
			self.pstack.pop()
			self.top.stmts.append(ccode.BlankLine())

		self.pstack.pop()

		# codegen everything to CCodeIO object
		out = ccodeio.CCodeIO(indent, cpp_indent)
		self.tu.codegen(out)
		return out.getvalue()

	def add_getter(self, field):
		meth = ccode.Method(type=self.datatype_from_field(field),
		                    name='get_' + field.name,
		                    params=[],
		                    is_const=True)
		meth.stmts.append(ccode.Stmt(code='return ' + field.name + ';'))
		self.top.methods.append(meth)

	def add_setter(self, field):
		param = ccode.Parameter(type=self.datatype_from_field(field),
		                        name='value')
		meth = ccode.Method(type=ccode.DataType(name='void'),
		                    name='set_' + field.name,
		                    params=[param])
		field_name = 'this->' + field.name if field.name == 'value' else field.name
		if not field.type.is_weak and \
				isinstance(field.type.type, (nodes.Node, nodes.ExternType)):
			meth.stmts.append(ccode.Stmt(code='delete ' + field_name + ';'))
		meth.stmts.append(ccode.Stmt(code=field_name + ' = value;'))
		self.top.methods.append(meth)

	def add_methods(self, node):
		if self.target.get_option("use_accessors", False):
			for field in node.fields:
				self.add_getter(field)
				self.add_setter(field)
		for visitor in self.spec.visitors:
			meth_type = ccode.DataType(name="void")
			param_type = ccode.DataType(name=visitor.name + "&")
			meth_param = ccode.Parameter(type=param_type, name="visitor")
			meth = ccode.Method(type=meth_type, name="accept", params=[meth_param])
			meth.stmts.append(ccode.Stmt(code="visitor.visit(*this);"))
			self.top.methods.append(meth)

	def datatype_from_field(self, field):
		if isinstance(field.type.type, nodes.Node):
			return ccode.DataType(name=field.type.type.name + '*')
		elif isinstance(field.type.type, nodes.PrimitiveType):
			return ccode.DataType(name=self.primitive_type(field.type.type.name))
		elif isinstance(field.type.type, nodes.ListElementType):
			el_type = field.type.type.type
			list_type = self.target.get_option('list_type', 'std::vector<$@>')
			list_type = list_type.value
			if list_type.startswith('"') and list_type.endswith('"'):
				list_type = list_type[1:-1]
			star = '*' if isinstance(el_type, nodes.Node) else ''
			list_type = list_type.replace('$@', el_type.name + star)
			return ccode.DataType(name=list_type)
		elif isinstance(field.type.type, nodes.ExternType):
			ext_type = self.externs[field.type.type.name]
			ext_type = ext_type.get_option('type')
			if not ext_type:
				raise ValueError("extern in target doesn't specify a type: option")
			ext_type = ext_type.value
			if ext_type.startswith('"') and ext_type.endswith('"'):
				ext_type = ext_type[1:-1]
			else:
				raise ValueError("expected string literal")
			return ccode.DataType(name=ext_type)

	def add_fields(self, node):
		for field in node.fields:
			dt = self.datatype_from_field(field)
			if dt is None:
				raise ValueError("unknown field type '%s'" % field.type.type.name)
			self.top.fields.append(ccode.Field(type=dt, name=field.name))

	def find_field(self, node, name):
		for field in node.fields:
			if field.name == name:
				return field
		return None

	def list_ctor_fields(self, ctor, node, fields_list):
		if node.base:
			self.list_ctor_fields(ctor, node.base, fields_list)
		if len(node.ctrs) > 0: # FIXME
			for arg in node.ctrs[0].args:
				field = node.get_field(arg)
				if field:
					fields_list.append(field)

	def add_construct_params(self, ctor, node):
		fields = []
		self.list_ctor_fields(ctor, node, fields)
		for field in fields:
			dt = self.datatype_from_field(field)
			if dt is None:
				raise ValueError("unknown field type '%s'" % field.type.type.name)
			self.top.params.append(ccode.Parameter(type=dt, name=field.name))

	def make_initializer(self, ctor, node):
		fields = []
		self.list_ctor_fields(ctor, node, fields)
		initializer = ccode.Initializer(target=node.name)
		for field in fields:
			init = ccode.InitializerArgument(name=field.name)
			initializer.args.append(init)
		return initializer

	def add_initializers(self, ctor, node):
		if node.base:
			init = ccode.ConstructorChainUp(target=node.base.name)
			if len(node.base.ctrs) > 0:
				fields = []
				self.list_ctor_fields(None, node.base, fields)
				for field in fields:
					init_arg = ccode.InitializerArgument(name=field.name)
					init.args.append(init_arg)
			self.top.initializers.append(init)
		if len(node.ctrs) > 0:
			for ctr in node.ctrs:
				for arg in ctr.args:
					init_arg = ccode.InitializerArgument(name=arg)
					init = ccode.Initializer(target=arg, arg=init_arg)
					self.top.initializers.append(init)

	def add_constructors(self, node):
		if len(node.ctrs) == 0:
			return
		for ctr in node.ctrs:
			ctor = ccode.Constructor(name=node.name)
			self.top.constructors.append(ctor)
			self.pstack.append(ctor)
			self.add_construct_params(ctr, node)
			self.add_initializers(ctr, node)
			self.pstack.pop()

	def delete_stmts(self, node):
		for field in node.fields:
			if not field.type.is_weak:
				if isinstance(field.type.type, nodes.Node):
						#self.top.stmts.append(ccode.DeleteStmt(target=field.name))
						self.top.stmts.append(ccode.Stmt(code='delete ' + field.name))
				elif isinstance(field.type.type, nodes.ExternType):
					dtor_stmt = self.extern_destructor(field.type.type.name)
					dtor_stmt = dtor_stmt.replace('$$', field.name)
					self.top.stmts.append(ccode.Stmt(code=dtor_stmt))
				elif isinstance(field.type.type, nodes.ListElementType):
					dtor_stmt = ccode.Stmt(code='for (auto i : ' + field.name +
						') { delete i; }')
					self.top.stmts.append(dtor_stmt)

	def add_destructor(self, node):
		dtor = ccode.Destructor(name=self.top.name, is_virtual=True)
		self.top.destructor = dtor
		self.pstack.append(dtor)
		self.delete_stmts(node)
		self.pstack.pop()
