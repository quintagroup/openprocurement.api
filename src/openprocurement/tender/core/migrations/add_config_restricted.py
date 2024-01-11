from gevent import monkey

if __name__ == "__main__":
    monkey.patch_all(thread=False, select=False)

import os
import argparse
import logging

from pyramid.paster import bootstrap

from openprocurement.api.constants import BASE_DIR

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def restricted_populator(tender):
    return False


def run(env, args):
    migration_name = os.path.basename(__file__).split(".")[0]

    logger.info("Starting migration: %s", migration_name)

    collection = env["registry"].mongodb.tenders.collection

    logger.info("Updating tenders with restricted field")

    log_every = 100000
    count = 0

    cursor = collection.find(
        {"config.restricted": {"$exists": False}},
        {"config": 1, "procurementMethodType": 1, "is_masked": 1},
        no_cursor_timeout=True,
    )
    cursor.batch_size(args.b)
    try:
        for tender in cursor:
            if tender.get("config", {}).get("restricted") is None:
                collection.update_one(
                    {"_id": tender["_id"]},
                    {"$set": {"config.restricted": restricted_populator(tender)}}
                )
                count += 1
                if count % log_every == 0:
                    logger.info(f"Updating tenders with restricted field: updated {count} tenders")
    finally:
        cursor.close()

    logger.info(f"Updating tenders with restricted field finished: updated {count} tenders")

    logger.info(f"Successful migration: {migration_name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p",
        default=os.path.join(BASE_DIR, "etc/service.ini"),
        help="Path to service.ini file",
    )
    parser.add_argument(
        "-b",
        type=int,
        default=1000,
        help=(
            "Limits the number of documents returned in one batch. Each batch "
            "requires a round trip to the server."
        )
    )
    args = parser.parse_args()
    with bootstrap(args.p) as env:
        run(env, args)
