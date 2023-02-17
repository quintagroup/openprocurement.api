# -*- coding: utf-8 -*-
from openprocurement.api.utils import json_view
from openprocurement.framework.core.utils import frameworksresource
from openprocurement.framework.core.views.framework import CoreFrameworkResource
from openprocurement.framework.core.validation import (
    validate_patch_framework_data,
    validate_framework_patch_status,
)
from openprocurement.framework.open.constants import OPEN_TYPE


@frameworksresource(
    name=f"{OPEN_TYPE}:Frameworks",
    path="/frameworks/{framework_id}",
    frameworkType=OPEN_TYPE,
    description="Frameworks",
)
class FrameworkResource(CoreFrameworkResource):

    @json_view(
        content_type="application/json",
        validators=(
            validate_patch_framework_data,
            validate_framework_patch_status,
        ),
        permission="edit_framework",
    )
    def patch(self):
        return super(FrameworkResource, self).patch()