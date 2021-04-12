import unittest

from openprocurement.api.tests.base import snitch
from openprocurement.framework.electroniccatalogue.tests.agreement_blanks import (
    create_agreement,
    change_agreement,
    patch_contract_suppliers,
    post_ban_milestone,
    post_ban_milestone_with_documents,
    post_disqualification_milestone,
    post_disqualification_milestone_with_documents,
    post_milestone_invalid,
    get_documents_list,
    get_document_by_id,
    create_milestone_document_forbidden,
    create_milestone_documents,
    create_milestone_document_json_bulk,
    put_milestone_document,
    patch_agreement_terminated_status,
    patch_contract_active_status,
    patch_several_contracts_active_status,
)
from openprocurement.framework.electroniccatalogue.tests.base import (
    test_electronicCatalogue_data,
    test_submission_data,
    AgreementContentWebTest,
    MilestoneContentWebTest,
    ban_milestone_data_with_documents,
)
from openprocurement.framework.electroniccatalogue.tests.qualification import (
    QualificationContentWebTest as BaseQualificationContentWebTest,
)


class QualificationContentWebTest(BaseQualificationContentWebTest):
    def setUp(self):
        super().setUp()
        response = self.app.post(
            "/qualifications/{}/documents?acc_token={}".format(self.qualification_id, self.framework_token),
            upload_files=[("file", "name  name.doc", b"content")]
        )
        self.assertEqual(response.status, "201 Created")


class TestAgreementCreation(QualificationContentWebTest):
    initial_data = test_electronicCatalogue_data
    initial_submission_data = test_submission_data
    initial_auth = ('Basic', ('broker', ''))
    docservice = True

    test_create_agreement = snitch(create_agreement)


class TestAgreementChanges(AgreementContentWebTest):
    initial_data = test_electronicCatalogue_data
    initial_submission_data = test_submission_data
    initial_auth = ('Basic', ('broker', ''))

    test_change_agreement = snitch(change_agreement)
    test_patch_contract_suppliers = snitch(patch_contract_suppliers)


class TestAgreementResource(AgreementContentWebTest):
    initial_data = test_electronicCatalogue_data
    initial_submission_data = test_submission_data
    initial_auth = ('Basic', ('broker', ''))

    # Chronograph
    test_patch_agreement_terminated_status = snitch(patch_agreement_terminated_status)
    test_patch_contract_active_status = snitch(patch_contract_active_status)
    test_patch_several_contracts_active_status = snitch(patch_several_contracts_active_status)


class TestAgreementMilestoneResource(AgreementContentWebTest):
    initial_data = test_electronicCatalogue_data
    initial_submission_data = test_submission_data
    initial_auth = ('Basic', ('broker', ''))

    test_post_milestone_invalid = snitch(post_milestone_invalid)
    test_post_ban_milestone_with_documents = snitch(post_ban_milestone_with_documents)
    test_post_ban_milestone = snitch(post_ban_milestone)
    test_post_disqualification_milestone = snitch(post_disqualification_milestone)
    test_post_disqualification_milestone_with_documents = snitch(post_disqualification_milestone_with_documents)


class TestMilestoneDocumentGet(MilestoneContentWebTest):
    initial_data = test_electronicCatalogue_data
    initial_submission_data = test_submission_data
    initial_milestone_data = ban_milestone_data_with_documents

    test_get_documents_list = snitch(get_documents_list)
    test_get_document_by_id = snitch(get_document_by_id)

    def setUp(self):
        for document in self.initial_milestone_data["documents"]:
            document["url"] = self.generate_docservice_url()
        super().setUp()


class TestMilestoneCreate(MilestoneContentWebTest):
    initial_data = test_electronicCatalogue_data
    initial_submission_data = test_submission_data
    initial_milestone_data = ban_milestone_data_with_documents
    initial_auth = ('Basic', ('broker', ''))
    docservice = True

    test_create_milestone_document_forbidden = snitch(create_milestone_document_forbidden)
    test_create_milestone_documents = snitch(create_milestone_documents)
    test_create_milestone_document_json_bulk = snitch(create_milestone_document_json_bulk)
    test_put_milestone_document = snitch(put_milestone_document)

    def setUp(self):
        for document in self.initial_milestone_data["documents"]:
            document["url"] = self.generate_docservice_url()
        super().setUp()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestAgreementCreation)
    suite.addTest(TestAgreementChanges)
    suite.addTest(TestAgreementMilestoneResource)
    suite.addTest(TestMilestoneDocumentGet)
    suite.addTest(TestMilestoneCreate)


if __name__ == "__main__":
    unittest.main(defaultTest="suite")