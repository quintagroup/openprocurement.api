from openprocurement.api.utils import raise_operation_error, handle_data_exceptions, error_handler, context_unpack
from openprocurement.api.constants import (
    RELEASE_2020_04_19,
    CRITERION_REQUIREMENT_STATUSES_FROM,
    RELEASE_GUARANTEE_CRITERION_FROM,
    GUARANTEE_ALLOWED_TENDER_TYPES,
    RELEASE_ECRITERIA_ARTICLE_17,
)
from openprocurement.api.validation import (
    validate_json_data,
    _validate_accreditation_level,
    _validate_accreditation_level_mode,
    OPERATIONS,
)
from openprocurement.tender.core.validation import TYPEMAP
from openprocurement.tender.core.procedure.utils import (
    is_item_owner,
    apply_data_patch,
    delete_nones,
    get_first_revision_date,
)
from openprocurement.tender.core.procedure.documents import check_document_batch, check_document, update_document_url
from openprocurement.tender.core.procedure.context import get_now, get_tender, get_request
from openprocurement.tender.core.procedure.state.tender_document import get_tender_document_role
from schematics.exceptions import ValidationError
from pyramid.httpexceptions import HTTPError
from copy import deepcopy
from decimal import Decimal
import logging


LOGGER = logging.getLogger(__name__)


def validate_input_data(input_model, allow_bulk=False, filters=None, none_means_remove=False):
    """
    :param input_model: a model to validate data against
    :param allow_bulk: if True, request.validated["data"] will be a list of valid inputs
    :param filters: list of filter function that applied on valid data
    :param none_means_remove: null values passed cause deleting saved values at those keys
    :return:
    """
    def validate(request, **_):
        request.validated["json_data"] = json_data = validate_json_data(request, allow_bulk=allow_bulk)
        # now you can use context.get_json_data() in model validators to access the whole passed object
        # instead of .__parent__.__parent__. Though it may not be valid
        if not isinstance(json_data, list):
            json_data = [json_data]

        data = []
        for input_data in json_data:
            result = {}
            if none_means_remove:
                # if None is passed it should be added to the result
                # None means that the field value is deleted
                # IMPORTANT: input_data can contain more fields than are allowed to update
                # validate_data will raise Rogue field error then
                # Update: doesn't work with sub-models {'auctionPeriod': {'startDate': None}}
                for k, v in input_data.items():
                    if (
                        v is None
                        or isinstance(v, list) and len(v) == 0  # for list fields, an empty list does the same
                    ):
                        result[k] = v

            valid_data = validate_data(request, input_model, input_data)
            if valid_data is not None:
                result.update(valid_data)
            data.append(result)

        if filters:
            data = [f(request, d) for f in filters for d in data]
        request.validated["data"] = data if allow_bulk else data[0]
        return request.validated["data"]

    return validate


def validate_patch_data(model, item_name):
    """
    Because api supports questionable requests like
    PATCH /bids/uid {"parameters": [{}, {}, {"code": "new_code"}]}
    where {}, {} and {"code": "new_code"} are invalid parameters and can't be validated.
    We have to have this validator that
    1) Validate requests data against simple patch model
    (use validator validate_input_data(PatchModel) before this one)
    2) Apply the patch on the saved data  (covered by this validator)
    3) Validate patched data against the full model (covered by this validator)
    In fact, the output of the second model is what should be sent to the api, to make everything simple
    :param model:
    :param item_name:
    :return:
    """
    def validate(request, **_):
        patch_data = request.validated["data"]
        request.validated["data"] = data = apply_data_patch(request.validated[item_name], patch_data)
        if data:
            request.validated["data"] = validate_data(request, model, data)
        return request.validated["data"]
    return validate


