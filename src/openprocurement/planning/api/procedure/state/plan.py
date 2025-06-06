from copy import deepcopy
from itertools import chain

from dateorro import calc_working_datetime

from openprocurement.api.constants import (
    KATOTTG_SCHEME,
    KPK_SCHEME,
    KPK_SCHEMES,
    KPKV_UK_SCHEME,
    TKPKMB_SCHEME,
)
from openprocurement.api.constants_env import (
    PLAN_ADDRESS_KIND_REQUIRED_FROM,
    RELEASE_SIMPLE_DEFENSE_FROM,
    UKRAINE_FACILITY_CLASSIFICATIONS_REQUIRED_FROM,
)
from openprocurement.api.context import get_request, get_request_now
from openprocurement.api.procedure.models.organization import ProcuringEntityKind
from openprocurement.api.procedure.state.base import BaseState
from openprocurement.api.procedure.utils import is_obj_const_active
from openprocurement.api.procedure.validation import (
    validate_items_classifications_prefixes,
)
from openprocurement.api.utils import error_handler, raise_operation_error
from openprocurement.planning.api.constants import (
    PROCEDURES,
    PROCURING_ENTITY_STANDSTILL,
)
from openprocurement.planning.api.procedure.models.milestone import Milestone
from openprocurement.tender.core.constants import FIRST_STAGE_PROCUREMENT_TYPES
from openprocurement.tender.pricequotation.constants import PQ
from openprocurement.tender.requestforproposal.constants import REQUEST_FOR_PROPOSAL


