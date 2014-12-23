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

# TODO: can probably make this way more efficient
def _write_if_different(fn, out_file, content):
    # on error, content will be empty, don't overwrite last output in this case
    if not content:
        return
    existing_content = ''
    with open(fn, 'r') as file:
        existing_content = file.read()
    # only over-write if changed to avoid modifying file times if no change
    if existing_content != content:
        if hasattr(out_file, "seek"):
            out_file.seek(0)
        if hasattr(out_file, "truncate"):
            out_file.truncate(0)
        out_file.write(content)

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
        if out_filename is None:
            out_file.write(code)
        else:
            _write_if_different(out_filename, out_file, code)
    return code