def validate_patch_data_simple(model, item_name):
    """
    Does same thing as validate_patch_data
    but doesn't apply data recursively
    :param model:
    :param item_name:
    :return:
    """
    def validate(request, **_):
        patch_data = request.validated["data"]
        data = deepcopy(request.validated[item_name])

        # check if there are any changes
        for f, v in patch_data.items():
            if data.get(f) != v:
                break
        else:
            request.validated["data"] = {}
            return  # no changes

        # TODO: move lots management to a distinct endpoint!
        if "lots" in patch_data:
            patch_lots = patch_data.pop("lots", None)
            if patch_lots:
                new_lots = []
                for patch, lot_data in zip(patch_lots, data["lots"]):
                    # if patch_lots is shorter, then some lots are going to be deleted
                    # longer, then some lots are going to be added
                    if lot_data is None:
                        lot_data = patch  # new lot
                    else:
                        lot_data.update(patch)
                    new_lots.append(lot_data)
                data["lots"] = new_lots
            elif "lots" in data:
                del data["lots"]

        data.update(patch_data)
        request.validated["data"] = validate_data(request, model, data)
        return request.validated["data"]
    return validate


def validate_data_model(input_model):
    """
    Simple way to validate data in request.validated["data"] against a provided model
    the result is put back in request.validated["data"]
    :param input_model:
    :return:
    """
    def validate(request, **_):
        data = request.validated["data"]
        request.validated["data"] = validate_data(request, input_model, data)
        return request.validated["data"]
    return validate


def validate_data(request, model, data, to_patch=False):
    with handle_data_exceptions(request):
        instance = model(data)
        instance.validate()
        data = instance.serialize()
    return data


def validate_data_documents(route_key="tender_id", uid_key="_id"):
    def validate(request, **_):
        data = request.validated["data"]
        for key in data.keys():
            if key == "documents" or "Documents" in key:
                if data[key]:
                    docs = []
                    for document in data[key]:
                        # some magic, yep
                        # route_kwargs = {"bid_id": data["id"]}
                        route_kwargs = {route_key: data[uid_key]}
                        document = check_document_batch(request, document, key, route_kwargs)
                        docs.append(document)

                    # replacing documents in request.validated["data"]
                    if docs:
                        data[key] = docs
        return data
    return validate


def validate_item_owner(item_name):
    def validator(request, **_):
        item = request.validated[item_name]
        if not is_item_owner(request, item):
            raise_operation_error(
                request,
                "Forbidden",
                location="url",
                name="permission"
            )
    return validator


def unless_item_owner(*validations, item_name):
    def decorated(request, **_):
        item = request.validated[item_name]
        if not is_item_owner(request, item):
            for validation in validations:
                validation(request)
    return decorated


def unless_administrator(*validations):
    def decorated(request, **_):
        if request.authenticated_role != "Administrator":
            for validation in validations:
                validation(request)
    return decorated


def unless_admins(*validations):
    def decorated(request, **_):
        if request.authenticated_role != "admins":
            for validation in validations:
                validation(request)
    return decorated


def unless_bots(*validations):
    def decorated(request, **_):
        if request.authenticated_role != "bots":
            for validation in validations:
                validation(request)
    return decorated


def unless_bots_or_auction(*validations):
    def decorated(request, **_):
        if request.authenticated_role not in ("bots", "auction"):
            for validation in validations:
                validation(request)
    return decorated


def validate_any(*validations):
    """
    use case:
    @json_view(
        validators=(
            validate_any(
                validate_item_owner("tender"),
                validate_item_owner("bid"),
            ),
            ...
        ),
        ...
    )
    :param validations:
    :return:
    """
    def decorated(request, **_):
        e = AssertionError("validations list can't be empty")
        errors_on_start = deepcopy(request.errors)
        for validation in validations:
            try:
                validation(request)
            except HTTPError as e:
                pass
            else:  # on success
                request.errors = errors_on_start
                break
        else:
            raise e
    return decorated


def validate_accreditation_level(levels, item, operation, source="tender", kind_central_levels=None):
    def validate(request, **kwargs):
        # operation
        _validate_accreditation_level(request, levels, item, operation)

        # real mode acc lvl
        mode = request.validated[source].get("mode")
        _validate_accreditation_level_mode(request, mode, item, operation)

        # procuringEntity.kind = central
        if kind_central_levels:
            pe = request.validated[source].get("procuringEntity")
            if pe:
                kind = pe.get("kind")
                if kind == "central":
                    _validate_accreditation_level(request, kind_central_levels, item, operation)
    return validate


