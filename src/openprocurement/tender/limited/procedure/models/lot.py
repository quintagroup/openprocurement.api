from schematics.types import StringType
from schematics.types.compound import ModelType
from schematics.types.serializable import serializable

from openprocurement.tender.core.procedure.models.guarantee import PostValue, Value
from openprocurement.tender.core.procedure.models.lot import (
    BaseLot,
    BaseLotSerializersMixin,
)
from openprocurement.tender.core.procedure.models.lot import PatchLot as BasePatchLot
from openprocurement.tender.core.procedure.models.lot import (
    PatchTenderLot as BasePatchTenderLot,
)
from openprocurement.tender.core.procedure.models.lot import PostBaseLot, TenderLotMixin


class LotValueSerializerMixin(BaseLotSerializersMixin):
    @serializable(serialized_name="value", type=ModelType(Value))
    def lot_value(self):
        tender = self.get_tender()
        return Value(
            {
                "amount": self.value.amount,
                "currency": tender["value"]["currency"],
                "valueAddedTaxIncluded": tender["value"]["valueAddedTaxIncluded"],
            }
        )


class PostLot(PostBaseLot, LotValueSerializerMixin):
    value = ModelType(PostValue, required=True)


class PatchLot(BasePatchLot):
    title = StringType()
    value = ModelType(Value)


class PostTenderLot(PostLot, TenderLotMixin):
    pass


class PatchTenderLot(BasePatchTenderLot, TenderLotMixin):
    value = ModelType(Value, required=True)


class Lot(BaseLot, TenderLotMixin, LotValueSerializerMixin):
    value = ModelType(Value, required=True)
