from collections import namedtuple
from . import report

OptionInfoT = namedtuple('OptionInfo', "type default required")
def OptionInfo(type, default, required=False):
    return OptionInfoT(type, default, required)

class CodegenTarget(object):
    """
    Base class for codegen targets (ex. CPlusPlusTarget).
    """

    def __init__(self, opts=None, externs=None):

        if not hasattr(self.__class__, "name"):
            raise ValueError("The codegen target class does not contain a 'name' variable")

        if opts is not None:
            if not hasattr(self.__class__, "options"):
                raise ValueError("The codegen target %s class does " % self.name +
                                 "not contain an 'options' variable")
            self._dupe_check_options(opts)
            self.opts = dict((o.name, o.value) for o in opts)
        else:
            self.opts = {}
        self._validate_opts()

        if externs is not None:
            if not hasattr(self.__class__, "external_options"):
                raise ValueError("The codegen target %s class " % self.name +
                                 "does not contain an 'external_options' " +
                                 "variable")
            self.externs = {}
            for extern in externs:
                self.externs[extern.name] = dict((o.name, o.value) for o in extern.options)
                self._dupe_check_extern_options(extern.options, extern.name)
        else:
            self.externs = {}
        self._validate_externs()

    def _dupe_check_options(self, options):
        optset = set()
        for opt in options:
            if opt.name in optset:
                report.error("duplicate option '%s' in codegen target " % opt.name +
                             "'%s'" % self.name, opt.location)
            optset.add(opt.name)

    def _dupe_check_extern_options(self, options, name):
        optset = set()
        for opt in options:
            if opt.name in optset:
                report.error("duplicate option '%s' in codegen target " % opt.name +
                             "'%s' extern type '%s'" % (self.name, name),
                             opt.location)
            optset.add(opt.name)

    def _validate_opts(self):
        # First validate the existence and types of the options supplied
        for name, value in self.opts.items():
            if not name in self.options:
                report.error("unexpected option '%s' in target '%s'" % (name, self.name),
                             self.opts[name].location)
            elif not isinstance(value, self.options[name].type):
                report.error("wrong data type for option '%s' of codegen " % name +
                             "target '%s', expected a '%s' but a '%s' was used" % (
                                self.name,
                                self.options[name].type.__name__,
                                value.__class__.__name__),
                             self.opts[name].location)
        # Then fill in the default values for those not specified
        for name, info in self.options.items():
            if name not in self.opts:
                if info.required:
                    report.error("required option '%s' was " % name +
                                "missing for codegen target '%s'" % self.name)
                if isinstance(info.default, list): # copy to prevent using same list over and over
                    self.opts[name] = list(info.default)
                else:
                    self.opts[name] = info.default

    def _validate_externs(self):
        # First validate the existence and types of the options supplied to each extern
        for type_name, options in self.externs.items():
            for name, value in options.items():
                if not name in self.external_options:
                    report.error("unexpected option '%s' in codegen " % name +
                                 "target '%s' extern type '%s'" % (self.name, type_name),
                                 options[name].location)
                elif not isinstance(value, self.external_options[name].type):
                    report.error("wrong data type for option '%s' of codegen " % name +
                                 "target '%s' extern type '%s', " % (self.name, type_name) +
                                 "expected a '%s' but a '%s' was used" % (
                                    self.external_options[name].type.__name__,
                                    value.__class__.__name__),
                                 options[name].location)
        # Then fill in the default values for each extern where one wasn't specified
        for type_name, options in self.externs.items():
            for name, info in self.external_options.items():
                if name not in options:
                    if info.required:
                        report.error("required option '%s' was " % name +
                                     "missing for codegen target '%s'" % self.name +
                                     "extern type '%s'" % type_name)
                    options[name] = info.default

    def get_opt(self, name, default=None):
        return self.opts.get(name, default)

    def get_ext_opt(self, type, name, default=None):
        options = self.externs.get(type, {})
        return options.get(name, default)

