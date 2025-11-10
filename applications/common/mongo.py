from django.conf import settings
from pymongo import MongoClient
from bson import ObjectId
from typing import Optional
import threading
import logging
import os


_client_lock = threading.Lock()
_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    """Return a process-wide MongoClient singleton (connection-pool, thread-safe).

    Best practice with PyMongo is to create one long-lived client and reuse it.
    """
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is None:
            uri = getattr(settings, 'MONGO_URI', None) or os.environ.get('MONGO_URI')
            if not uri:
                raise RuntimeError('MONGO_URI is not configured')
            # tlsAllowInvalidCertificates=True only if you use self-signed certs
            logging.getLogger(__name__).info('Initializing MongoClient for uri=%s', uri)
            _client = MongoClient(uri, tlsAllowInvalidCertificates=True)
    return _client  # type: ignore


def get_mongo_db(db_name: Optional[str] = None):
    if not db_name:
        db_name = getattr(settings, 'MONGO_DB', None) or os.environ.get('MONGO_DB')
    if not db_name:
        raise RuntimeError('MONGO_DB is not configured')
    logging.getLogger(__name__).debug('Selecting MongoDB database=%s', db_name)
    return get_mongo_client()[db_name]


def get_mongo_collection(collection: str, db_name: Optional[str] = None):
    logging.getLogger(__name__).debug('Selecting MongoDB collection=%s db=%s', collection, db_name or getattr(settings, 'MONGO_DB', None))
    return get_mongo_db(db_name)[collection]


def get_users_collection():
    coll = getattr(settings, 'MONGO_USERS_COLLECTION', None) or os.environ.get('MONGO_USERS_COLLECTION') or 'users'
    logging.getLogger(__name__).debug('Retrieving users collection=%s', coll)
    return get_mongo_collection(coll)


def to_plain(value):
    """Recursively convert BSON types (e.g., ObjectId) to JSON-serializable Python types."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {k: to_plain(v) for k, v in value.items() if k != '_id'} | ({'id': str(value.get('_id'))} if value.get('_id') is not None else {})
    if isinstance(value, list):
        return [to_plain(v) for v in value]
    return value


