from mex.utils import *

def test_remove_common_prefix():
    result = tuple(map(
        list,
        remove_common_prefix(
            ['hello', 'there'],
            ['hello', 'here']
        )
    ))

    assert (['there'], ['here']) == result
