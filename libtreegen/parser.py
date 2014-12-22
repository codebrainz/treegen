#!/usr/bin/env python3

import os
import sys
import ply.lex as lex
import ply.yacc as yacc
from .nodes import *

#
# Lexical analyzer
#

reserved = {
	"abstract": "ABSTRACT",
	"extern":   "EXTERN",
	"false":    "FALSE",
	"node":     "NODE",
	"null":     "NULL",
	"root":     "ROOT",
	"target":   "TARGET",
	"true":     "TRUE",
	"visitor":  "VISITOR",
	"weak":     "WEAK",
	"list":     "LIST",
}

primitives = {
	"bool":   "BOOL",
	"float":  "FLOAT",
	"int":    "INT",
	"string": "STRING",
}

tokens = [
	'BINLIT',
	'BOOLEAN',
	'CHRLIT',
	'COLON',
	'COMMA',
	'COMMENT',
	'DECLIT',
	'EQUAL',
	'FLOATLIT',
	'HEXLIT',
	'IDENT',
	'INTEGER',
	'LBRACE',
	'LBRACKET',
	'LPAREN',
	'OCTLIT',
	'RBRACE',
	'RBRACKET',
	'RPAREN',
	'SEMICOLON',
	'STRLIT',
] + \
list(reserved.values()) + \
list(primitives.values())

t_COLON     = '\:'
t_COMMA     = '\,'
t_EQUAL     = '\='
t_LBRACE    = '\{'
t_LBRACKET  = '\['
t_LPAREN    = '\('
t_RBRACE    = '\}'
t_RBRACKET  = '\]'
t_RPAREN    = '\)'
t_SEMICOLON = '\;'

def t_COMMENT(t):
	r'//[^\n]*\n|/\*(.+?)\*/'
	pass #ignored

def t_IDENT(t):
	r'[a-zA-Z_][a-zA-Z_0-9]*'
	if t.value == "true":
		t.type = 'BOOLEAN'
		t.value = True
	elif t.value == "false":
		t.type = 'BOOLEAN'
		t.value = False
	else:
		t.type = reserved.get(t.value, None)
		if t.type is None:
			t.type = primitives.get(t.value, 'IDENT')
	return t

def t_BINLIT(t):
	r'0[bB][0-1_]+'
	t.type = 'INTEGER'
	t.value = int(t.value.replace("_",""), 2)
	return t

def t_HEXLIT(t):
	r'0[xX][a-fA-F0-9_]+'
	t.type = 'INTEGER'
	t.value = int(t.value.replace("_",""), 16)
	return t

def t_OCTLIT(t):
	r'0[oO][0-7]+|0[0-9_]*'
	t.type = 'INTEGER'
	t.value = int(t.value.replace("_",""), 8)
	return t

def t_DECLIT(t):
	r'[1-9][0-9_]*'
	t.type = 'INTEGER'
	t.value = int(t.value.replace("_",""), 10)
	return t

def t_FLOATLIT(t):
	r'[0-9]*\.[0-9]+|[0-9]+\.[0-9]*'
	t.type = 'FLOAT'
	t.value = float(t.value)
	return t

# FIXME
def t_CHRLIT(t):
	r"'(''|[^'])*'"
	return t

# FIXME
def t_STRLIT(t):
	r'"(""|[^"])*"'
	return t

def t_newline(t):
	r'\n+'
	t.lexer.lineno += len(t.value)

t_ignore = ' \t'

def find_column(input, token):
	last_cr = input.rfind('\n', 0, token.lexpos)
	if last_cr < 0:
		last_cr = 0
	column = (token.lexpos - last_cr) + 1
	return column

def t_error(t):
	sys.stderr.write("error: %d:%d: illegal character '%s'" % (
		t.lexer.lineno, find_column(t.lexer.lexdata, t),
		t.value[0]))
	sys.exit(1)

#
# Syntax analyzer
#

start = "spec_file"

def push_parent(p, node):
	parents = getattr(p.parser, "parents")
	parents.append(node)