def validate_bid_accreditation_level(request, **kwargs):  # TODO: use validate_accreditation_level directly
    validator = validate_accreditation_level(request.tender_model.edit_accreditations, "bid", "creation")
    validator(request, **kwargs)


# bids
def validate_bid_operation_period(request, **kwargs):
    tender = request.validated["tender"]
    tender_period = tender.get("tenderPeriod", {})
    if (
        tender_period.get("startDate")
        and get_now().isoformat() < tender_period.get("startDate")
        or get_now().isoformat() > tender_period.get("endDate", "")  # TODO: may "endDate" be missed ?
    ):
        operation = "added" if request.method == "POST" else "deleted"
        if request.authenticated_role != "Administrator" and request.method in ("PUT", "PATCH"):
            operation = "updated"
        raise_operation_error(
            request,
            "Bid can be {} only during the tendering period: from ({}) to ({}).".format(
                operation,
                tender_period.get("startDate"),
                tender_period.get("endDate"),
            ),
        )


def validate_bid_operation_in_tendering(request, **_):
    tender_status = request.validated["tender"]["status"]
    if tender_status == "active.tendering":
        raise_operation_error(
            request,
            "Can't view {} in current ({}) tender status".format(
                "bid" if request.matchdict.get("bid_id") else "bids", tender_status
            ),
        )


def validate_bid_operation_not_in_tendering(request, **_):
    status = request.validated["tender"]["status"]
    if status != "active.tendering":
        operation = "add" if request.method == "POST" else "delete"
        if request.authenticated_role != "Administrator" and request.method in ("PUT", "PATCH"):
            operation = "update"
        raise_operation_error(
            request, "Can't {} bid in current ({}) tender status".format(operation, status)
        )


def validate_lotvalue_value(tender, related_lot, value):
    if value or related_lot:
        for lot in tender.get("lots", ""):
            if lot and lot["id"] == related_lot:
                tender_lot_value = lot.get("value")
                if float(tender_lot_value["amount"]) < value.amount:
                    raise ValidationError("value of bid should be less than value of lot")
                if tender_lot_value["currency"] != value.currency:
                    raise ValidationError("currency of bid should be identical to currency of value of lot")
                if tender_lot_value["valueAddedTaxIncluded"] != value.valueAddedTaxIncluded:
                    raise ValidationError(
                        "valueAddedTaxIncluded of bid should be identical " "to valueAddedTaxIncluded of value of lot"
                    )


def validate_bid_value(tender, value):
    if tender.get("lots"):
        if value:
            raise ValidationError("value should be posted for each lot of bid")
    else:
        tender_value = tender.get("value")
        if not value:
            raise ValidationError("This field is required.")
        if Decimal(tender_value["amount"]) < value.amount:
            raise ValidationError("value of bid should be less than value of tender")
        if tender_value["currency"] != value.currency:
            raise ValidationError("currency of bid should be identical to currency of value of tender")
        if tender_value["valueAddedTaxIncluded"] != value.valueAddedTaxIncluded:
            raise ValidationError(
                "valueAddedTaxIncluded of bid should be identical " "to valueAddedTaxIncluded of value of tender"
            )


def validate_value_type(value, datatype):
    if not value:
        return
    type_ = TYPEMAP.get(datatype)
    if not type_:
        raise ValidationError(
            'Type mismatch: value {} does not confront type {}'.format(
                value, type_
            )
        )
    # validate value
    return type_.to_native(value)


def validate_relatedlot(tender, relatedLot):
    if relatedLot not in [lot["id"] for lot in tender.get("lots") or [] if lot]:
        raise ValidationError("relatedLot should be one of lots")


