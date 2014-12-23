from . import ccode
from . import ccodeio
from . import nodes
from . import report
from . import target
from .target import OptionInfo as OptInf

class CPlusPlusTarget(target.CodegenTarget):
    # Name of the target as in the spec file
    name = "CPlusPlus"

    # Options allowed in target X { ... } blocks
    options = {
        "allocator":           OptInf(nodes.StringLiteral, "new $@"),
        "class_extra":         OptInf(nodes.ListLiteral, []),
        "cpp_indent":          OptInf(nodes.StringLiteral, " "),
        "deleter":             OptInf(nodes.StringLiteral, "delete $$"),
        "epilog":              OptInf(nodes.StringLiteral, ""),
        "header_only":         OptInf(nodes.BoolLiteral, True),
        "includes":            OptInf(nodes.ListLiteral, []),
        "indent":              OptInf(nodes.StringLiteral, "    "),
        "list_type":           OptInf(nodes.StringLiteral, "std::vector<$@>"),
        "namespace":           OptInf(nodes.StringLiteral, ""),
        "prolog":              OptInf(nodes.StringLiteral, ""),
        "strong_ptr":          OptInf(nodes.StringLiteral, "$@*"),
        "use_accessors":       OptInf(nodes.BoolLiteral, False),
        "use_line_directives": OptInf(nodes.BoolLiteral, True),
        "weak_ptr":            OptInf(nodes.StringLiteral, "$@*"),
    }

    # Options allowed in extern X { ... } blocks
    external_options = {
        "construct": OptInf(nodes.StringLiteral, ""),
        "destruct":  OptInf(nodes.StringLiteral, ""),
        "type":      OptInf(nodes.StringLiteral, "", True),
    }

    def __init__(self, spec):
        self.spec = spec
        self.pstack = []

        # TODO: move to super class, pass spec file up to super constructor
        have_target = False
        for target in spec.targets:
            if target.name == self.name:
                if have_target:
                    report.error("spec file '%s' contains multiple " % spec.filename +
                                 "'%s' targets, only one is allowed" % self.name)
                self.target = target
                have_target = True

        if not have_target:
            report.warning("spec file '%s' contains no " % spec.filename +
                           "'%s' target, attempting to use default options " % self.name +
                           "(some options may be required)")

        super().__init__(self.target.options, self.target.externs)

    def extern_type(self, name):
        return self.get_ext_opt(name, "type")

    def extern_destructor(self, name):
        return self.get_ext_opt(name, "destruct", "")

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

    def line_dir(self, location):
        if location:
            lds = self.get_opt("use_line_directives")
            if lds and lds.value:
                return ccode.CppLine(first='%d' % location.line,
                                     second='"%s"' % location.file)
        return ccode.Stmt(code='')

    def reset_line_dir(self):
        lds = self.get_opt("use_line_directives")
        if lds and lds.value:
            return ccode.CppLineReset()
        return ccode.Stmt(code='')

    def codegen(self, out_filename, indent='  ', cpp_indent=' '):
        """
        First builds a CCodeNode tree from the spec file and then calls the
        codegen method to generate output code.
        """

        self.tu = ccode.TranslationUnit(filename=out_filename, is_header=True)
        self.pstack.append(self.tu)

        # include required by primitive string type
        self.tu.includes.append(ccode.CppInclude(first="<string>"))

        includes = self.get_opt("includes", None)
        if includes:
            for inc in includes.value:
                if not isinstance(inc, nodes.StringLiteral):
                    report.error("invalid data type '%s' in " % inc.__class__.__name__ +
                                 "'includes' option for codegen target '%s'" % self.name)
                inc_name = inc.value
                # Add double quotes if not <> include and has no enclosing quotes
                if (not inc_name.startswith('<') and not inc_name.endswith('>')) and \
                   (not inc_name.startswith('"') and not inc_name.endswith('"')):
                    inc_name = '"' + inc_name + '"'
                self.tu.includes.append(self.line_dir(includes.location))
                self.tu.includes.append(ccode.CppInclude(first=inc_name))
                self.tu.includes.append(self.reset_line_dir())

        ns_name = self.get_opt("namespace")
        if ns_name:
            self.top.stmts.append(self.line_dir(ns_name.location))
            ns_name = ns_name.value
            ns = ccode.Namespace(name=ns_name)
            ns.stmts.append(self.reset_line_dir())
            self.top.stmts.append(ns)
            self.pstack.append(ns)
            self.top.stmts.append(ccode.BlankLine())

        # forward declare all the node types
        for node in self.spec.nodes:
            fd = ccode.ClassForwardDecl(name=node.name, is_struct=True)
            self.top.stmts.append(fd)

        self.top.stmts.append(ccode.BlankLine())

        # create a class for each visitor
        # TODO: use the visitor X { ... } block options to control output
        for visitor in self.spec.visitors:
            self.top.stmts.append(self.line_dir(visitor.location))
            cls = ccode.ClassDecl(name=visitor.name)
            cls.fields.append(self.reset_line_dir())
            self.top.stmts.append(cls)
            self.pstack.append(cls)
            for node in self.spec.nodes:
                meth_type = ccode.DataType(name="void")
                param_type = ccode.DataType(name=node.name + "&")
                meth_param = ccode.Parameter(type=param_type, name="node")
                meth = ccode.InlineMethod(
                        type=meth_type,
                        name="visit",
                        params=[meth_param])
                cls.methods.append(meth)
            self.pstack.pop()

        self.top.stmts.append(ccode.BlankLine())

        # create all the node classes
        for node in self.spec.nodes:
            self.top.stmts.append(self.line_dir(node.location))
            bases = [node.base] if node.base else []
            cls = ccode.ClassDecl(name=node.name, bases=bases)
            self.top.stmts.append(cls)
            self.pstack.append(cls)
            self.top.fields.append(self.reset_line_dir())
            self.add_fields(node)
            self.add_constructors(node)
            self.add_destructor_decl(node)
            self.add_method_decls(node)
            self.add_class_extra()
            self.pstack.pop()
            self.top.stmts.append(ccode.BlankLine())

        # create all the destructor definitions and accessors after the classes are fully defined
        for node in self.spec.nodes:
            self.add_method_defs(node)
            self.add_destructor_def(node)

        ns_name = self.get_opt("namespace")
        if ns_name:
            # pop the namespace off
            self.pstack.pop()

        # codegen everything to CCodeIO object
        out = ccodeio.CCodeIO(out_filename, indent, cpp_indent)
        self.tu.codegen(out)
        return out.contents

    def add_class_extra(self):
        extra = self.get_opt("class_extra", None)
        if extra:
            self.top.extra_stmts.append(self.line_dir(extra.location))
            for ext in extra.value:
                if not isinstance(ext, nodes.StringLiteral):
                    raise ValueError("expected a list of string literal for 'class_extra' option")
                self.top.extra_stmts.append(ccode.Stmt(code=ext.value))
            self.top.extra_stmts.append(self.reset_line_dir())

    def add_getter_decl(self, field):
        meth = ccode.MethodDecl(type=self.datatype_from_field(field),
                                name='get_' + field.name,
                                params=[],
                                is_const=True)
        #meth.stmts.append(ccode.Stmt(code='return ' + field.name + ';'))
        self.top.methods.append(meth)

    def add_setter_decl(self, field):
        param = ccode.Parameter(type=self.datatype_from_field(field),
                                name='value')
        meth = ccode.MethodDecl(type=ccode.DataType(name='void'),
                                name='set_' + field.name,
                                params=[param])
        #field_name = 'this->' + field.name if field.name == 'value' else field.name
        #if not field.type.is_weak and \
        #        isinstance(field.type.type, (nodes.Node, nodes.ExternType)):
        #    meth.stmts.append(ccode.Stmt(code='delete ' + field_name + ';'))
        #meth.stmts.append(ccode.Stmt(code=field_name + ' = value;'))
        self.top.methods.append(meth)

    def add_method_decls(self, node):
        use_accessors = self.get_opt("use_accessors", None)
        if use_accessors:
            if not isinstance(use_accessors, nodes.BoolLiteral):
                raise ValueError("expected a boolean literal for 'use_accessors'")
            if use_accessors.value:
                if self.get_opt("use_accessors", False):
                    for field in node.fields:
                        self.add_getter_decl(field)
                        self.add_setter_decl(field)
        for visitor in self.spec.visitors:
            meth_type = ccode.DataType(name="void")
            param_type = ccode.DataType(name=visitor.name + "&")
            meth_param = ccode.Parameter(type=param_type, name="visitor")
            meth = ccode.InlineMethod(type=meth_type, name="accept", params=[meth_param])
            meth.stmts.append(ccode.Stmt(code="visitor.visit(*this);"))
            self.top.methods.append(meth)

    def add_getter_def(self, cls, field):
        meth = ccode.Method(type=self.datatype_from_field(field),
                            name='get_' + field.name,
                            params=[],
                            is_const=True,
                            cls=cls)
        meth.stmts.append(ccode.Stmt(code='return ' + field.name + ';'))
        self.top.stmts.append(meth)

    def add_setter_def(self, cls, field):
        param = ccode.Parameter(type=self.datatype_from_field(field),
                                name='value')
        meth = ccode.Method(type=ccode.DataType(name='void'),
                            name='set_' + field.name,
                            params=[param],
                            cls=cls)
        field_name = 'this->' + field.name if field.name == 'value' else field.name
        if not field.type.is_weak and \
                isinstance(field.type.type, (nodes.Node, nodes.ExternType)):
            meth.stmts.append(ccode.Stmt(code='delete ' + field_name + ';'))
        meth.stmts.append(ccode.Stmt(code=field_name + ' = value;'))
        self.top.stmts.append(meth)

    def add_method_defs(self, node):
        use_accessors = self.get_opt("use_accessors", None)
        if use_accessors:
            if not isinstance(use_accessors, nodes.BoolLiteral):
                raise ValueError("expected a boolean literal for 'use_accessors'")
            if use_accessors.value:
                if self.get_opt("use_accessors", False):
                    for field in node.fields:
                        self.add_getter_def(node.name, field)
                        self.add_setter_def(node.name, field)

    def datatype_from_field(self, field):
        if isinstance(field.type.type, nodes.Node):
            return ccode.DataType(name=field.type.type.name + '*')
        elif isinstance(field.type.type, nodes.PrimitiveType):
            return ccode.DataType(name=self.primitive_type(field.type.type.name))
        elif isinstance(field.type.type, nodes.ListElementType):
            el_type = field.type.type.type
            list_type = self.get_opt('list_type', 'std::vector<$@>')
            list_type = list_type.value
            star = '*' if isinstance(el_type, nodes.Node) else ''
            list_type = list_type.replace('$@', el_type.name + star)
            return ccode.DataType(name=list_type)
        elif isinstance(field.type.type, nodes.ExternType):
            ext_type = self.extern_type(field.type.type.name)
            if not ext_type:
                raise ValueError("extern in target doesn't specify a type: option")
            if not isinstance(ext_type, nodes.StringLiteral):
                raise ValueError("expected string literal")
            return ccode.DataType(name=ext_type.value)

    def add_fields(self, node):
        for field in node.fields:
            self.top.fields.append(self.line_dir(field.location))
            dt = self.datatype_from_field(field)
            if dt is None:
                raise ValueError("unknown field type '%s'" % field.type.type.name)
            self.top.fields.append(ccode.Field(type=dt, name=field.name))
            self.top.fields.append(self.reset_line_dir())

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
            self.top.constructors.append(self.line_dir(ctr.location))
            ctor = ccode.Constructor(name=node.name)
            self.top.constructors.append(ctor)
            self.top.constructors.append(self.reset_line_dir())
            self.pstack.append(ctor)
            self.add_construct_params(ctr, node)
            self.add_initializers(ctr, node)
            self.pstack.pop()

    def add_destructor_decl(self, node):
        dtor = ccode.DestructorDecl(name=self.top.name, is_virtual=True)
        self.top.destructor = dtor

    def add_destructor_def(self, node):
        dtor = ccode.Destructor(name=node.name, is_inline=True)
        self.top.stmts.append(dtor)
        self.pstack.append(dtor)
        self.delete_stmts(node)
        self.pstack.pop()
        self.top.stmts.append(ccode.BlankLine())

    def delete_stmts(self, node):
        for field in node.fields:
            if not field.type.is_weak:
                if isinstance(field.type.type, nodes.Node):
                        #self.top.stmts.append(ccode.DeleteStmt(target=field.name))
                        self.top.stmts.append(ccode.Stmt(code='delete ' + field.name))
                elif isinstance(field.type.type, nodes.ExternType):
                    dtor_stmt = self.extern_destructor(field.type.type.name)
                    dtor_stmt = dtor_stmt.value.replace('$$', field.name)
                    self.top.stmts.append(ccode.Stmt(code=dtor_stmt))
                elif isinstance(field.type.type, nodes.ListElementType):
                    dtor_stmt = ccode.Stmt(code='for (auto i : ' + field.name +
                        ') { delete i; }')
                    self.top.stmts.append(dtor_stmt)