def pop_parent(p):
	parents = getattr(p.parser, "parents")
	top = parents[-1]
	parents.pop()

def add_node(p, node):
	parents = getattr(p.parser, "parents")
	top = parents[-1]
	node.parent = top
	top.children.append(node)
	#print("%s > %s" % (node.__class__.__name__, top.__class__.__name__))
	return node

def p_expr_list_first(p):
	''' expr_list : expr
	'''
	p[0] = [p[1]]
	return p

def p_expr_list_rest(p):
	''' expr_list : expr_list COMMA expr
	'''
	p[1].append(p[3])
	p[0] = p[1]
	return p

def p_list_literal(p):
	''' list_literal : LBRACKET expr_list RBRACKET
	'''
	p[0] = ListLiteral(p[2])
	return p

def p_list_literal_empty(p):
	''' list_literal : LBRACKET RBRACKET
	'''
	p[0] = ListLiteral([])
	return p

def p_literal_bool(p):
	''' literal : BOOLEAN
	'''
	p[0] = add_node(p, BoolLiteral(p[1]))
	return p

def p_literal_int(p):
	''' literal : INTEGER
	'''
	p[0] = add_node(p, IntLiteral(p[1]))
	return p

def p_literal_float(p):
	''' literal : FLOAT
	'''
	p[0] = add_node(p, FloatLiteral(p[1]))
	return p

def p_literal_chr(p):
	''' literal : CHRLIT
	'''
	p[0] = add_node(p, CharLiteral(p[1]))
	return p

def p_literal_str(p):
	''' literal : STRLIT
	'''
	p[0] = add_node(p, StringLiteral(p[1]))
	return p

def p_literal_null(p):
	''' literal : NULL
	'''
	p[0] = add_node(p, NullLiteral())
	return p

def p_literal_list(p):
	''' literal : list_literal
	'''
	p[0] = p[1]
	return p

def p_expr(p):
	''' expr : literal
	'''
	p[0] = p[1]
	return p

def p_expr_call(p):
	''' expr : IDENT LPAREN RPAREN
	'''
	p[0] = add_node(p, Call(p[1]))
	return p

def p_primitive_type(p):
	''' primitive_type : BOOL
	                   | FLOAT
	                   | INT
	                   | STRING
	'''
	p[0] = p[1]
	return p

def p_data_type_prim(p):
	''' data_type : primitive_type
	'''
	p[0] = add_node(p, PrimitiveType(p[1]))
	return p

def p_data_type_unresolved(p):
	''' data_type : IDENT
	'''
	p[0] = add_node(p, UnresolvedType(p[1]))
	return p

def p_option_decl(p):
	''' option_decl : IDENT
	'''
	p[0] = add_node(p, Option(p[1], None))
	push_parent(p, p[0])
	return p

def p_option(p):
	''' option : option_decl COLON expr SEMICOLON
	'''
	p[0] = p[1]
	p[0].value = p[3]
	pop_parent(p)
	return p

def p_option_list_first(p):
	''' option_list : option
	'''
	p[0] = [p[1]]
	return p

def p_option_list_rest(p):
	''' option_list : option_list option
	'''
	p[1].append(p[2])
	p[0] = p[1]
	return p

def p_extern(p):
	''' extern : EXTERN IDENT LBRACE option_list RBRACE
	'''
	p[0] = add_node(p, ExternTypeDef(p[2], p[4]))
	for opt in p[4]:
		opt.parent = p[0]
		p[0].children.append(opt)
	return p

def p_target_item_option(p):
	''' target_item : option
	'''
	p[0] = p[1]
	return p

def p_target_item_extern(p):
	''' target_item : extern
	'''
	p[0] = p[1]
	return p

def p_target_item_list_first(p):
	''' target_item_list : target_item
	'''
	p[0] = [p[1]]
	return p

def p_target_item_list_rest(p):
	''' target_item_list : target_item_list target_item
	'''
	p[1].append(p[2])
	p[0] = p[1]
	return p