def validate_view_bid_document(request, **kwargs):
    tender_status = request.validated["tender"]["status"]
    if tender_status in ("active.tendering", "active.auction") \
       and not is_item_owner(request, request.validated["bid"]):
        raise_operation_error(
            request,
            "Can't view bid documents in current ({}) tender status".format(tender_status),
        )


def validate_view_bids(request, **kwargs):
    tender_status = request.validated["tender"]["status"]
    if tender_status in ("active.tendering", "active.auction"):
        raise_operation_error(
            request,
            "Can't view {} in current ({}) tender status".format(
                "bid" if request.matchdict.get("bid_id") else "bids", tender_status
            ),
        )


def validate_update_deleted_bid(request, **kwargs):
    if request.validated["bid"]["status"] == "deleted":
        raise_operation_error(request, "Can't update bid in (deleted) status")


def validate_bid_document_operation_period(request, **_):
    tender = request.validated["tender"]
    now = get_now().isoformat()
    if tender["status"] == "active.tendering":
        tender_period = tender["tenderPeriod"]
        if (
            tender_period.get("startDate") and now < tender_period["startDate"]
            or now > tender_period["endDate"]
        ):
            raise_operation_error(
                request,
                "Document can be {} only during the tendering period: from ({}) to ({}).".format(
                    "added" if request.method == "POST" else "updated",
                    tender_period.get("startDate"),
                    tender_period["endDate"],
                ),
            )


# documents
def validate_upload_document(request, **_):
    document = request.validated["data"]
    delete_nones(document)

    # validating and uploading magic
    check_document(request, document)
    document_route = request.matched_route.name.replace("collection_", "")
    update_document_url(request, document, document_route, {})


def update_doc_fields_on_put_document(request, **_):
    """
    PUT document means that we upload a new version, but some of the fields is taken from the base version
    we have to copy these fields in this method and insert before document model validator
    """
    document = request.validated["data"]
    prev_version = request.validated["document"]
    json_data = request.validated["json_data"]

    # here we update new document with fields from the previous version
    force_replace = ("id", "author", "datePublished")
    black_list = ("title", "format", "url", "dateModified", "hash")
    for key, value in prev_version.items():
        if key in force_replace or (key not in black_list and key not in json_data):
            document[key] = value


# for openua, openeu
def unless_allowed_by_qualification_milestone(*validations):
    """
    decorator for 24hours and anomaly low price features to skip some view validator functions
    :param validation: a function runs unless it's disabled by an active qualification milestone
    :return:
    """
    def decorated_validation(request, **_):
        now = get_now().isoformat()
        tender = request.validated["tender"]
        bid_id = request.validated["bid"]["id"]
        awards = [q for q in tender.get("awards", "")
                  if q["status"] == "pending" and q["bid_id"] == bid_id]

        # 24 hours
        if "qualifications" in tender:   # for procedures with pre-qualification
            qualifications = [q for q in tender["qualifications"]
                              if q["status"] == "pending" and q["bidID"] == bid_id]
        else:
            qualifications = awards

        for q in qualifications:
            for milestone in q.get("milestones", ""):
                if milestone["code"] == "24h" and milestone["date"] <= now <= milestone["dueDate"]:
                    return  # skipping the validation because of 24 hour milestone

        # low price
        for award in awards:
            for milestone in award.get("milestones", ""):
                if milestone["date"] <= now <= milestone["dueDate"]:
                    if milestone["code"] == "alp":
                        return  # skipping the validation because of low price milestone

        # else
        for validation in validations:
            validation(request)

    return decorated_validation


# auction
def validate_auction_tender_status(request, **_):
    tender_status = request.validated["tender"]["status"]
    if tender_status != "active.auction":
        operations = {
            "GET": "get auction info",
            "POST": "report auction results",
            "PATCH": "update auction urls",
        }
        raise_operation_error(
            request, f"Can't {operations[request.method]} in current ({tender_status}) tender status"
        )


def validate_auction_tender_non_lot(request, **_):
    tender = request.validated["tender"]
    if tender.get("lots"):
        raise_operation_error(
            request,
            [{"participationUrl": ["url should be posted for each lot of bid"]}],
            location="body", name="bids",
            status=422,
        )


