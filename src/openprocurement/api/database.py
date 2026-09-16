import os
import time
from contextlib import contextmanager
from decimal import Decimal
from logging import getLogger
from uuid import uuid4

from bson.codec_options import CodecOptions, TypeCodec, TypeRegistry
from bson.decimal128 import Decimal128
from bson.timestamp import Timestamp
from pymongo import (
    ASCENDING,
    DESCENDING,
    IndexModel,
    MongoClient,
    ReadPreference,
    ReturnDocument,
)
from pymongo.monitoring import CommandListener
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from openprocurement.api.context import get_db_session, get_request, get_request_now

LOGGER = getLogger("{}.init".format(__name__))


#  mongodb
class MongodbResourceConflict(Exception):
    """
    On doc update we pass _id and _rev as filter
    _rev can be changed by concurrent requests
    then update_one(or replace_one) doesn't find any document to update and returns matched_count = 0
    that causes MongodbResourceConflict that is shown to the User as 409 response code
    that means they have to retry his request
    """


class DecimalCodec(TypeCodec):
    python_type = Decimal  # the Python type acted upon by this type codec
    bson_type = Decimal128  # the BSON type acted upon by this type codec

    def transform_python(self, value):
        """Function that transforms a custom type value into a type
        that BSON can encode."""
        return Decimal128(value)

    def transform_bson(self, value):
        """Function that transforms a vanilla BSON type value into our
        custom type."""
        return value.to_decimal()


type_registry = TypeRegistry(
    [
        DecimalCodec(),
    ]
)
codec_options = CodecOptions(type_registry=type_registry)


# How many seconds behind the MongoDB cluster time the feed lags.
# Prevents race conditions where $$NOW (public_modified) is captured at
# operation start, not at commit time — concurrent writes can commit
# out-of-order and permanently disappear from the feed for crawlers.
# Must be greater than the maximum "$$NOW -> commit" delay of a write.
# The cutoff is computed from the cluster time (the clock of oplog timestamps),
# so neither the API server clock nor the replica clock is involved, and
# the feed read waits for the replica to catch up to that cluster time
# (see MongodbStore.get_feed_watermark).
# See: docs/source/developers/projects/cdb/feed_ordering.rst
FEED_WATERMARK_SECONDS = int(os.environ.get("FEED_WATERMARK_SECONDS", "1"))

# Upper bound for how long a feed read may block waiting for the replica
# (or the majority snapshot) to catch up to the watermark cluster time.
FEED_WATERMARK_MAX_TIME_MS = int(os.environ.get("FEED_WATERMARK_MAX_TIME_MS", "10000"))


def get_public_modified():
    public_modified = {"$divide": [{"$toLong": "$$NOW"}, 1000]}
    return public_modified


def get_public_ts():
    return "$$CLUSTER_TIME"


class MongoServerLoggingListener(CommandListener):
    @staticmethod
    def _format_mongo_server(connection_id):
        """Format (host, port) as 'host:port' for logging."""
        host, port = connection_id[0], connection_id[1]
        return f"{host}:{port}" if port is not None else str(host)

    @staticmethod
    def _mongo_settings(store):
        database = store.database
        return {
            "DB_NAME": database.name,
            "READ_PREFERENCE": database.read_preference.name,
            "WRITE_CONCERN": str(database.write_concern.document),
            "READ_CONCERN": database.read_concern.level,
        }

    @staticmethod
    def _replica_info_from_topology(store, connection_id):
        client = store.connection
        topo = client.topology_description
        sds = topo.server_descriptions()

        host, port = connection_id[0], connection_id[1]
        for addr, sdesc in sds.items():
            if addr[0] == host and addr[1] == port:
                out = {
                    "SERVER_TYPE": sdesc.server_type_name,
                    "RTT_SEC": sdesc.round_trip_time or sdesc.min_round_trip_time,
                }
                return out

        return {}

    def _update_logging_context(self, event):
        if event.connection_id is None:
            return

        request = get_request()
        if request is None:
            return

        params = {"SERVER": self._format_mongo_server(event.connection_id)}

        store = getattr(request.registry, "mongodb", None)
        if store:
            try:
                params.update(self._replica_info_from_topology(store, event.connection_id))
                params.update(self._mongo_settings(store))
            except (AttributeError, TypeError):
                LOGGER.warning("Failed to get mongo settings from store for logging context", exc_info=True)

        # pylint: disable-next=import-outside-toplevel
        from openprocurement.api.utils import update_logging_context

        update_logging_context(request, {"MONGO_LAST_COMMAND_INFO": params})

    def started(self, event):
        pass

    def succeeded(self, event):
        self._update_logging_context(event)

    def failed(self, event):
        self._update_logging_context(event)


