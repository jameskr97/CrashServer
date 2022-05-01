#!/usr/bin/env python
from rq import Connection, Worker
from redis import Redis

from crashserver.server import create_app
from crashserver.server.models import Storage

if __name__ == "__main__":
    app = create_app()
    with app.app_context(), Connection(Redis("redis")):
        Storage.load_storage_modules()
        Storage.init_targets()
        Worker("crashserver").work()