class PlanState(BaseState):
    def status_up(self, before, after, data):
        super().status_up(before, after, data)

    def always(self, data):
        super().always(data)

    def on_post(self, data):
        self.validate_on_post(data)
        self._switch_status({}, data)
        self._update_rationale_date(data)
        data["datePublished"] = get_request_now().isoformat()
        super().on_post(data)

    def on_patch(self, before, after):
        self.validate_on_patch(before, after)
        self._check_field_change_events(before, after)
        self._switch_status(before, after)
        self._update_rationale_date(after, before)
        super().on_patch(before, after)

    def _update_rationale_date(self, after, before=None):
        before = before or {}
        if "rationale" in after:
            if after["rationale"].get("description") != before.get("rationale", {}).get("description"):
                after["rationale"]["date"] = get_request_now().isoformat()
            else:
                after["rationale"]["date"] = before.get("rationale", {}).get("date", get_request_now().isoformat())

    def plan_tender_on_post(self, plan, tender):
        self.plan_tender_validate_on_post(plan, tender)

    def tender_plan_on_post(self, plan, tender):
        self.tender_plan_validate_on_post(plan, tender)
        plan["tender_id"] = tender["_id"]
        plan["status"] = "complete"

    def validate_on_post(self, data):
        self._validate_plan_availability(data)
        self._validate_tender_procurement_method_type(data)
        self._validate_items_classification_prefix(data)
        self.validate_required_breakdown_classifications(data)

    def validate_on_patch(self, before, after):
        self._validate_plan_changes_in_terminated(before, after)
        self._validate_plan_procurement_method_type_update(before, after)
        self._validate_plan_status_update(before, after)
        self._validate_plan_with_tender(before, after)
        self._validate_tender_procurement_method_type(after)
        self._validate_items_classification_prefix(after)
        self.validate_required_breakdown_classifications(after)

    def plan_tender_validate_on_post(self, plan, tender):
        self._validate_plan_scheduled(plan)
        self._validate_plan_has_not_tender(plan)
        self._validate_tender_data(tender)
        self._validate_tender_plan_procurement_method_type(tender, plan)
        self._validate_tender_matches_plan(tender, plan)
        self._validate_plan_budget_breakdown(plan)

    def tender_plan_validate_on_post(self, plan, tender):
        self._validate_procurement_kind_is_central(plan, tender)
        self._validate_tender_in_draft(plan, tender)
        self._validate_plan_not_terminated(plan)
        self._validate_plan_has_not_tender(plan)
        self._validate_plan_budget_breakdown(plan)
        self._validate_tender_data(tender)
        self._validate_tender_matches_plan(tender, plan)

    def _check_field_change_events(self, before, after):
        src_identifier = before["procuringEntity"]["identifier"]
        identifier = after["procuringEntity"]["identifier"]
        if src_identifier["scheme"] != identifier["scheme"] or src_identifier["id"] != identifier["id"]:
            if any(m["status"] in Milestone.ACTIVE_STATUSES for m in before.get("milestones", "")):
                standstill_end = calc_working_datetime(get_request_now(), PROCURING_ENTITY_STANDSTILL)
                if standstill_end.isoformat() > after["tender"]["tenderPeriod"]["startDate"]:
                    raise_operation_error(
                        self.request,
                        "Can't update procuringEntity later than {} "
                        "business days before tenderPeriod.StartDate".format(PROCURING_ENTITY_STANDSTILL.days),
                    )
                # invalidate active milestones and update milestone.dateModified
                for m in after["milestones"]:
                    if m["status"] in Milestone.ACTIVE_STATUSES:
                        m["status"] = Milestone.STATUS_INVALID
                        m["dateModified"] = get_request_now().isoformat()

    def _switch_status(self, before, after):
        if after.get("cancellation") and after["cancellation"]["status"] == "active":
            self.set_object_status(after, "cancelled", update_date=False)
        elif after.get("tender_id") is not None:
            self.set_object_status(after, "complete", update_date=False)

    def _validate_plan_availability(self, data):
        procurement_method_type = data.get("tender", {}).get("procurementMethodType", "")
        now = get_request_now()
        if (now >= RELEASE_SIMPLE_DEFENSE_FROM and procurement_method_type == "aboveThresholdUA.defense") or (
            now < RELEASE_SIMPLE_DEFENSE_FROM and procurement_method_type == "simple.defense"
        ):
            raise_operation_error(
                get_request(),
                "procedure with procurementMethodType = {} is not available".format(
                    procurement_method_type,
                ),
            )

    def _validate_tender_procurement_method_type(self, data):
        procedures = deepcopy(PROCEDURES)
        if get_request_now() >= PLAN_ADDRESS_KIND_REQUIRED_FROM:
            procedures[""] = ("centralizedProcurement",)
        procurement_method_types = list(chain(*procedures.values()))
        procurement_method_types_without_above_threshold_ua_defense = list(
            x for x in procurement_method_types if x not in ("aboveThresholdUA.defense", "simple.defense")
        )
        kind_allows_procurement_method_type_mapping = {
            ProcuringEntityKind.DEFENSE: procurement_method_types,
            ProcuringEntityKind.GENERAL: procurement_method_types_without_above_threshold_ua_defense,
            ProcuringEntityKind.SPECIAL: procurement_method_types_without_above_threshold_ua_defense,
            ProcuringEntityKind.CENTRAL: procurement_method_types_without_above_threshold_ua_defense,
            ProcuringEntityKind.AUTHORITY: procurement_method_types_without_above_threshold_ua_defense,
            ProcuringEntityKind.SOCIAL: procurement_method_types_without_above_threshold_ua_defense,
            ProcuringEntityKind.OTHER: ["belowThreshold", "reporting", "priceQuotation", REQUEST_FOR_PROPOSAL],
        }

        kind = data.get("procuringEntity", {}).get("kind", "")
        tender_procurement_method_type = data.get("tender", {}).get("procurementMethodType", "")
        allowed_procurement_method_types = kind_allows_procurement_method_type_mapping.get(kind)
        if allowed_procurement_method_types and get_request_now() >= PLAN_ADDRESS_KIND_REQUIRED_FROM:
            if tender_procurement_method_type not in allowed_procurement_method_types:
                request = get_request()
                request.errors.add(
                    "body",
                    "kind",
                    "procuringEntity with {kind} kind cannot publish this type of procedure. "
                    "Procurement method types allowed for this kind: {methods}.".format(
                        kind=kind, methods=", ".join(allowed_procurement_method_types)
                    ),
                )
                request.errors.status = 403

    def _validate_plan_not_terminated(self, before):
        status = before.get("status")
        if status in ("cancelled", "complete"):
            request = get_request()
            request.errors.add("body", "status", "Can't update plan in '{}' status".format(status))
            request.errors.status = 422
            raise error_handler(request)

    def _validate_plan_changes_in_terminated(self, before, after):
        status = before.get("status")
        allowed_keys = ("rationale",)
        if status in ("cancelled", "complete"):
            all_keys = set(before.keys()) | set(after.keys())
            keys_to_compare = all_keys - set(allowed_keys)

            for key in keys_to_compare:
                if before.get(key) != after.get(key):
                    raise_operation_error(
                        get_request(),
                        "Can't update {} in {} status".format(key, status),
                    )

    def _validate_plan_procurement_method_type_update(self, before, after):
        new_pmt = after.get("tender", {}).get("procurementMethodType", "")
        current_pmt = before["tender"]["procurementMethodType"]
        now = get_request_now()

        if current_pmt != new_pmt and (
            now < RELEASE_SIMPLE_DEFENSE_FROM
            and new_pmt == "simple.defense"
            or now > RELEASE_SIMPLE_DEFENSE_FROM
            and new_pmt == "aboveThresholdUA.defense"
        ):
            request = get_request()
            request.errors.add(
                "body",
                "tender",
                "Plan tender.procurementMethodType can not be changed from '{}' to '{}'".format(current_pmt, new_pmt),
            )
            request.errors.status = 422
            raise error_handler(request)

    def _validate_plan_status_update(self, before, after):
        status = before.get("status")
        if after.get("status") == "draft" and status != after.get("status"):
            request = get_request()
            request.errors.add("body", "status", "Plan status can not be changed back to 'draft'")
            request.errors.status = 422
            raise error_handler(request)

    def _validate_plan_with_tender(self, before, after):
        # we need this because of the plans created before the statuses release
        if before.get("tender_id") and not before.get("status"):
            names = []
            if before.get("procuringEntity") != after.get("procuringEntity"):
                names.append("procuringEntity")
            before_breakdown = before.get("budget", {}).get("breakdown")
            after_breakdown = after.get("budget", {}).get("breakdown")
            if before_breakdown != after_breakdown:
                names.append("budget.breakdown")
            request = get_request()
            for name in names:
                request.errors.add(
                    "body",
                    name,
                    "Changing this field is not allowed after tender creation",
                )
            if request.errors:
                request.errors.status = 422
                raise error_handler(request)

    def _validate_plan_scheduled(self, plan):
        status = plan.get("status")
        if status and status != "scheduled":
            request = get_request()
            request.errors.add(
                "body",
                "status",
                "Can't create tender in '{}' plan status".format(status),
            )
            request.errors.status = 422
            raise error_handler(request)

    def _validate_plan_has_not_tender(self, plan):
        if plan.get("tender_id"):
            request = get_request()
            request.errors.add("body", "tender_id", "This plan has already got a tender")
            request.errors.status = 422
            raise error_handler(request)

    def _validate_tender_data(self, tender):
        tender_type = tender.get("procurementMethodType")
        if tender_type not in FIRST_STAGE_PROCUREMENT_TYPES:
            request = get_request()
            request.errors.add(
                "body",
                "procurementMethodType",
                "Should be one of the first stage values: {}".format(
                    FIRST_STAGE_PROCUREMENT_TYPES,
                ),
            )
            request.errors.status = 403
            raise error_handler(request)

    def _validate_tender_plan_procurement_method_type(self, tender, plan):
        tender_type = tender.get("procurementMethodType")
        plan_type = plan["tender"]["procurementMethodType"]
        if plan_type not in (tender_type, "centralizedProcurement"):
            if tender_type == PQ and plan_type == "belowThreshold":
                return
            request = get_request()
            request.errors.add(
                "body",
                "procurementMethodType",
                "procurementMethodType doesn't match: {} != {}".format(plan_type, tender_type),
            )
            request.errors.status = 422
            raise error_handler(request)

    def _validate_tender_matches_plan(self, tender, plan):
        request = get_request()
        plan_identifier = plan["procuringEntity"]["identifier"]
        tender_identifier = tender.get("procuringEntity", {}).get("identifier", {})

        if plan["tender"]["procurementMethodType"] == "centralizedProcurement" and plan_identifier["id"] == "01101100":
            plan_identifier = plan["buyers"][0]["identifier"]

        if plan_identifier["id"] != tender_identifier.get("id") or plan_identifier["scheme"] != tender_identifier.get(
            "scheme"
        ):
            request.errors.add(
                "body",
                "procuringEntity",
                "procuringEntity.identifier doesn't match: {} {} != {} {}".format(
                    plan_identifier["scheme"],
                    plan_identifier["id"],
                    tender_identifier["scheme"],
                    tender_identifier["id"],
                ),
            )

        if request.errors:
            request.errors.status = 422
            raise error_handler(request)

        classifications = [
            item["classification"]
            for item in tender.get("items", "")
            if item.get("classification")  # item.classification may be empty in pricequotation
        ]
        if classifications:
            validate_items_classifications_prefixes(
                classifications,
                root_classification=plan["classification"],
                root_name="plan",
            )

    def _validate_plan_budget_breakdown(self, plan):
        budget = plan.get("budget")
        if not budget or not budget.get("breakdown"):
            request = get_request()
            request.errors.add("body", "budget.breakdown", "Plan should contain budget breakdown")
            request.errors.status = 422
            raise error_handler(request)

    def _validate_procurement_kind_is_central(self, plan, tender):
        if tender["procuringEntity"]["kind"] != ProcuringEntityKind.CENTRAL:
            raise raise_operation_error(
                self.request,
                "Only allowed for procurementEntity.kind = '{}'".format(ProcuringEntityKind.CENTRAL),
            )

    def _validate_tender_in_draft(self, plan, tender):
        if tender["status"] != "draft":
            raise raise_operation_error(self.request, "Only allowed in draft tender status")

    def _validate_items_classification_prefix(self, plan):
        classifications = [item["classification"] for item in plan.get("items", [])]
        if not classifications:
            return
        validate_items_classifications_prefixes(classifications)
        validate_items_classifications_prefixes(
            classifications,
            root_classification=plan["classification"],
        )

    def validate_required_breakdown_classifications(self, plan):
        if not is_obj_const_active(plan, UKRAINE_FACILITY_CLASSIFICATIONS_REQUIRED_FROM):
            return
        if plan.get("budget") and plan["budget"].get("breakdown"):
            for breakdown in plan["budget"]["breakdown"]:
                classification = breakdown.get("classification", {})
                if breakdown.get("title") == "state" and not any(
                    classification.get("scheme") == kpk_scheme for kpk_scheme in KPK_SCHEMES
                ):
                    raise_operation_error(
                        self.request,
                        f"{KPK_SCHEME} is required for {breakdown['title']} budget.",
                        status=422,
                        name="budget.breakdown.classification",
                    )
                elif breakdown.get("title") in ("local", "crimea"):
                    if classification.get("scheme") != TKPKMB_SCHEME:
                        raise_operation_error(
                            self.request,
                            f"{TKPKMB_SCHEME} is required for {breakdown['title']} budget.",
                            status=422,
                            name="budget.breakdown.classification",
                        )
                    elif not breakdown.get("address", {}):
                        raise_operation_error(
                            self.request,
                            f"Address is required for {breakdown['title']} budget.",
                            status=422,
                            name="budget.breakdown.address",
                        )
                    elif breakdown.get("address", {}).get("countryName") == "Україна" and not any(
                        detail.get("scheme") == KATOTTG_SCHEME
                        for detail in breakdown.get("address", {}).get("addressDetails", [])
                    ):
                        raise_operation_error(
                            self.request,
                            f"{KATOTTG_SCHEME} is required for {breakdown['title']} budget.",
                            status=422,
                            name="budget.breakdown.address.addressDetails",
                        )
        if any(
            classification["scheme"] == KPKV_UK_SCHEME for classification in plan.get("additionalClassifications", [])
        ):
            raise_operation_error(
                self.request,
                f"Forbidden to add {KPKV_UK_SCHEME}. Should be added in budget.breakdown.classification.",
                status=422,
                name="additionalClassifications",
            )
