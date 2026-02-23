#!moo verb eval_key --on $lock_utils

# pylint: disable=return-outside-function,undefined-variable

"""
This verb evaluates the key expression `key`, in the context of the candidate object `who`. It returns `True` if the
key will allow who to pass, otherwise it returns `False`. The simple examples below are intended to show the ways in
which this verb can be invoked:

    Verb Call                                      Returned
    ---------                                      --------
    .eval_key(lookup(35), lookup(35))              1
    .eval_key({"!", lookup(35)], lookup(35))       0
    .eval_key({"!", lookup(35)], lookup(123))      1

The key expression is given as a list, in the format described below:

Objects are represented by their object numbers and all other kinds of key expressions are represented by lists. These
lists have as their first element a string drawn from the following set:

    "&&"     "||"     "!"     "?"

For the first two of these, the list should be three elements long; the second and third elements are the
representations of the key expressions on the left- and right-hand sides of the appropriate operator. In the third
case, `!', the list should be two elements long; the second element is again a representation of the operand. Finally,
in the `?' case, the list is also two elements long but the second element must be an object number.

As an example, the key expression

    #45  &&  ?#46  &&  (#47  ||  !#48)

would be represented as follows:

    ["&&", ["&&", #45, ["?", #46]], ["||", #47, ["!", #48]]]
"""

from moo.core import lookup

key, who = args

def eval_key_expression(expr, candidate):
    if isinstance(expr, int):
        subject = lookup(expr)
        return subject == candidate or candidate.contains(subject)
    elif isinstance(expr, list):
        operator = expr[0]
        if operator == "&&":
            left = eval_key_expression(expr[1], candidate)
            right = eval_key_expression(expr[2], candidate)
            return left and right
        elif operator == "||":
            left = eval_key_expression(expr[1], candidate)
            right = eval_key_expression(expr[2], candidate)
            return left or right
        elif operator == "!":
            operand = eval_key_expression(expr[1], candidate)
            return not operand
        elif operator == "?":
            obj = lookup(expr[1])
            return eval_key_expression(obj.key, candidate)
    return False

return eval_key_expression(key, who)