def validate_active_lot(request, **_):
    tender = request.validated["tender"]
    lot_id = request.matchdict.get("auction_lot_id")
    if not any(
        lot["status"] == "active"
        for lot in tender.get("lots", "")
        if lot["id"] == lot_id
    ):
        raise_operation_error(
            request,
            "Can {} only in active lot status".format(
                "report auction results" if request.method == "POST" else "update auction urls"
            ),
        )


# award
def validate_create_award_not_in_allowed_period(request, **kwargs):
    tender = request.validated["tender"]
    if tender["status"] != "active.qualification":
        raise_operation_error(request, f"Can't create award in current ({tender['status']}) tender status")


def validate_create_award_only_for_active_lot(request, **kwargs):
    tender = request.validated["tender"]
    award = request.validated["data"]
    if any(lot.get("status") != "active" for lot in tender.get("lots", "")
           if lot["id"] == award.get("lotID")):
        raise_operation_error(request, "Can create award only in active lot status")


def validate_update_award_in_not_allowed_status(request, **kwargs):
    tender = request.validated["tender"]
    if tender["status"] not in ("active.qualification", "active.awarded"):
        raise_operation_error(request, f"Can't update award in current ({tender['status']}) tender status")


def validate_update_award_only_for_active_lots(request, **kwargs):
    tender = request.validated["tender"]
    award = request.validated["award"]
    if any(lot.get("status") != "active" for lot in tender.get("lots", "")
           if lot.get("id") == award.get("lotID")):
        raise_operation_error(request, "Can update award only in active lot status")


def validate_award_with_lot_cancellation_in_pending(request, **kwargs):
    if request.authenticated_role != "tender_owner":
        return

    tender = get_tender()
    lot_id = request.validated["award"].get("lotID")
    if not lot_id:
        return

    tender_created = get_first_revision_date(tender, default=get_now())
    if tender_created < RELEASE_2020_04_19:
        return

    accept_lot = all(
        any(
            complaint.get("status") == "resolved"
            for complaint in cancellation["complaints"]
        )
        for cancellation in tender.get("cancellations", [])
        if cancellation.get("status") == "unsuccessful"
        and cancellation.get("complaints")
        and cancellation.get("relatedLot") == lot_id
    )
    has_lot_pending_cancellations = any(
        cancellation.get("relatedLot") == lot_id
        and cancellation.get("status") == "pending"
        for cancellation in tender.get("cancellations", [])
    )
    if (
        has_lot_pending_cancellations
        or not accept_lot
    ):
        raise_operation_error(
            request,
            f"Can't {OPERATIONS.get(request.method)} award with lot that have active cancellation",
        )


def validate_update_award_with_accepted_complaint(request, **kwargs):
    tender = get_tender()
    lot_id = request.validated["award"].get("lotID")
    if any(
        any(c.get("status") == "accepted"
            for c in i.get("complaints", ""))
        for i in tender.get("awards", "")
        if i.get("lotID") == lot_id
    ):
        raise_operation_error(request, "Can't update award with accepted complaint")


def validate_update_award_status_before_milestone_due_date(request, **kwargs):
    from openprocurement.tender.core.models import QualificationMilestone
    award = request.validated["award"]
    sent_status = request.json.get("data", {}).get("status")
    if award.get("status") == "pending" and sent_status != "pending":
        now = get_now().isoformat()
        for milestone in award.get("milestones", ""):
            if (
                milestone["code"] in (QualificationMilestone.CODE_24_HOURS, QualificationMilestone.CODE_LOW_PRICE)
                and milestone["date"] <= now <= milestone["dueDate"]
            ):
                raise_operation_error(
                    request,
                    f"Can't change status to '{sent_status}' until milestone.dueDate: {milestone['dueDate']}"
                )


