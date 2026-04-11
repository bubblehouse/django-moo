# pylint: disable=undefined-variable
sys = lookup(1)

# LambdaMOO special sentinel references (mirrors $nothing, $ambiguous_match, $failed_match)
sys.set_property("nothing", lookup("nothing"))
sys.set_property("ambiguous_match", lookup("ambiguous_match"))
sys.set_property("failed_match", lookup("failed_match"))
