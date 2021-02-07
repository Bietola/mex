from enum import Enum

from mex.utils import eprint

class ValType(Enum):
    LITERAL = 1
    EXPR = 2
    ERROR = 3

class Val:
    def __str__(self):
        if self.valType == ValType.ERROR:
            return "Error({})".format(self.val)
        else:
            return str(self.val)

    def __init__(self, valType, val):
        self.valType = valType
        self.val = val

    def Lit(val):
        # TODO: Don't parse only number literals
        if isinstance(val, str) and val.replace('.', '', 1).isdigit():
            val = float(val)

        return Val(ValType.LITERAL, val)

    def Nil():
        return Val.Lit(None)

    def raw(self):
        if self.valType == ValType.ERROR:
            return "RawError({})".format(self.val)
        else:
            return self.val

    def eval(self, key, scope):
        if self.valType == ValType.ERROR or self.valType == ValType.LITERAL:
            return self
        elif self.valType == ValType.EXPR:
            import mex.main
            return mex.main.do_eval_interpolation(key, self.val, scope)
        else:
            assert False, "Illegal branch"

