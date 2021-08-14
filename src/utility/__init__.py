import functools
import flask

def url_arg_required(arg=""):
    """
    Used after a flask `app.route` decorator. Requires that the arg is in the url parameters of the request
    :param arg: The arg to look for
    """
    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            if arg not in flask.request.args.keys():
                return {"error": "missing url argument '{}'".format(arg)}, 400
            return func(*args, **kwargs)
        return inner
    return decorator