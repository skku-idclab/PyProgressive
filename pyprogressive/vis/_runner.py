import inspect


def _make_callback(n_vars, update_fn):
    """
    Create a callback with exactly (n_vars + 1) parameters so that
    Program.run() passes elapsed as the last argument.

    Setting __signature__ lets inspect.signature() see the right parameter
    count while the real implementation still uses *args.
    """
    params = [
        inspect.Parameter(f"_v{i}", inspect.Parameter.POSITIONAL_OR_KEYWORD)
        for i in range(n_vars)
    ]
    params.append(
        inspect.Parameter("_elapsed", inspect.Parameter.POSITIONAL_OR_KEYWORD)
    )

    def _cb(*args):
        elapsed_obj = args[-1]
        values = args[:-1]
        update_fn(elapsed_obj.elapsed(), elapsed_obj.done, *values)

    _cb.__signature__ = inspect.Signature(params)
    return _cb


