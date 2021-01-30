from enum import Enum

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
        return Val(ValType.LITERAL, val)

    def Nil():
        return Val.Lit(None)

    def raw (self):
        if self.valType == ValType.ERROR:
            return "RawError({})".format(self.val)
        else:
            return self.val