def p_target_decl(p):
	''' target_decl : TARGET IDENT
	'''
	p[0] = add_node(p, Target(p[2]))
	push_parent(p, p[0])
	return p

def p_target(p):
	''' target : target_decl LBRACE target_item_list RBRACE
	'''
	p[0] = p[1]
	for item in p[3]:
		if isinstance(item, Option):
			p[0].options.append(item)
		elif isinstance(item, ExternTypeDef):
			p[0].externs.append(item)
		else:
			raise RuntimeError('unexpected item %s' % item)
		p[0].children.append(item)
		item.parent = p[0]
	pop_parent(p)
	return p

def p_visitor_decl(p):
	''' visitor_decl : VISITOR IDENT
	'''
	p[0] = add_node(p, Visitor(p[2]))
	push_parent(p, p[0])
	return p

def p_visitor(p):
	''' visitor : visitor_decl LBRACE option_list RBRACE
	'''
	p[0] = p[1]
	p[0].options = p[3]
	pop_parent(p)
	return p

def p_visitor_empty(p):
	''' visitor : visitor_decl LBRACE RBRACE
	'''
	p[0] = p[1]
	return p

def p_root(p):
	''' root : ROOT IDENT SEMICOLON
	'''
	p[0] = add_node(p, RootSpec(None))
	push_parent(p, p[0])
	p[0].type = add_node(p, UnresolvedType(p[2]))
	pop_parent(p)
	return p

def p_field_specifier(p):
	''' field_specifier : WEAK
	                    | LIST
	'''
	p[0] = p[1]
	return p

def p_field_specifier_list_first(p):
	''' field_specifier_list : field_specifier
	'''
	p[0] = [p[1]]
	return p

def p_field_specifier_list_rest(p):
	''' field_specifier_list : field_specifier_list field_specifier
	'''
	p[1].append(p[2])
	p[0] = p[1]
	return p

def p_field_decl(p):
	''' field_decl : IDENT
	'''
	p[0] = add_node(p, Field(type=None, name=p[1]))
	return p

def p_field_decl_init(p):
	''' field_decl : IDENT EQUAL expr
	'''
	p[0] = add_node(p, Field(type=None, name=p[1], default=p[3]))
	push_parent(p, p[0])
	add_node(p, p[3])
	pop_parent(p)
	return p

def p_field_decl_list_first(p):
	''' field_decl_list : field_decl
	'''
	p[0] = [p[1]]
	return p

def p_field_decl_list_rest(p):
	''' field_decl_list : field_decl_list COMMA field_decl
	'''
	p[1].append(p[3])
	p[0] = p[1]
	return p

def p_field_type(p):
	''' field_type : field_specifier_list data_type
	'''
	is_weak = True if "weak" in p[1] else False
	is_list = True if "list" in p[1] else False
	p[0] = FieldType(p[2], is_weak=is_weak)
	push_parent(p, p[0])
	if is_list:
		let = add_node(p, ListElementType(None, is_weak=is_weak))
		push_parent(p, let)
		let.type = add_node(p, p[2])
		pop_parent(p)
		p[0].type = let
	else:
		p[0].type = add_node(p, p[2])
	pop_parent(p)
	return p

def p_field_type_no_spec(p):
	''' field_type : data_type
	'''
	p[0] = add_node(p, FieldType(p[1]))
	return p

def p_fields(p):
	''' fields : field_type field_decl_list SEMICOLON
	'''
	p[0] = []
	for field in p[2]:
		push_parent(p, field)
		field.type = add_node(p, p[1])
		pop_parent(p)
		p[0].append(field)
	return p

def p_arg_list_first(p):
	''' arg_list : IDENT
	'''
	p[0] = [p[1]]
	return p

def p_arg_list_rest(p):
	''' arg_list : arg_list COMMA IDENT
	'''
	p[1].append(p[3])
	p[0] = p[1]
	return p

def p_ctor_ident(p):
	''' ctor_ident : IDENT
	'''
	p[0] = add_node(p, Constructor(p[1],[]))
	push_parent(p, p[0])

