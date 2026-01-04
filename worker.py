import os
from redis import Redis
from rq import Worker, Queue, Connection
from app.settings import REDIS_URL
from app.db import init_db

def redis_from_url(url: str) -> Redis:
    import urllib.parse
    u = urllib.parse.urlparse(url)
    db = int((u.path or "/0").replace("/", "") or "0")
    
    # Check if using SSL (rediss://)
    use_ssl = u.scheme == "rediss"
    
    return Redis(
        host=u.hostname or "localhost",
        port=u.port or 6379,
        db=db,
        password=u.password,
        ssl=use_ssl,
        ssl_cert_reqs=None if use_ssl else None
    )

if __name__ == "__main__":
    init_db()
    redis_conn = redis_from_url(REDIS_URL)
    with Connection(redis_conn):
        worker = Worker([Queue("pob")])
        worker.work()
