import logging
import os

from openprocurement.api.migrations.base import BaseMigration, migrate
from openprocurement.tender.cfaua.constants import CFA_UA
from openprocurement.tender.competitivedialogue.constants import (
    CD_EU_TYPE,
    CD_UA_TYPE,
    STAGE_2_EU_TYPE,
)
from openprocurement.tender.esco.constants import ESCO
from openprocurement.tender.openeu.constants import ABOVE_THRESHOLD_EU

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def qualification_complain_duration_populator(tender):
    pmt = tender.get("procurementMethodType")
    if pmt in [ABOVE_THRESHOLD_EU, CD_UA_TYPE, CD_EU_TYPE, STAGE_2_EU_TYPE, ESCO, CFA_UA]:
        return 5
    return 0


def run(env, args):
    """Run the migration.

    :param env: WSGI environment
    :param args: command line arguments
    :return: None
    """

    migration_name = os.path.basename(__file__).split(".")[0]

    logger.info("Starting migration: %s", migration_name)

    collection = env["registry"].mongodb.tenders.collection

    logger.info("Updating tenders with qualificationComplainDuration field")

    log_every = 100000
    count = 0

    cursor = collection.find(
        {
            "config.qualificationComplainDuration": {"$exists": False},
        },
        {"config": 1, "procurementMethodType": 1},
        no_cursor_timeout=True,
    )
    cursor.batch_size(args.b)
    try:
        for tender in cursor:
            if tender.get("config", {}).get("qualificationComplainDuration") is None:
                collection.update_one(
                    {"_id": tender["_id"]},
                    {
                        "$set": {
                            "config.qualificationComplainDuration": qualification_complain_duration_populator(tender)
                        }
                    },
                )
                count += 1
                if count % log_every == 0:
                    logger.info(f"Updating tenders with qualificationComplainDuration field: updated {count} tenders")
    finally:
        cursor.close()

    logger.info(f"Updating tenders with qualificationComplainDuration field finished: updated {count} tenders")

    logger.info(f"Successful migration: {migration_name}")


class Migration(BaseMigration):
    def run(self):
        run(self.env, self.args)


if __name__ == "__main__":
    migrate(Migration)
