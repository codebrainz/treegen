import sys
from .nodes import *
from . import report

# Supported codegen targets, update when adding new targets
from . import cplusplus
targets = {
    "CPlusPlus": cplusplus.CPlusPlusTarget
}

def _target_from_name(name, targets):
    for target in targets:
        if target.name == name:
            return target
    return None

def codegen(spec, target, out_file=None, out_filename=None, indent='  '):
    if not target in targets:
        tgt = _target_from_name(target, spec.targets)
        if tgt:
            report.error("unknown target '%s'" % target, tgt.location)
        else:
            report.error("unknown target '%s'" % target)
    target = targets[target](spec)
    code = target.codegen(out_filename, indent)
    if out_file is not None:
        out_file.write(code)
    return code