class MongodbStore:
    def __init__(self, settings):
        self.settings = settings
        self.collections = {}

        db_name = os.environ.get("DB_NAME", settings["mongodb.db_name"])
        mongodb_uri = os.environ.get("MONGODB_URI", settings["mongodb.uri"])
        max_pool_size = int(os.environ.get("MONGODB_MAX_POOL_SIZE", settings["mongodb.max_pool_size"]))
        min_pool_size = int(os.environ.get("MONGODB_MIN_POOL_SIZE", settings["mongodb.min_pool_size"]))

        # https://docs.mongodb.com/manual/core/causal-consistency-read-write-concerns/#causal-consistency-and-read-and-write-concerns
        raw_read_preference = os.environ.get(
            "READ_PREFERENCE",
            settings.get("mongodb.read_preference", "SECONDARY_PREFERRED"),
        )
        raw_w_concert = os.environ.get("WRITE_CONCERN", settings.get("mongodb.write_concern", "majority"))
        raw_r_concern = os.environ.get("READ_CONCERN", settings.get("mongodb.read_concern", "majority"))
        self.connection = MongoClient(
            mongodb_uri,
            maxPoolSize=max_pool_size,
            minPoolSize=min_pool_size,
            event_listeners=[MongoServerLoggingListener()],
        )
        self.database = self.connection.get_database(
            db_name,
            read_preference=getattr(ReadPreference, raw_read_preference),
            write_concern=WriteConcern(w=int(raw_w_concert) if raw_w_concert.isnumeric() else raw_w_concert),
            read_concern=ReadConcern(level=raw_r_concern),
            codec_options=codec_options,
        )

    def __getattr__(self, name):
        """
        Used in code related to specific packages, like:
        >>> store = MongodbStore(settings)
        >>> store.add_collection("tenders", TenderCollection)
        >>> store.add_collection("plans", PlanCollection)
        >>> store.plans.get(uid)
        >>> store.tenders.save(doc)
        >>> store.tenders.count(filters)

        :param name: collection name
        :return: collection instance
        """
        if name in self.collections:
            return self.collections[name]
        raise AttributeError(f"MongodbStore has no attribute {name}")

    def add_collection(self, name, cls):
        self.collections[name] = cls(self, self.settings)

    def get_sequences_collection(self):
        return self.database.sequences

    def get_next_sequence_value(self, uid):
        collection = self.get_sequences_collection()
        result = collection.find_one_and_update(
            {"_id": uid},
            {"$inc": {"value": 1}},
            return_document=ReturnDocument.AFTER,
            upsert=True,
            session=get_db_session(),
        )
        return result["value"]

    def flush_sequences(self):
        collection = self.get_sequences_collection()
        self.flush(collection)

    @staticmethod
    def get_next_rev(current_rev=None):
        """
        This mimics couchdb _rev field
        that prevents concurrent updates
        :param current_rev:
        :return:
        """
        if current_rev:
            version, _ = current_rev.split("-")
            version = int(version)
        else:
            version = 1
        next_rev = f"{version + 1}-{uuid4().hex}"
        return next_rev

    @staticmethod
    def get(collection, uid):
        res = collection.find_one(
            {"_id": uid},
            projection={
                "is_public": False,
                "is_test": False,
            },
            session=get_db_session(),
        )
        return res

    def list(
        self,
        collection,
        fields,
        inclusive_filter: bool = False,
        offset_field="_id",
        offset_value=None,
        mode="all",
        descending=False,
        limit=0,
        filters=None,
    ):
        filters = filters or {}
        filters["is_public"] = True
        if mode == "test":
            filters["is_test"] = True
        elif mode != "_all_":
            filters["is_test"] = False
        if offset_value:
            suffix = "e" if inclusive_filter else ""
            operator = "$lt" if descending else "$gt"
            filters[offset_field] = {operator + suffix: offset_value}

        session = get_db_session()
        find_kwargs = {}
        if offset_field == "public_modified" and FEED_WATERMARK_SECONDS > 0 and (not descending or not offset_value):
            # Watermark: exclude records newer than FEED_WATERMARK_SECONDS
            # and make the read wait for the replica to catch up (see get_feed_watermark).
            # Skipped when FEED_WATERMARK_SECONDS=0 (e.g. in tests via monkeypatch).
            #
            # Applied to:
            #   - forward feed (not descending): always, to prevent crawlers from
            #     advancing past records that haven't committed yet.
            #   - descending feed WITHOUT offset (first page only): to guarantee that
            #     pm_max used as a forward-sync starting point is old enough that all
            #     concurrent writes with $$NOW <= pm_max have already committed.
            #     Without this, backward→forward sync can permanently miss records
            #     that were in-flight during the initial descending read.
            #   - descending WITH offset: skipped — paginating through historical data,
            #     no race condition possible for already-committed old records.
            watermark = self.get_feed_watermark(session)
            filters.setdefault(offset_field, {})["$lte"] = watermark
            find_kwargs["max_time_ms"] = FEED_WATERMARK_MAX_TIME_MS

        results = list(
            collection.find(
                filter=filters,
                projection={f: 1 for f in fields},
                limit=limit,
                sort=((offset_field, DESCENDING if descending else ASCENDING),),
                session=session,
                **find_kwargs,
            )
        )
        for e in results:
            self.rename_id(e)
        return results

    def get_cluster_time(self, session=None):
        """
        The newest MongoDB cluster time this process knows about ($clusterTime gossip):
        the logical clock the oplog timestamps are taken from.
        Falls back to a `ping` when nothing has been executed yet.
        Returns None for deployments without a logical clock (standalone server).
        """
        cluster_time = self.connection._topology.max_cluster_time()  # pylint: disable=protected-access
        if cluster_time is None:
            self.database.command("ping", session=session)
            cluster_time = self.connection._topology.max_cluster_time()  # pylint: disable=protected-access
        if cluster_time:
            return cluster_time["clusterTime"]
        return None

    def get_feed_watermark(self, session=None):
        """
        Returns the feed cutoff (unix seconds, int):
        only records with public_modified <= cutoff are exposed by the feed.

        The cutoff is derived from the MongoDB cluster time (the clock oplog timestamps
        come from), not from the wall clock of the API server or of the replica that
        serves the read. On top of that, the causally consistent session is asked to read
        after Timestamp(cluster_time_seconds, 0): a lagging secondary (or a lagging majority
        snapshot) then blocks until it has applied every write committed before that second,
        instead of answering from a stale snapshot. So the watermark stays a guarantee no
        matter how far behind the replica is: every write with public_modified <= cutoff
        that committed within FEED_WATERMARK_SECONDS is visible to this read.

        The cluster time is clamped by the API clock, so that a logical clock running ahead
        of the wall clock can't shrink the watermark.
        """
        now = int(time.time())
        cluster_time = self.get_cluster_time(session)
        if cluster_time is None:  # standalone: no replication, no lag
            return now - FEED_WATERMARK_SECONDS
        seconds = min(cluster_time.time, now)
        if session is not None:
            # afterClusterTime must not be greater than the cluster time of the node,
            # so it is always taken from a cluster time already seen by this client.
            session.advance_operation_time(Timestamp(seconds, 0))
        return seconds - FEED_WATERMARK_SECONDS

    def save_data(self, collection, data, insert=False, modified=True):
        uid = data.pop("id" if "id" in data else "_id")
        revision = data.pop("rev" if "rev" in data else "_rev", None)

        data["_id"] = uid
        data["_rev"] = self.get_next_rev(revision)
        data["is_public"] = data.get("status") not in ("draft", "deleted")
        data["is_test"] = data.get("mode") == "test"
        if "is_masked" in data and data.get("is_masked") is not True:
            data.pop("is_masked")

        pipeline = [
            {"$replaceWith": {"$literal": data}},
        ]
        if insert:
            data["dateCreated"] = get_request_now().isoformat()
        if modified:
            data["dateModified"] = get_request_now().isoformat()
            pipeline.append(
                {
                    "$set": {
                        "public_modified": get_public_modified(),
                        "public_ts": get_public_ts(),  # create items to migrate
                    }
                }
            )
        result = collection.find_one_and_update(
            {"_id": uid, "_rev": revision},
            pipeline,
            upsert=insert,
            session=get_db_session(),
        )
        if not result:
            if insert:
                pass  # it's fine, when upsert=True works and document is created it's not returned by default
            else:
                raise MongodbResourceConflict("Conflict while updating document. Please, retry")
        return data

    def save_data_simple(self, collection, data, insert=False):
        uid = data.pop("id" if "id" in data else "_id")
        data["_id"] = uid
        if insert:
            collection.insert_one(data)
        else:
            result = collection.replace_one(
                {"_id": uid},
                data,
                session=get_db_session(),
            )
            if result.matched_count == 0:
                raise MongodbResourceConflict("Unable to find the object")
        return data

    @staticmethod
    def flush(collection):
        result = collection.delete_many({})
        return result

    @staticmethod
    def delete(collection, uid):
        result = collection.delete_one({"_id": uid}, session=get_db_session())
        return result

    @staticmethod
    def rename_id(obj):
        if obj:
            obj["id"] = obj.pop("_id")
        return obj


