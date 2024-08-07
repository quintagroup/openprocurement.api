from openprocurement.api.procedure.serializers.base import ListSerializer
from openprocurement.tender.core.procedure.serializers.bid import (
    BidSerializer as BaseBidSerializer,
)
from openprocurement.tender.core.procedure.serializers.document import (
    DocumentSerializer,
)
from openprocurement.tender.core.procedure.serializers.parameter import (
    ParameterSerializer,
)
from openprocurement.tender.esco.procedure.serializers.lot_value import (
    LotValueSerializer,
)
from openprocurement.tender.esco.procedure.serializers.value import ValueSerializer


class BidSerializer(BaseBidSerializer):
    serializers = {
        "value": ValueSerializer,
        "lotValues": ListSerializer(LotValueSerializer),
        "documents": ListSerializer(DocumentSerializer),
        "eligibilityDocuments": ListSerializer(DocumentSerializer),
        "qualificationDocuments": ListSerializer(DocumentSerializer),
        "financialDocuments": ListSerializer(DocumentSerializer),
        "parameters": ListSerializer(ParameterSerializer),
    }
