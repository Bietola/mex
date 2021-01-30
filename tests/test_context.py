from mex.context import *


"""
subject:
    studied:
        total:$> { "example exp: "; sum(ctx.vtree('.', r'/^l\d+/$')) }
        l1: 10
        l2: 22
        l3: 22
        intruder: 1
"""
mock_env = {
    'subject': {
        'studied': {
            # total:$> { some exp }
            'total': Val.Nil(), 

            'l1': Val.Lit(10),
            'l2': Val.Lit(22),
            'l3': Val.Lit(3),
            'intruder': Val.Lit(1)
        }
    }
}

mock_ctx = Context(
    scope=['subject', 'studied'],
    cur_item='total',
    env=mock_env
)

#########
# Tests #
#########

def test_tree():
    result = mock_ctx.tree('.')

    # CICCIO: Turn numbers into Vals in mocks
    expected = {
        'l1': 10,
        'l2': 22,
        'l3': 3,
        'intruder': 1
    }

    assert result == expected

def test_vtree_numbers():
    assert mock_ctx.vtree('.') == [10, 22, 3, 1]

def test_vtree_mixed_types():
    ctx = Context(
        env = {
            'constant': Val.Lit(2),
            'test': Val.Lit('hello'),
            'test2': Val.Nil()
        },
        scope = [],
        cur_item = 'test2'
    )

    assert ctx.vtree('.') == [2, 'hello']