# AWARD DOCUMENTS
def validate_award_document_tender_not_in_allowed_status_base(
    request, allowed_bot_statuses=("active.awarded",), **kwargs
):
    allowed_tender_statuses = ["active.qualification"]
    if request.authenticated_role == "bots":
        allowed_tender_statuses.extend(allowed_bot_statuses)
    status = request.validated["tender"]["status"]
    if status not in allowed_tender_statuses:
        raise_operation_error(
            request,
            f"Can't {OPERATIONS.get(request.method)} document in current ({status}) tender status"
        )


def validate_award_document_lot_not_in_allowed_status(request, **kwargs):
    award_lot_id = request.validated["award"].get("lotID")
    if any(
        i.get("status", "active") != "active"
        for i in request.validated["tender"].get("lots", "")
        if i["id"] == award_lot_id
    ):
        raise_operation_error(request, f"Can {OPERATIONS.get(request.method)} document only in active lot status")


def get_award_document_role(request):
    tender = request.validated["tender"]
    if is_item_owner(request, tender):
        role = "tender_owner"
    else:
        role = request.authenticated_role
    return role


def validate_award_document_author(request, **kwargs):
    doc_author = request.validated["document"].get("author") or "tender_owner"
    role = get_award_document_role(request)
    if doc_author == "bots" and role != "bots":
    # if role != doc_author:   # TODO: unkoment when "author": "brokers" fixed
        raise_operation_error(
            request,
            "Can update document only author",
            location="url",
            name="role",
        )


# TENDER
def validate_tender_status_allows_update(*statuses):
    def validate(request, **_):
        tender_status = get_tender()["status"]
        if tender_status not in statuses:
            raise_operation_error(request, f"Can't update tender in current ({tender_status}) status")
    return validate


def validate_item_quantity(request, **kwargs):
    items = request.validated["data"].get("items", [])
    for item in items:
        if item.get("quantity") is not None and not item["quantity"]:
            tender = get_tender()
            tender_creation_date = get_first_revision_date(tender, default=get_now())
            if tender_creation_date >= CRITERION_REQUIREMENT_STATUSES_FROM:
                related_criteria = any(
                    criterion.get("relatedItem") == item['id'] and requirement.get("status") == "active"
                    for criterion in tender.get("criteria", "")
                    for rg in criterion.get("requirementGroups", "")
                    for requirement in rg.get("requirements", "")
                )
                if related_criteria:
                    raise_operation_error(
                        request,
                        f"Can't set to 0 quantity of {item['id']} item while related criterion has active requirements"
                    )


def validate_tender_guarantee(request, **kwargs):
    tender = request.validated["tender"]
    data = request.validated["data"]
    tender_type = tender["procurementMethodType"]
    tender_created = get_first_revision_date(tender, default=get_now())
    if (
        tender_created < RELEASE_GUARANTEE_CRITERION_FROM
        or tender_type not in GUARANTEE_ALLOWED_TENDER_TYPES
        or tender["status"] == data.get("status")
        or data.get("status") not in ("active", "active.tendering")
    ):
        return

    if tender.get("lots"):
        related_guarantee_lots = [
            criterion.get("relatedItem")
            for criterion in tender.get("criteria", "")
            if criterion.get("relatesTo") == "lot"
            and criterion.get("classification")
            and criterion["classification"]["id"] == "CRITERION.OTHER.BID.GUARANTEE"
        ]
        for lot in tender["lots"]:
            if lot["id"] in related_guarantee_lots:
                if not lot.get("guarantee") or lot["guarantee"]["amount"] <= 0:
                    raise_operation_error(
                        request,
                        "Should be specified 'guarantee.amount' more than 0 to lot"
                    )

    else:
        amount = data["guarantee"]["amount"] if data.get("guarantee") else 0
        needed_criterion = "CRITERION.OTHER.BID.GUARANTEE"
        tender_criteria = [
            criterion["classification"]["id"]
            for criterion in tender.get("criteria", "")
            if criterion.get("classification")
        ]
        if (
            (amount <= 0 and needed_criterion in tender_criteria)
            or (amount > 0 and needed_criterion not in tender_criteria)
        ):
            raise_operation_error(
                request,
                "Should be specified {} and 'guarantee.amount' more than 0".format(needed_criterion)
            )


