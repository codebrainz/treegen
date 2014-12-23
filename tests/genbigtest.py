#!/usr/bin/env python3

import sys

MAGIC = 42 # TODO: reason about and use a real value here
max_depth = sys.getrecursionlimit() - MAGIC
counter = 0

def gen_node():
    global counter
    next_node = 'node_%d' % counter
    if counter == 0:
        parent = ''
    else:
        parent = ' : node_%d' % (counter - 1)
    parent = parent.title()
    counter += 1
    node_name = next_node.title()
    node_field = '%s_field' % next_node
    code  = 'node %s%s {\n' % (node_name, parent)
    code += '  %s %s;\n' % ('int', node_field)
    code += '  %s(%s);\n' % (node_name, node_field)
    code += '}\n\n'
    sys.stdout.write(code)
    if counter == max_depth:
        sys.stderr.write("status: wrote %d nested node subclasses\n" % counter)
        sys.exit()

sys.stdout.write('''\
//
// Horrible generated test to run with `treegen'
//
// Every node subclasseses from the one before it except the top.
//

target CPlusPlus {
    header_only: true;
    use_accessors: true;
    use_line_directives: true;
}

''')

while True:
    gen_node()
