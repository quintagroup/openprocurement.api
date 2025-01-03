# pylint: disable=wrong-import-position

if __name__ == "__main__":
    from gevent import monkey

    monkey.patch_all(thread=False, select=False)

import logging
import os

from pymongo.errors import OperationFailure
from pyramid.paster import bootstrap

from openprocurement.api.migrations.base import MigrationArgumentParser

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def has_items_populator(framework):
    return False


def run(env, args):
    migration_name = os.path.basename(__file__).split(".")[0]

    logger.info("Starting migration: %s", migration_name)

    collection = env["registry"].mongodb.frameworks.collection

    logger.info("Updating frameworks with hasItems field")

    log_every = 100000
    count = 0

    cursor = collection.find(
        {"config.hasItems": {"$exists": False}},
        {"config": 1},
        no_cursor_timeout=True,
    )
    cursor.batch_size(args.b)
    try:
        for framework in cursor:
            if framework.get("config", {}).get("hasItems") is None:
                try:
                    collection.update_one(
                        {"_id": framework["_id"]},
                        {"$set": {"config.hasItems": has_items_populator(framework)}},
                    )
                    count += 1
                    if count % log_every == 0:
                        logger.info(f"Updating frameworks with hasItems field: updated {count} frameworks")
                except OperationFailure as e:
                    logger.warning(f"Skip updating framework {framework['_id']}. Details: {e}")
    finally:
        cursor.close()

    logger.info(f"Updating frameworks with hasItems field finished: updated {count} frameworks")

    logger.info(f"Successful migration: {migration_name}")


if __name__ == "__main__":
    parser = MigrationArgumentParser()
    args = parser.parse_args()
    with bootstrap(args.p) as env:
        run(env, args)