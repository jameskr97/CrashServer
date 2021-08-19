import functools

import flask

from src.webapp.models import Project
from src.webapp import db


def api_key_required(url_arg_key="api_key", pass_project=True):
    """
    Requires that the `api_key` url argument has been included in request.
    Queries the database for a matching api_key, and passes the project in as the first parameter
    Used after a flask `app.route` decorator.
    :arg url_arg_key The url argument to require. Typically url_arg_key though different for symupload
    :arg pass_project True if the project_id queried from the database should be passed into the decorated function
    :return:
    """
    def decorator(func):
        @functools.wraps(func)
        def action(*args, **kwargs):
            # Ensure arg exists
            if url_arg_key not in flask.request.args.keys():
                return {"error": "Endpoint requires %s" % url_arg_key}, 400

            # Get the project
            res = db.session.query(Project.id).filter_by(api_key=flask.request.args[url_arg_key]).scalar()
            if res is None:
                return {"error": "Bad %s" % url_arg_key}, 400

            if pass_project:
                return func(res, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        return action
    return decorator

def url_arg_required(arg=""):
    """
    Used after a flask `app.route` decorator. Requires that the arg is in the url parameters of the request
    :param arg: The arg to look for
    """
    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            if arg not in flask.request.args.keys():
                return {"error": "missing url argument {}".format(arg)}, 400
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
