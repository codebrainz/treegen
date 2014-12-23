#!/usr/bin/env python3

import sys

counter = 0
LIMIT = 1000

def gen_node():
    global counter
    next_node = 'node_%d' % counter
    counter += 1
    node_name = next_node.title()
    node_field = '%s_field' % next_node
    code  = 'node %s {\n' % node_name
    code += '  %s %s;\n' % ('int', node_field)
    code += '  %s(%s);\n' % (node_name, node_field)
    code += '}\n\n'
    sys.stdout.write(code)
    if counter == LIMIT:
        sys.stderr.write("status: wrote %d independent node classes\n" % counter)
        sys.exit(0)

sys.stdout.write('''\
//
// Non-Horrible generated test to run with `treegen'
//
// Just lots of nodes but no subclassing
//

target CPlusPlus {
    header_only: true;
    use_accessors: true;
    use_line_directives: true;
}

''')

while True:
    gen_node()
