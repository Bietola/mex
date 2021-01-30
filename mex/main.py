import re
import sys
import json
import contextlib
import io
from enum import Enum

from mex.utils import eprint
from mex.context import Context, add_scope
import mex.dotted_dict as dotkey

###########
# Globals #
###########

env = {}
cached_exps = {}
lines = []

#######################
# Precompiles regexes #
#######################

# Warning: First capture group of these must be the indent
keyval_pair_re = re.compile('^(\s*)(.*?)\s*:(.>)?\s*(.*)$')
new_subscope_re = re.compile('^(\s*)(.*?):\s*$')

whitespace_re = re.compile('^\s*$')
list_ele_re = re.compile('^\s*-.*$')
heading_re = re.compile('^#.*$')

###########
# Classes #
###########

class ValType(Enum):
    LITERAL = 1
    EXPR = 2
    ERROR = 3

class Val:
    def __init__(self, valType, val):
        self.valType = valType
        self.val = val

    def __str__(self):
        if self.valType == ValType.ERROR:
            return str("Error({})".format(self.val))
        else:
            return str(self.val)

####################
# Helper functions #
####################

def do_eval_in_sub(scope, m):
    indent = m.group(1)
    name = m.group(2)
    control_seq = m.group(3)
    exp = m.group(4)

    str_key = indent + name
    name = add_scope(scope, name)
    control_char = control_sequence[0] # e.g.: from "E>" to "E"

    if control_char == "$":
        dotkey.insert(cached_exps, name, exp)
        val = do_eval_interpolation(name, exp, scope)
        return str_key + ":#> " + str(val)

    elif control_char == "#" or control_char == "S" or control_char == "E":
        if cached_exp := dotkey.get(cached_exps, name):
            if control_char == "#":
                val = do_eval_interpolation(name, cached_exp, scope)
            elif control_char == "S":
                val = cached_exp
            elif control_char == "E":
                val = cached_exp
                control_char = "$"

            return str_key + ":" + control_char + "> " + str(val)

    else:
        return str_key + ":" + control_char + "> " + "Error: Unknown control character: " + control_char

def is_op(s):
    return (s == "+" or s == "-" or s == "/" or s == "*" or s == "(" or s == ")")

def is_float(value):
  try:
    float(value)
    return True
  except:
    return False

def do_eval_interpolation(exp_key, interpolated_str, scope):
    return re.sub(
        r'\$\{(.*?)\}',
        lambda m: str(do_eval(exp_key, m.group(1), scope)),
        interpolated_str
    )

def do_eval(exp_key, exp, scope):
    def sub_identifier(m):
        anonymous_scope = m.group(1) != None
        ident = m.group(2)
        
        if anonymous_scope:
            ident = add_scope(scope, ident)

        val = dotkey.get(env, ident)
        if val == None:
            return Val(ValType.ERROR, "(No identifier named \"" + ident + "\")")
        elif type(val) is dict:
            return Val(ValType.ERROR, ident + " is a dictionary")
        elif val.val == None:
            return Val(ValType.ERROR, ident + " has a Null value")
        elif val.valType == ValType.ERROR:
            return val
        elif val.valType == ValType.EXPR:
            return do_eval_interpolation(exp_key, val.val, scope_of(ident))
        elif val.valType == ValType.LITERAL:
            # TODO: Do this only if necessary
            dotkey.insert(env, ident, val, False)
            return val
        else:
            assert False, "Fatal: Unhandled branch"

    exp = re.sub(
        r'\$(\.)?([a-zA-Z\_][\w\-\.]*)\b',
        lambda m: str(sub_identifier(m)),
        exp
    )

    stmts = exp.split(';')
    try:
        ctx = Context(exp_key, scope, env, cached_exps)

        for stmt in stmts[:-1]:
            exec(stmt.strip(), {'ctx': ctx})

        exec('ctx.ret = {}'.format(stmts[-1].strip()), {'ctx': ctx})

        return Val(ValType.LITERAL, ctx.ret)

    except Exception as e:
        return Val(ValType.ERROR, "EvalError({}) on Program({})".format(e, stmts))

    # eprint(exp_w_subs)

