from cornice.resource import resource

from openprocurement.api.procedure.validation import (
    unless_administrator,
    validate_input_data,
    validate_patch_data,
)
from openprocurement.api.utils import json_view
from openprocurement.framework.core.procedure.models.qualification import (
    PatchQualification,
)
from openprocurement.framework.core.procedure.validation import (
    validate_action_in_not_allowed_framework_status,
    validate_framework_owner,
    validate_update_qualification_in_not_allowed_status,
)
from openprocurement.framework.core.procedure.views.qualification import (
    QualificationsResource,
)
from openprocurement.framework.ifi.constants import IFI_TYPE
from openprocurement.framework.ifi.procedure.models.qualification import Qualification
from openprocurement.framework.ifi.procedure.state.framework import IFIFrameworkState


@resource(
    name=f"{IFI_TYPE}:Qualifications",
    collection_path="/qualifications",
    path="/qualifications/{qualification_id}",
    description=f"{IFI_TYPE} qualifications",
    qualificationType=IFI_TYPE,
    accept="application/json",
)
class IFIQualificationResource(QualificationsResource):
    state_class = IFIFrameworkState

    @json_view(
        content_type="application/json",
        validators=(
            unless_administrator(
                validate_framework_owner("qualification"),
            ),
            validate_input_data(PatchQualification),
            validate_update_qualification_in_not_allowed_status,
            validate_action_in_not_allowed_framework_status("qualification"),
            validate_patch_data(Qualification, item_name="qualification"),
        ),
        permission="edit_qualification",
    )
    def patch(self):
        return super().patch()
