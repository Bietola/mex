import sys
import itertools

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def remove_common_prefix(lhs, rhs):
    return map(
        lambda x: itertools.takewhile(lambda y: y, x),
        zip(
            *itertools.dropwhile(
                lambda p: p[0] == p[1],
                itertools.zip_longest(lhs, rhs)
            )
        )
    )
