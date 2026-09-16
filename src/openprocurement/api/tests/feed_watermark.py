import time
import unittest
from unittest.mock import MagicMock, patch

from bson.timestamp import Timestamp

import openprocurement.api.database as db_module
from openprocurement.api.context import set_db_session
from openprocurement.api.database import MongodbStore
from openprocurement.api.tests.base import BaseWebTest


class FeedWatermarkUnitTest(unittest.TestCase):
    def setUp(self):
        self.store = MongodbStore.__new__(MongodbStore)
        self.store.collections = {}
        self.store.connection = MagicMock()
        self.store.database = MagicMock()
        self.session = MagicMock()

    def set_cluster_time(self, cluster_time):
        self.store.connection._topology.max_cluster_time.return_value = (
            {"clusterTime": cluster_time} if cluster_time else None
        )

    @patch.object(db_module, "FEED_WATERMARK_SECONDS", 3)
    def test_cutoff_from_cluster_time(self):
        cluster_time = Timestamp(int(time.time()) - 5, 7)
        self.set_cluster_time(cluster_time)

        cutoff = self.store.get_feed_watermark(self.session)

        self.assertEqual(cutoff, cluster_time.time - 3)
        self.session.advance_operation_time.assert_called_once_with(Timestamp(cluster_time.time, 0))
        self.store.database.command.assert_not_called()

    @patch.object(db_module, "FEED_WATERMARK_SECONDS", 1)
    def test_cluster_time_ahead_of_wall_clock_is_clamped(self):
        now = int(time.time())
        self.set_cluster_time(Timestamp(now + 100, 1))

        cutoff = self.store.get_feed_watermark(self.session)

        self.assertLessEqual(cutoff, now - 1)
        self.assertGreaterEqual(cutoff, now - 2)  # the second may tick during the test
        operation_time = self.session.advance_operation_time.call_args[0][0]
        self.assertEqual(operation_time, Timestamp(cutoff + 1, 0))

    @patch.object(db_module, "FEED_WATERMARK_SECONDS", 1)
    def test_ping_when_cluster_time_unknown(self):
        cluster_time = Timestamp(int(time.time()) - 2, 1)
        self.store.connection._topology.max_cluster_time.side_effect = [None, {"clusterTime": cluster_time}]

        cutoff = self.store.get_feed_watermark(self.session)

        self.store.database.command.assert_called_once_with("ping", session=self.session)
        self.assertEqual(cutoff, cluster_time.time - 1)
        self.session.advance_operation_time.assert_called_once_with(Timestamp(cluster_time.time, 0))

    @patch.object(db_module, "FEED_WATERMARK_SECONDS", 1)
    def test_standalone_without_cluster_time(self):
        self.store.connection._topology.max_cluster_time.return_value = None

        before = int(time.time())
        cutoff = self.store.get_feed_watermark(self.session)

        self.store.database.command.assert_called_once_with("ping", session=self.session)
        self.assertGreaterEqual(cutoff, before - 1)
        self.session.advance_operation_time.assert_not_called()

    @patch.object(db_module, "FEED_WATERMARK_SECONDS", 1)
    def test_no_session(self):
        cluster_time = Timestamp(int(time.time()) - 2, 1)
        self.set_cluster_time(cluster_time)

        cutoff = self.store.get_feed_watermark(None)

        self.assertEqual(cutoff, cluster_time.time - 1)


class FeedWatermarkListTest(BaseWebTest):
    """
    list() against a real replica set:
    the watermark is a plain range on public_modified plus a causal read.
    """

    def setUp(self):
        super().setUp()
        self.collection = self.mongodb.tenders.collection
        self.now = time.time()
        self.collection.insert_many(
            [
                {"_id": "old", "is_public": True, "is_test": False, "public_modified": self.now - 60},
                {"_id": "fresh", "is_public": True, "is_test": False, "public_modified": self.now + 60},
            ]
        )

    def tearDown(self):
        set_db_session(None)
        super().tearDown()

    def list_ids(self, **kwargs):
        with self.mongodb.connection.start_session(causal_consistency=True) as session:
            set_db_session(session)
            self.advance_operation_time = MagicMock(wraps=session.advance_operation_time)
            with patch.object(session, "advance_operation_time", self.advance_operation_time):
                results = self.mongodb.list(self.collection, fields=["public_modified"], **kwargs)
        return [e["id"] for e in results]

    @patch.object(db_module, "FEED_WATERMARK_SECONDS", 1)
    def test_forward_feed_hides_fresh_records(self):
        self.assertEqual(self.list_ids(offset_field="public_modified"), ["old"])
        self.advance_operation_time.assert_called_once()
        operation_time = self.advance_operation_time.call_args[0][0]
        self.assertEqual(operation_time.inc, 0)
        self.assertLessEqual(operation_time.time, int(time.time()))
        self.assertGreaterEqual(operation_time.time, int(self.now) - 5)

        self.assertEqual(
            self.list_ids(offset_field="public_modified", offset_value=self.now - 120),
            ["old"],
        )
        self.assertEqual(
            self.list_ids(offset_field="public_modified", offset_value=self.now - 30),
            [],
        )

    @patch.object(db_module, "FEED_WATERMARK_SECONDS", 1)
    def test_descending_feed(self):
        # first page: watermark applied
        self.assertEqual(self.list_ids(offset_field="public_modified", descending=True), ["old"])
        # next pages: historical data, no watermark
        self.assertEqual(
            self.list_ids(offset_field="public_modified", descending=True, offset_value=self.now + 120),
            ["fresh", "old"],
        )

    @patch.object(db_module, "FEED_WATERMARK_SECONDS", 0)
    def test_disabled_watermark(self):
        self.assertEqual(self.list_ids(offset_field="public_modified"), ["old", "fresh"])
        self.advance_operation_time.assert_not_called()

    @patch.object(db_module, "FEED_WATERMARK_SECONDS", 1)
    def test_other_offset_fields_untouched(self):
        self.assertEqual(self.list_ids(offset_field="_id"), ["fresh", "old"])
        self.advance_operation_time.assert_not_called()
