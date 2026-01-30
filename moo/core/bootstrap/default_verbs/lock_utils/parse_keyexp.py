#!moo verb parse_keyexp --on $lock_utils

# pylint: disable=return-outside-function,undefined-variable

"""
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

This verb parses the string `keyexp` and returns the internal representation of the expression, for use with
`$lock_utils.eval_key`. It is used, for example, by the verb `$player:@lock` to parse the text given by a player into a
key expression to store on the `.key` property of an object.
"""

keyexp = args[0]

# Example 1: from docs
# keyexp = "#45 && ?#46 && (#47 || !#48)"
# result = ["&&", ["&&", 45, ["?", 46]], ["||", 47, ["!", 48]]]

# Example 2: simple object number
# keyexp = "#123"
# result = 123

# Example 3: two objects
# keyexp = "#12 || #34"
# result = ["||", 12, 34]

# Example 4: negation
# keyexp = "!#56"
# result = ["!", 56]

def parse_expression(expr):
    expr = expr.strip("() ").strip()
    if "&&" in expr:
        # AND operation
        left, right = expr.rsplit("&&", 1)
        return ["&&", parse_expression(left), parse_expression(right)]
    elif "||" in expr:
        # OR operation
        left, right = expr.rsplit("||", 1)
        return ["||", parse_expression(left), parse_expression(right)]
    elif expr.startswith("#"):
        # Simple object number
        return int(expr[1:])
    elif expr.startswith("!"):
        # Negation
        operand = expr[1:].strip()
        return ["!", parse_expression(operand)]
    elif expr.startswith("?"):
        # Question operation
        obj_num = expr[1:].strip()
        return ["?", int(obj_num[1:])]  # Assuming format is ?#num
    else:
        raise ValueError("Invalid key expression format: %s" % expr)

return parse_expression(keyexp)