def p_ctor_no_args(p):
	''' ctor : ctor_ident LPAREN RPAREN SEMICOLON
	'''
	p[0] = p[1]
	return p

def p_ctor_with_args(p):
	''' ctor : ctor_ident LPAREN arg_list RPAREN SEMICOLON
	'''
	p[0] = p[1]
	p[0].args = p[3]
	pop_parent(p)
	return p

def p_node_specifier(p):
	''' node_specifier : ABSTRACT
	'''
	p[0] = p[1]
	return p

def p_node_specifier_list_first(p):
	''' node_specifier_list : node_specifier
	'''
	p[0] = [p[1]]
	return p

def p_node_specifier_list_rest(p):
	''' node_specifier_list : node_specifier_list node_specifier
	'''
	p[1].append(p[2])
	return p

def p_node_base(p):
	''' node_base : COLON IDENT
	'''
	p[0] = add_node(p, UnresolvedType(p[2], is_weak=True))
	return p

def p_node_item_fields(p):
	''' node_item : fields
	'''
	p[0] = p[1]
	return p

def p_node_item_ctor(p):
	''' node_item : ctor
	'''
	p[0] = p[1]
	return p

def p_node_item_list_first(p):
	''' node_item_list : node_item
	'''
	p[0] = [p[1]]
	return p

def p_node_item_list_rest(p):
	''' node_item_list : node_item_list node_item
	'''
	p[1].append(p[2])
	p[0] = p[1]
	return p

def p_node_type(p):
	''' node_type : node_specifier_list NODE
	'''
	p[0] = p[1]
	return p

def p_node_type_no_spec(p):
	''' node_type : NODE
	'''
	p[0] = []
	return p

def p_node_declarator(p):
	''' node_declarator : node_type IDENT
	'''
	abstract = True if "abstract" in p[1] else False
	p[0] = add_node(p, Node(p[2], None, is_abstract=abstract))
	push_parent(p, p[0])
	return p

def p_node_block(p):
	''' node_block : LBRACE node_item_list RBRACE
	'''
	p[0] = p[2]
	return p

def p_node_block_empty(p):
	''' node_block : LBRACE RBRACE
	'''
	p[0] = []
	return p

def p_node(p):
	''' node : node_declarator node_block
	'''
	p[0] = p[1]
	for item in p[2]:
		if isinstance(item, Field):
			p[0].fields.append(item)
		elif isinstance(item, Constructor):
			p[0].ctrs.append(item)
		elif all(isinstance(e, Field) for e in item):
			p[0].fields.extend(item)
		else:
			raise RuntimeError("unexpected node type '%s'" % item.__class__.__name__)
	p[0].base = None
	pop_parent(p)
	return p

def p_node_with_base(p):
	''' node : node_declarator node_base node_block
	'''
	p[0] = p[1]
	for item in p[3]:
		if isinstance(item, Field):
			p[0].fields.append(item)
		elif isinstance(item, Constructor):
			p[0].ctrs.append(item)
		elif all(isinstance(e, Field) for e in item):
			p[0].fields.extend(item)
		else:
			raise RuntimeError("unexpected node type '%s'" % item.__class__.__name__)
	p[0].base = p[2]
	pop_parent(p)
	return p

def p_spec_file_item_target(p):
	''' spec_file_item : target
	'''
	p[0] = p[1]
	return p

def p_spec_file_item_visitor(p):
	''' spec_file_item : visitor
	'''
	p[0] = p[1]
	return p

def p_spec_file_item_root(p):
	''' spec_file_item : root
	'''
	p[0] = p[1]
	return p

def p_spec_file_item_node_spec(p):
	''' spec_file_item : node
	'''
	p[0] = p[1]
	return p

def p_spec_file_item_list_first(p):
	''' spec_file_item_list : spec_file_item
	'''
	p[0] = [p[1]]
	return p

def p_spec_file_item_list_rest(p):
	''' spec_file_item_list : spec_file_item_list spec_file_item
	'''
	p[1].append(p[2])
	p[0] = p[1]
	return p

