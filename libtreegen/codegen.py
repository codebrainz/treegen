import sys
from .nodes import *

# Supported codegen targets
from .cplusplus import CPlusPlusTarget
targets = {
    "CPlusPlus": CPlusPlusTarget
}

def codegen(spec, target, out_file=None, out_filename=None, indent='  '):
    if not target in targets:
        raise ValueError("unknown target '%s'" % target)
    target = targets[target](spec)
    code = target.codegen(out_filename, indent)
    if out_file is not None:
        out_file.write(code)
    return code
