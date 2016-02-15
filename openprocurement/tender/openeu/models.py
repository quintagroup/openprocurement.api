from uuid import uuid4
from datetime import timedelta, time, datetime
from zope.interface import implementer
from schematics.types import StringType, MD5Type
from schematics.types.compound import ModelType
from schematics.types.serializable import serializable
from schematics.transforms import blacklist, whitelist
from schematics.exceptions import ValidationError
from openprocurement.api.models import ITender, TZ
from openprocurement.api.models import (Document, Model, Address, Period,
                                        IsoDateTimeType, ListType)
from openprocurement.api.models import Tender as BaseTender
from openprocurement.api.models import Identifier as BaseIdentifier
from openprocurement.api.models import Item as BaseItem
from openprocurement.api.models import Bid as BaseBid
from openprocurement.api.models import Lot as BaseLot
from openprocurement.api.models import Award as BaseAward
from openprocurement.api.models import ContactPoint as BaseContactPoint
from openprocurement.api.models import LotValue as BaseLotValue
from openprocurement.api.models import Lot as BaseLot
from openprocurement.api.models import validate_cpv_group, validate_items_uniq, validate_lots_uniq
from openprocurement.api.models import (
    plain_role, create_role, edit_role, view_role, listing_role,
    auction_view_role, auction_post_role, auction_patch_role, enquiries_role,
    auction_role, chronograph_role, chronograph_view_role, view_bid_role,
    Administrator_bid_role, Administrator_role, schematics_default_role,
    schematics_embedded_role, get_now, embedded_lot_role, default_lot_role,
    calc_auction_end_time, get_tender, validate_lots_uniq,
)
from openprocurement.tender.openua.utils import calculate_business_date
from openprocurement.tender.openua.models import (
    PeriodStartEndRequired, SifterListType, Complaint, COMPLAINT_SUBMIT_TIME,
)

eu_role = blacklist('enquiryPeriod', 'qualifications')
edit_role_eu = edit_role + eu_role
create_role_eu = create_role + eu_role
qualifications_role = enquiries_role + eu_role
eu_auction_role = auction_role + eu_role

TENDERING_DAYS = 30
TENDERING_DURATION = timedelta(days=TENDERING_DAYS)
QUESTIONS_STAND_STILL = timedelta(days=3)
COMPLAINT_STAND_STILL = timedelta(days=10)


def bids_validation_wrapper(validation_func):
    def validator(klass, data, value):
        if data['status'] in ('deleted', 'invalid'):
            # skip not valid bids
            return
        tender = data['__parent__']
        request = tender.__parent__.request
        if request.method == "PATCH" and isinstance(tender, Tender) and request.authenticated_role == "tender_owner":
            # disable bids validation on tender PATCH requests as tender bids will be invalidated
            return
        return validation_func(klass, data, value)
    return validator

class Item(BaseItem):
    """A good, service, or work to be contracted."""

    description_en = StringType(required=True, min_length=1)


class Identifier(BaseIdentifier):

    legalName_en = StringType(required=True, min_length=1)


class ContactPoint(BaseContactPoint):

    name_en = StringType(required=True, min_length=1)
    availableLanguage = StringType(required=True, min_length=1)


class Organization(Model):
    """An organization."""
    class Options:
        roles = {
            'embedded': schematics_embedded_role,
            'view': schematics_default_role,
        }

    name = StringType(required=True)
    name_en = StringType(required=True, min_length=1)
    name_ru = StringType()
    identifier = ModelType(Identifier, required=True)
    additionalIdentifiers = ListType(ModelType(Identifier))
    address = ModelType(Address, required=True)
    contactPoint = ModelType(ContactPoint, required=True)
    additionalContactPoints = ListType(ModelType(ContactPoint, required=True),
                                       required=False)


class ConfidentialDocument(Document):
    """ Confidential Document """

    confidentiality = StringType(choices=['public', 'buyerOnly'], default='public')
    confidentialityRationale = StringType()

    def validate_confidentialityRationale(self, data, val):
        if data['confidentiality'] != 'public':
            if not val:
                raise ValidationError(u"confidentialityRationale is required")
            elif len(val) < 30:
                raise ValidationError(u"confidentialityRationale should contain at least 30 characters")


class TenderAuctionPeriod(Period):
    """The auction period."""

    @serializable(serialize_when_none=False)
    def shouldStartAfter(self):
        if self.endDate:
            return
        tender = self.__parent__
        if tender.lots or tender.status not in ['active.pre-qualification.stand-still', 'active.auction'] or not tender.qualificationPeriod or not tender.qualificationPeriod.endDate:
            return
        if self.startDate and get_now() > calc_auction_end_time(tender.numberOfBids, self.startDate):
            return calc_auction_end_time(tender.numberOfBids, self.startDate).isoformat()
        else:
            decision_dates = [
                datetime.combine(complaint.dateDecision.date() + timedelta(days=3), time(0, tzinfo=complaint.dateDecision.tzinfo))
                for complaint in tender.complaints
                if complaint.dateDecision
            ]
            decision_dates.append(tender.qualificationPeriod.endDate)
            return max(decision_dates).isoformat()