def validate_tender_change_status_with_cancellation_lot_pending(request, **_):
    tender = request.validated["tender"]
    tender_created = get_first_revision_date(tender, default=get_now())
    data = request.validated["data"]
    new_status = data.get("status", tender["status"])

    if (
        tender_created < RELEASE_2020_04_19
        or not tender.get("lots")
        or tender["status"] == new_status
    ):
        return

    accept_lot = all(
        any(j.get("status") == "resolved" for j in i.get("complaints", ""))
        for i in tender.get("cancellations", "")
        if i.get("status") == "unsuccessful" and i.get("complaints") and i.get("relatedLot")
    )
    if (
        any(i.get("relatedLot") and i.get("status") == "pending" for i in tender.get("cancellations", ""))
        or not accept_lot

    ):
        raise_operation_error(
            request,
            "Can't update tender with pending cancellation in one of exists lot",
        )


def validate_tender_activate_with_criteria(request, **_):
    tender = request.validated["tender"]
    data = request.validated["data"]
    if (
        get_first_revision_date(tender, default=get_now()) < RELEASE_ECRITERIA_ARTICLE_17
        or request.validated["tender_src"]["status"] == data.get("status")
        or data.get("status") not in ("active", "active.tendering")
    ):
        return

    tender_criteria = {criterion["classification"]["id"]
                       for criterion in tender.get("criteria", "")
                       if criterion.get("classification")}

    # exclusion criteria
    exclusion_criteria = {
        "CRITERION.EXCLUSION.CONVICTIONS.PARTICIPATION_IN_CRIMINAL_ORGANISATION",
        "CRITERION.EXCLUSION.CONVICTIONS.FRAUD",
        "CRITERION.EXCLUSION.CONVICTIONS.CORRUPTION",
        "CRITERION.EXCLUSION.CONVICTIONS.CHILD_LABOUR-HUMAN_TRAFFICKING",
        "CRITERION.EXCLUSION.CONTRIBUTIONS.PAYMENT_OF_TAXES",
        "CRITERION.EXCLUSION.BUSINESS.BANKRUPTCY",
        "CRITERION.EXCLUSION.MISCONDUCT.MARKET_DISTORTION",
        "CRITERION.EXCLUSION.CONFLICT_OF_INTEREST.MISINTERPRETATION",
        "CRITERION.EXCLUSION.NATIONAL.OTHER",
    }
    if exclusion_criteria - tender_criteria:
        raise_operation_error(request, "Tender must contain all 9 `EXCLUSION` criteria")

    # language criteria
    tenders_types = ["aboveThresholdUA", "aboveThresholdEU",
                     "competitiveDialogueUA", "competitiveDialogueEU",
                     "competitiveDialogueUA.stage2", "competitiveDialogueEU.stage2",
                     "esco", "closeFrameworkAgreementUA"]

    language_criterion = "CRITERION.OTHER.BID.LANGUAGE"
    if (
        tender["procurementMethodType"] in tenders_types
        and language_criterion not in tender_criteria
    ):
        raise_operation_error(request, f"Tender must contain {language_criterion} criterion")


# tender documents
def validate_document_operation_in_not_allowed_period(request, **_):
    tender_status = request.validated["tender"]["status"]
    if (
        request.authenticated_role != "auction" and tender_status not in (
            "active.tendering", "draft", "draft.stage2")
        or request.authenticated_role == "auction" and tender_status not in ("active.auction", "active.qualification")
    ):
        raise_operation_error(
            request,
            f"Can't {OPERATIONS.get(request.method)} document in current ({tender_status}) tender status",
        )


def validate_tender_document_update_not_by_author_or_tender_owner(request, **_):
    document = request.validated["document"]
    role = get_tender_document_role(request)
    if role != (document.get("author") or "tender_owner"):
        request.errors.add("url", "role", "Can update document only author")
        request.errors.status = 403
        raise error_handler(request)
