from logging import getLogger
from itertools import zip_longest
from decimal import Decimal, ROUND_FLOOR

from openprocurement.api.context import get_request
from openprocurement.tender.core.procedure.state.base import BaseState
from openprocurement.tender.core.procedure.state.contract import ContractStateMixing
from openprocurement.api.utils import raise_operation_error, to_decimal

LOGGER = getLogger(__name__)


class BaseContractState(BaseState, ContractStateMixing):
    terminated_statuses = ("terminated",)

    def always(self, data) -> None:
        super().always(data)

    def on_patch(self, before, after) -> None:
        self.validate_contract_patch(self.request, before, after)
        if after.get("value"):
            self.synchronize_items_unit_value(after)
        super().on_patch(before, after)

    def validate_contract_patch(self, request, before: dict, after: dict):
        self.validate_patch_contract_items(request, before, after)
        self.validate_update_contracting_items_unit_value_amount(request, before, after)
        self.validate_update_contract_value_net_required(request, before, after)
        self.validate_update_contract_value_net_required(request, before, after, name="amountPaid")
        self.validate_update_contract_value(request, before, after)
        self.validate_update_contracting_value_identical(request, before, after)
        self.validate_update_contract_value_amount(request, before, after)
        self.validate_update_contract_paid_amount(request, before, after)
        self.validate_update_contract_value_net_required(request, before, after)
        self.validate_terminate_contract_without_amountPaid(request, before, after)

    def validate_patch_contract_items(self, request, before: dict, after: dict) -> None:
        # TODO: Remove this logic later with adding new endpoint for items in contract

        after_status = after["status"]
        if after_status == "active":
            item_patch_fields = (
                "description",
                "description_en",
                "description_ru",
                "unit",
                "deliveryDate",
                "deliveryAddress",
                "deliveryLocation",
                "quantity",
            )
        else:
            item_patch_fields = ("unit.value.amount",)
        items_before = before.get("items", [])
        items_after = after.get("items", [])
        for item_before, item_after in zip_longest(items_before, items_after):
            if None in (item_before, item_after):
                raise_operation_error(
                    get_request(),
                    "Can't change items list length"
                )
            else:
                for k in item_before.keys() | item_after.keys():

                    before, after = item_before.get(k), item_after.get(k)
                    if not before and not after:  # [] or None check
                        continue

                    if k == "unit" and "unit.value.amount" in item_patch_fields:
                        before = {k: v for k, v in (before or {}).items() if k != "value"}
                        after = {k: v for k, v in (after or {}).items() if k != "value"}

                    if k not in item_patch_fields and before != after:
                        raise_operation_error(
                            get_request(),
                            f"Updated could be only {item_patch_fields} in item"
                        )

    def validate_update_contracting_items_unit_value_amount(self, request, before, after) -> None:
        if after.get("items"):
            self._validate_contract_items_unit_value_amount(after)

    def _validate_contract_items_unit_value_amount(self, contract: dict) -> None:
        items_unit_value_amount = []
        for item in contract.get("items", ""):
            if item.get("unit") and item.get("quantity") is not None:
                if item["unit"].get("value"):
                    if item["quantity"] == 0 and item["unit"]["value"]["amount"] != 0:
                        raise_operation_error(
                            get_request(), "Item.unit.value.amount should be updated to 0 if item.quantity equal to 0"
                        )
                    items_unit_value_amount.append(
                        to_decimal(item["quantity"]) * to_decimal(item["unit"]["value"]["amount"])
                    )

        if items_unit_value_amount and contract.get("value"):
            calculated_value = sum(items_unit_value_amount)

            if calculated_value.quantize(Decimal("1E-2"), rounding=ROUND_FLOOR) > to_decimal(
                    contract["value"]["amount"]):
                raise_operation_error(
                    get_request(), "Total amount of unit values can't be greater than contract.value.amount"
                )

    @staticmethod
    def validate_update_contracting_value_identical(request, before,  after):
        value = after.get("value")
        paid_data = request.validated["json_data"].get("amountPaid")
        for attr in ("currency",):
            if value and paid_data and paid_data.get(attr) is not None:
                if value.get(attr) != paid_data.get(attr):
                    raise_operation_error(
                        request,
                        f"{attr} of amountPaid should be identical to {attr} of value of contract",
                        name="amountPaid",
                    )

    def validate_update_contract_paid_amount(self, request, before, after):
        value = after.get("value")
        paid = after.get("amountPaid")
        if not paid:
            return
        self.validate_update_contract_value_amount(request, before, after, name="amountPaid")
        if not value:
            return
        attr = "amountNet"
        paid_amount = paid.get(attr)
        value_amount = value.get(attr)
        if value_amount and paid_amount > value_amount:
            raise_operation_error(
                request,
                f"AmountPaid {attr} can`t be greater than value {attr}",
                name="amountPaid",
            )
    @staticmethod
    def validate_terminate_contract_without_amountPaid(request, before, after):
        if after.get("status", "active") == "terminated" and not after.get("amountPaid"):
            raise_operation_error(request, "Can't terminate contract while 'amountPaid' is not set")