def scope_of(ident):
    return ident.split('.')[:-1]

def update_scope_and_then(scope, old_scope_lv, linenum, passthrough_re):
    indent_lv = 0
    new_subscope = ""
    just_augmented_scope = False
    and_then = None

    if m := new_subscope_re.match(line):
        indent_lv = len(m.group(1))
        new_subscope = m.group(2)

        just_augmented_scope = True
        and_then = None

    elif m := passthrough_re.match(line):
        indent_lv = len(m.group(1))
        new_subscope = ""

        and_then = m

    new_scope_lv = int(indent_lv / update_scope_and_then.INDENT_UNIT)
    lv_change = new_scope_lv - old_scope_lv

    just_previously_augmented_scope = update_scope_and_then.just_previously_augmented_scope
    # TODO: Check why this does not work
    # if not just_previously_augmented_scope:
    #     assert lv_change <= 0, "Indentation error at line " + str(linenum)
    update_scope_and_then.just_previously_augmented_scope = just_augmented_scope

    if lv_change < 0 or (lv_change == 0 and just_previously_augmented_scope):
        scope = scope[:new_scope_lv]

    if len(new_subscope) != 0: scope.append(new_subscope)
    
    return and_then, scope, new_scope_lv
# STATICS
update_scope_and_then.just_previously_augmented_scope = False
update_scope_and_then.INDENT_UNIT = 4

########
# Main #
########

def main():
    # Get contents of file
    lines = sys.stdin.read().split('\n')

    # Split file into body and storage sections
    try:
        splitPoint = next(filter(lambda e: e[1].strip() == "# STORAGE", enumerate(lines)))[0]
    except:
        splitPoint = -1

    if splitPoint == -1:
        body = lines
        storage = []
    else:
        body = lines[0:splitPoint]
        storage = lines[splitPoint+1:]

    # Get cached expressions from STORAGE section at the end of the file
    malformed_storage = False
    cached_exps = {}
    if not len(storage) == 0:
        try:
            cached_exps = json.loads('\n'.join(storage)) or {}
        except:
            eprint("Error: Malformed STORAGE section")
            malformed_storage = True

    # First pass: load environment (all variables) from body
    cur_scope_lv = 0
    scope = []
    just_augmented_scope = False
    for [linenum, line] in enumerate(body):
        if whitespace_re.match(line):
            continue

        if list_ele_re.match(line):
            continue

        if heading_re.match(line):
            continue

        m, scope, cur_scope_lv = update_scope_and_then(scope, cur_scope_lv, linenum, keyval_pair_re)
        if m:
            name = m.group(2)
            control_seq = m.group(3)
            control_char = control_seq[0] if control_seq else None

            if (control_char == '$'):
                val = Val(ValType.EXPR, m.group(4))
            elif (control_char == '#'):
                val = Val(ValType.EXPR, dotkey.get(cached_exps, add_scope(scope, name)))
            else:
                val = Val(ValType.LITERAL, m.group(4))
            dotkey.insert(env, add_scope(scope, name), val, True)

    eprint(env, end = '')

    # eprint(body)
    # eprint(storage)

    # for line in body:
    #     print(
    #         re.sub(
    #             r'^(\s*)(.*)\s*:(.)>\s*(.*)$',
    #             do_eval_in_sub,
    #             line
    #         )
    #     )

    scope = []
    cur_scope_lv = 0
    for [linenum, line] in enumerate(body):
        if whitespace_re.match(line) or list_ele_re.match(line) or heading_re.match(line):
            print(line)
            continue

        m, scope, cur_scope_lv = update_scope_and_then(scope, cur_scope_lv, linenum, keyval_pair_re)

        if m:
            control_sequence = m.group(3)
            if control_sequence:
                print(do_eval_in_sub(scope, m))
            else:
                print(line)
        else:
            print(line)

    if malformed_storage:
        print()
        print("# MALFORMED STORAGE BU")
        print(''.join(storage))

    # WARNING: STORAGE must be the last section of the doc!!
    if len(cached_exps) > 0:
        print("# STORAGE", end = '\n\n')
        print(json.dumps(cached_exps))
