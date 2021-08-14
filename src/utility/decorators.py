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

def file_key_required(file_key=""):
    """
    Used after a flask `app.route` decorator. Requires that the file_key is one of the uploaded file keys
    :param file_key: The file key to look for
    """
    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            if file_key not in flask.request.files.keys():
                return {"error": "missing file parameter {}".format(file_key)}, 400
            return func(*args, **kwargs)
        return inner
    return decorator