class LotAuctionPeriod(Period):
    """The auction period."""

    @serializable(serialize_when_none=False)
    def shouldStartAfter(self):
        if self.endDate:
            return
        tender = get_tender(self)
        lot = self.__parent__
        if tender.status not in ['active.pre-qualification.stand-still', 'active.auction'] or lot.status != 'active' or not tender.qualificationPeriod or not tender.qualificationPeriod.endDate:
            return
        if self.startDate and get_now() > calc_auction_end_time(lot.numberOfBids, self.startDate):
            return calc_auction_end_time(lot.numberOfBids, self.startDate).isoformat()
        else:
            decision_dates = [
                datetime.combine(complaint.dateDecision.date() + timedelta(days=3), time(0, tzinfo=complaint.dateDecision.tzinfo))
                for complaint in tender.complaints
                if complaint.dateDecision
            ]
            decision_dates.append(tender.qualificationPeriod.endDate)
            return max(decision_dates).isoformat()


class Lot(BaseLot):

    class Options:
        roles = {
            'create': whitelist('id', 'title', 'title_en', 'title_ru', 'description', 'description_en', 'description_ru', 'value', 'minimalStep'),
            'edit': whitelist('title', 'title_en', 'title_ru', 'description', 'description_en', 'description_ru', 'value', 'minimalStep'),
            'embedded': embedded_lot_role,
            'view': default_lot_role,
            'default': default_lot_role,
            'auction_view': default_lot_role,
            'auction_patch': whitelist('id', 'auctionUrl'),
            'chronograph': whitelist('id', 'auctionPeriod'),
            'chronograph_view': whitelist('id', 'auctionPeriod', 'numberOfBids', 'status'),
        }

    auctionPeriod = ModelType(LotAuctionPeriod, default={})

    @serializable
    def numberOfBids(self):
        """A property that is serialized by schematics exports."""
        bids = [
            bid
            for bid in self.__parent__.bids
            if self.id in [i.relatedLot for i in bid.lotValues if i.status in ["active", "pending"]] and bid.status in ["active", "pending"]
        ]
        return len(bids)


class LotValue(BaseLotValue):
    status = StringType(choices=['pending', 'active', 'unsuccessful'],
                        default='pending')

    def validate_value(self, data, value):
        if value and isinstance(data['__parent__'], Model) and ( data['__parent__'].status not in ('invalid')) and data['relatedLot']:
            lots = [i for i in get_tender(data['__parent__']).lots if i.id == data['relatedLot']]
            if not lots:
                return
            lot = lots[0]
            if lot.value.amount < value.amount:
                raise ValidationError(u"value of bid should be less than value of lot")
            if lot.get('value').currency != value.currency:
                raise ValidationError(u"currency of bid should be identical to currency of value of lot")
            if lot.get('value').valueAddedTaxIncluded != value.valueAddedTaxIncluded:
                raise ValidationError(u"valueAddedTaxIncluded of bid should be identical to valueAddedTaxIncluded of value of lot")

class Bid(BaseBid):
    class Options:
        roles = {
            'Administrator': Administrator_bid_role,
            'embedded': view_bid_role,
            'view': view_bid_role,
            'create': whitelist('value', 'tenderers', 'parameters', 'lotValues'),
            'edit': whitelist('value', 'tenderers', 'parameters', 'lotValues', 'status'),
            'auction_view': whitelist('value', 'lotValues', 'id', 'date', 'parameters', 'participationUrl'),
            'auction_post': whitelist('value', 'lotValues', 'id', 'date'),
            'auction_patch': whitelist('id', 'lotValues', 'participationUrl'),
            'active.enquiries': whitelist(),
            'active.tendering': whitelist(),
            'active.pre-qualification': whitelist('id', 'status', 'documents'),
            'active.pre-qualification.stand-still': whitelist('id', 'status', 'documents'),
            'active.auction': whitelist('id', 'status', 'documents'),
            'active.qualification': view_bid_role,
            'active.awarded': view_bid_role,
            'complete': view_bid_role,
            'unsuccessful': view_bid_role,
            'cancelled': view_bid_role,
            'invalid': whitelist('id', 'status', 'documents'),
            'deleted': whitelist('id', 'status'),
        }
    documents = ListType(ModelType(ConfidentialDocument), default=list())
    status = StringType(choices=['pending', 'active', 'invalid', 'unsuccessful', 'deleted'],
                        default='pending')

    lotValues = ListType(ModelType(LotValue), default=list())

    def serialize(self, role=None):
        if role and self.status in ['invalid', 'deleted']:
            role = self.status
        return super(Bid, self).serialize(role)

    @serializable(serialized_name="status")
    def serialize_status(self):
        if self.__parent__.status in ['active.tendering', 'active.pre-qualification']:
            return self.status
        if self.__parent__.lots:
            if [i.relatedLot for i in self.lotValues if i.status == 'active']:
                return 'active'
            else:
                return 'unsuccessful'
        return self.status

    @bids_validation_wrapper
    def validate_value(self, data, value):
        BaseBid._validator_functions['value'](self, data, value)

    @bids_validation_wrapper
    def validate_lotValues(self, data, lotValues):
        BaseBid._validator_functions['lotValues'](self, data, lotValues)

    @bids_validation_wrapper
    def validate_participationUrl(self, data, participationUrl):
        BaseBid._validator_functions['participationUrl'](self, data, participationUrl)

    @bids_validation_wrapper
    def validate_parameters(self, data, parameters):
        BaseBid._validator_functions['parameters'](self, data, parameters)