class BaseCollection:
    object_name = "dummy"

    def __init__(self, store, settings):
        self.store = store
        collection_name = os.environ.get(
            f"{self.object_name.upper()}_COLLECTION",
            settings[f"mongodb.{self.object_name.lower()}_collection"],
        )
        self.collection = getattr(store.database, collection_name)
        if isinstance(self.collection.read_preference, type(ReadPreference.PRIMARY)):
            self.collection_primary = self.collection
        else:
            self.collection_primary = self.collection.with_options(read_preference=ReadPreference.PRIMARY)
        self.create_indexes()

    def get_indexes(self):
        public_modified_index = IndexModel(
            [
                ("public_modified", ASCENDING),
            ],
            name="public_modified",
        )
        real_by_public_modified_index = IndexModel(
            [
                ("public_modified", ASCENDING),
            ],
            name="real_by_public_modified",
            partialFilterExpression={
                "is_test": False,
                "is_public": True,
            },
        )
        test_by_public_modified_index = IndexModel(
            [
                ("public_modified", ASCENDING),
                ("existing_key", ASCENDING),
                # this hack key was used to allow index with the same fields
                # but different partial index filters
                # https://jira.mongodb.org/browse/SERVER-25023
                # this is not required anymore
                # but we keep it so we don't need to recreate the existing indexes
            ],
            name="test_by_public_modified",
            partialFilterExpression={
                "is_test": True,
                "is_public": True,
            },
        )
        all_by_public_modified_index = IndexModel(
            [
                ("public_modified", ASCENDING),
                ("surely_existing_key", ASCENDING),
                # this hack key was used to allow index with the same fields
                # but different partial index filters
                # https://jira.mongodb.org/browse/SERVER-25023
                # this is not required anymore
                # but we keep it so we don't need to recreate the existing indexes
            ],
            name="all_by_public_modified",
            partialFilterExpression={
                "is_public": True,
            },
        )
        return [
            public_modified_index,
            real_by_public_modified_index,
            test_by_public_modified_index,
            all_by_public_modified_index,
        ]

    def create_indexes(self):
        indexes = self.get_indexes()
        # self.collection.drop_indexes()
        # index management probably shouldn't be a part of api initialization
        # a command like `migrate_db` could be called once per release
        # that can manage indexes and data migrations
        # for now I leave it here
        self.collection.create_indexes(indexes)

    def save(self, o, insert=False, modified=True):
        data = o.to_primitive()
        updated = self.store.save_data(self.collection, data, insert=insert, modified=modified)
        o.import_data(updated)

    def get(self, uid):
        # if a client doesn't use SESSION cookie
        # reading from primary solves the issues
        # when write operation is allowed because of a state object from a secondary replica
        # This means more reads from Primary, but at the moment we can't force everybody to use the cookie
        # ! There is also the case, that internal services (like chronograph or tasks)
        # can read stale versions from secondaries !
        collection = (
            self.collection if getattr(get_request(), "method", None) in ("GET", "HEAD") else self.collection_primary
        )
        doc = self.store.get(collection, uid)
        return doc

    def list(self, **kwargs):
        result = self.store.list(self.collection, **kwargs)
        return result

    def flush(self):
        self.store.flush(self.collection)

    def delete(self, uid):
        result = self.store.delete(self.collection, uid)
        return result


@contextmanager
def atomic_transaction():
    s = get_db_session()
    database = get_request().registry.mongodb.database
    with s.start_transaction(
        # read_preference=database.read_preference,
        write_concern=database.write_concern,
        read_concern=database.read_concern,
    ):
        yield s
