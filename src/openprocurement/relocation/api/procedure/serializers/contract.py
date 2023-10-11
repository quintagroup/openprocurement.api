from openprocurement.tender.core.procedure.serializers.base import BaseUIDSerializer


class TransferredContractSerializer(BaseUIDSerializer):
    whitelist = {
        "_id",
        "owner",
    }
    serializers = {}