class Award(BaseAward):
    """ An award for the given procurement. There may be more than one award
        per contracting process e.g. because the contract is split amongst
        different providers, or because it is a standing offer.
    """
    complaints = ListType(ModelType(Complaint), default=list())
    items = ListType(ModelType(Item))


class Qualification(Model):
    """ Pre-Qualification """

    class Options:
        roles = {
            'create': blacklist('id', 'status', 'documents', 'date'),
            'edit': blacklist('id', 'documents'),
            'embedded': schematics_embedded_role,
            'view': schematics_default_role,
            'auction_view': whitelist('value', 'date', 'relatedLot', 'participationUrl'),
            'auction_post': whitelist('value', 'date', 'relatedLot'),
            'auction_patch': whitelist('participationUrl', 'relatedLot'),
        }

    id = MD5Type(required=True, default=lambda: uuid4().hex)
    bidID = StringType(required=True)
    lotID = MD5Type()
    status = StringType(choices=['pending', 'active', 'unsuccessful', 'cancelled'], default='pending')
    date = IsoDateTimeType()
    documents = ListType(ModelType(Document), default=list())

    def validate_lotID(self, data, lotID):
        if isinstance(data['__parent__'], Model):
            if not lotID and data['__parent__'].lots:
                raise ValidationError(u'This field is required.')
            if lotID and lotID not in [i.id for i in data['__parent__'].lots]:
                raise ValidationError(u"lotID should be one of lots")