def find_extern_types(spec, types):
	for target in spec.targets:
		for extern in target.externs:
			if extern.name in types:
				types[extern.name].target_types.append(extern)
			else:
				types[extern.name] = ExternType(extern.name, [extern])

def find_node_types(spec, types):
	for node in spec.nodes:
		if node.name not in types:
			types[node.name] = node
		else:
			sys.stderr.write("error: duplicate node type %s\n" % node.name)

def resolve_node_fields(node, types):
	for field in node.fields:
		tp = field.type.type
		if isinstance(tp, UnresolvedType):
			if tp.name in types:
				field.type.type = types[field.type.type.name]
			else:
				sys.stderr.write("error: unresolved field type '%s'\n" % tp.name)
				sys.exit(1)

def resolve_node_base(node, types):
	if isinstance(node.base, UnresolvedType):
		if node.base.name in types:
			node.base = types[node.base.name]
		else:
			sys.stderr.write("error: unresolved base node type '%s'\n" % node.base.name)
			sys.exit(1)

def resolve_node_types(spec, types):
	for node in spec.nodes:
		resolve_node_fields(node, types)
		resolve_node_base(node, types)

def resolve_root_spec(spec, types):
	if spec.root and isinstance(spec.root.type, UnresolvedType):
		if spec.root.type.name in types:
			spec.root.type = types[spec.root.type.name]
		else:
			sys.stderr.write("error: unresolved root node type '%s'\n" % spec.root.type.name)
			sys.exit(1)

def resolve_list_types(spec, types):
	for node in spec.nodes:
		for field in node.fields:
			if isinstance(field.type.type, ListElementType):
				if isinstance(field.type.type.type, UnresolvedType):
					if field.type.type.type.name in types:
						field.type.type.type = types[field.type.type.type.name]
				else:
					sys.stderr.write("error: unresolved list node type '%s'\n" % field.type.type.name)
					sys.exit(1)

def resolve_types(spec):
	types = {}
	find_extern_types(spec, types)
	find_node_types(spec, types)
	resolve_node_types(spec, types)
	resolve_root_spec(spec, types)
	resolve_list_types(spec, types)
	return types

def check_include(fn_string, search_paths):
	if fn_string.startswith('"') and fn_string.endswith('"'):
		fn_string = fn_string[1:-1]
	if os.path.isabs(fn_string):
		return (fn_string, open(fn_string, 'r'))
	else:
		fn = os.path.abspath(fn_string)
		try:
			return (fn, open(fn, 'r'))
		except IOError:
			for dir in search_paths:
				fn = os.path.abspath(os.path.join(dir, fn_string))
				try:
					return (fn, open(fn, 'r'))
				except IOError:
					pass
		return (None, None)

def p_spec_file(p):
	''' spec_file : spec_file_item_list
	'''
	p[0] = getattr(p.parser, "parents")[0]
	for item in p[1]:
		if isinstance(item, Target):
			p[0].targets.append(item)
		elif isinstance(item, Visitor):
			p[0].visitors.append(item)
		elif isinstance(item, RootSpec):
			p[0].root = item
		elif isinstance(item, Node):
			p[0].nodes.append(item)
	p[0].types = resolve_types(p[0])
	return p

def p_error(t):
	sys.stderr.write('error %d:%d bad syntax\n' % (
		t.lexer.lineno, find_column(t.lexer.lexdata, t)))
	sys.exit(1)

def parse(file, filename, debug=True):
	lexer = lex.lex(debug=True) if debug \
				else lex.lex(debug=False, errorlog=lex.NullLogger())
	if file is not None:
		lexer.input(file.read())
	else:
		with open(filename, 'r') as f:
			lexer.input(f.read())
	parser = yacc.yacc(debug=True) if debug \
				else yacc.yacc(debug=False, errorlog=yacc.NullLogger())
	parents = []
	spec = SpecFile()
	spec.parent = None
	spec.filename = filename
	parents.append(spec)
	setattr(parser, "parents", parents)
	spec = parser.parse(lexer=lexer, tracking=True)
	return spec

