from schematics.types import BaseType, BooleanType, StringType
from schematics.types.compound import DictType

from openprocurement.api.procedure.models.base import Model, RootModel
from openprocurement.api.procedure.types import IsoDateTimeType, ListType, ModelType
from openprocurement.api.utils import get_now
from openprocurement.framework.core.procedure.models.document import (
    Document,
    PostDocument,
)


class PatchQualification(Model):
    documents = ListType(ModelType(PostDocument, required=True), default=list())
    status = StringType(
        choices=["pending", "active", "unsuccessful"],
        default="pending",
    )


class Qualification(RootModel):
    documents = ListType(ModelType(Document, required=True), default=list())
    submissionID = StringType(required=True)
    frameworkID = StringType(required=True)
    status = StringType(
        choices=["pending", "active", "unsuccessful"],
        default="pending",
    )

    date = IsoDateTimeType(default=get_now)
    dateCreated = IsoDateTimeType()
    dateModified = IsoDateTimeType()

    framework_owner = StringType()
    framework_token = StringType()

    submission_owner = StringType()
    submission_token = StringType()

    _attachments = DictType(DictType(BaseType), default=dict())
    revisions = BaseType(default=list)
    config = BaseType()

    mode = StringType(choices=["test"])


class QualificationConfig(Model):
    test = BooleanType()
    restricted = BooleanType()