@implementer(ITender)
class Tender(BaseTender):
    """ OpenEU tender model """
    class Options:
        roles = {
            'plain': plain_role,
            'create': create_role_eu,
            'edit': edit_role_eu,
            'edit_active.tendering': edit_role_eu,
            'edit_active.pre-qualification': whitelist('status'),
            'edit_active.pre-qualification.stand-still': whitelist(),
            'edit_active.auction': whitelist(),
            'edit_active.qualification': whitelist(),
            'edit_active.awarded': whitelist(),
            'edit_complete': whitelist(),
            'edit_unsuccessful': whitelist(),
            'edit_cancelled': whitelist(),
            'view': view_role,
            'listing': listing_role,
            'auction_view': auction_view_role,
            'auction_post': auction_post_role,
            'auction_patch': auction_patch_role,
            'active.tendering': qualifications_role,
            'active.pre-qualification': qualifications_role,
            'active.pre-qualification.stand-still': qualifications_role,
            'active.auction': eu_auction_role,
            'active.qualification': view_role,
            'active.awarded': view_role,
            'complete': view_role,
            'unsuccessful': view_role,
            'cancelled': view_role,
            'chronograph': chronograph_role,
            'chronograph_view': chronograph_view_role,
            'Administrator': Administrator_role,
            'default': schematics_default_role,
        }

    procurementMethodType = StringType(default="aboveThresholdEU")
    title_en = StringType(required=True, min_length=1)

    enquiryPeriod = ModelType(Period, required=False)
    tenderPeriod = ModelType(PeriodStartEndRequired, required=True)
    auctionPeriod = ModelType(TenderAuctionPeriod, default={})
    items = ListType(ModelType(Item), required=True, min_size=1, validators=[validate_cpv_group, validate_items_uniq])  # The goods and services to be purchased, broken into line items wherever possible. Items should not be duplicated, but a quantity of 2 specified instead.
    complaints = ListType(ModelType(Complaint), default=list())
    awards = ListType(ModelType(Award), default=list())
    procuringEntity = ModelType(Organization, required=True)  # The entity managing the procurement, which may be different from the buyer who is paying / using the items being procured.
    bids = SifterListType(ModelType(Bid), default=list(), filter_by='status', filter_in_values=['invalid', 'deleted',])  # A list of all the companies who entered submissions for the tender.
    qualifications = ListType(ModelType(Qualification), default=list())
    qualificationPeriod = ModelType(Period)
    lots = ListType(ModelType(Lot), default=list(), validators=[validate_lots_uniq])
    status = StringType(choices=['active.tendering', 'active.pre-qualification', 'active.pre-qualification.stand-still', 'active.auction',
                                 'active.qualification', 'active.awarded', 'complete', 'cancelled', 'unsuccessful'], default='active.tendering')

    def initialize(self):
        self.enquiryPeriod = Period(dict(startDate=self.tenderPeriod.startDate, endDate=calculate_business_date(self.tenderPeriod.endDate, -QUESTIONS_STAND_STILL)))

    @serializable(serialized_name="enquiryPeriod", type=ModelType(Period))
    def tender_enquiryPeriod(self):
        return Period(dict(startDate=self.tenderPeriod.startDate,
                           endDate=calculate_business_date(self.tenderPeriod.endDate, -QUESTIONS_STAND_STILL)))

    @serializable(type=ModelType(Period))
    def complaintPeriod(self):
        return Period(dict(startDate=self.tenderPeriod.startDate,
                           endDate=calculate_business_date(self.tenderPeriod.endDate, -COMPLAINT_SUBMIT_TIME)))

    @serializable(serialize_when_none=False)
    def next_check(self):
        now = get_now()
        checks = []
        if self.status == 'active.tendering' and self.tenderPeriod.endDate:
            checks.append(self.tenderPeriod.endDate.astimezone(TZ))
        elif self.status == 'active.pre-qualification.stand-still' and self.qualificationPeriod and self.qualificationPeriod.endDate:
            checks.append(self.qualificationPeriod.endDate.astimezone(TZ))
        elif not self.lots and self.status == 'active.auction' and self.auctionPeriod and self.auctionPeriod.startDate and not self.auctionPeriod.endDate:
            if now < self.auctionPeriod.startDate:
                checks.append(self.auctionPeriod.startDate.astimezone(TZ))
            elif now < calc_auction_end_time(self.numberOfBids, self.auctionPeriod.startDate).astimezone(TZ):
                checks.append(calc_auction_end_time(self.numberOfBids, self.auctionPeriod.startDate).astimezone(TZ))
        elif self.lots and self.status == 'active.auction':
            for lot in self.lots:
                if lot.status != 'active' or not lot.auctionPeriod or not lot.auctionPeriod.startDate or lot.auctionPeriod.endDate:
                    continue
                if now < lot.auctionPeriod.startDate:
                    checks.append(lot.auctionPeriod.startDate.astimezone(TZ))
                elif now < calc_auction_end_time(lot.numberOfBids, lot.auctionPeriod.startDate).astimezone(TZ):
                    checks.append(calc_auction_end_time(lot.numberOfBids, lot.auctionPeriod.startDate).astimezone(TZ))
        elif not self.lots and self.status == 'active.awarded':
            standStillEnds = [
                a.complaintPeriod.endDate.astimezone(TZ)
                for a in self.awards
                if a.complaintPeriod.endDate
            ]
            if standStillEnds:
                standStillEnd = max(standStillEnds)
                if standStillEnd > now:
                    checks.append(standStillEnd)
        elif self.lots and self.status in ['active.qualification', 'active.awarded']:
            lots_ends = []
            for lot in self.lots:
                if lot['status'] != 'active':
                    continue
                lot_awards = [i for i in self.awards if i.lotID == lot.id]
                standStillEnds = [
                    a.complaintPeriod.endDate.astimezone(TZ)
                    for a in lot_awards
                    if a.complaintPeriod.endDate
                ]
                if not standStillEnds:
                    continue
                standStillEnd = max(standStillEnds)
                if standStillEnd > now:
                    lots_ends.append(standStillEnd)
            if lots_ends:
                checks.append(min(lots_ends))
        return min(checks).isoformat() if checks else None

    def validate_tenderPeriod(self, data, period):
        if period and calculate_business_date(period.startDate, TENDERING_DURATION) > period.endDate:
            raise ValidationError(u"tenderPeriod should be greater than {} days".format(TENDERING_DAYS))

    @serializable
    def numberOfBids(self):
        """A property that is serialized by schematics exports."""
        return len([bid for bid in self.bids if bid.status in ("active", "pending",)])

    def invalidate_bids_data(self):
        for bid in self.bids:
            if bid.status != "deleted":
                bid.status = "invalid"
