import unittest

from openprocurement.api.tests.base import snitch
from openprocurement.contracting.api.tests.base import (
    BaseContractTest,
    BaseContractWebTest,
    BaseContractWebTestTwoItems,
)
from openprocurement.contracting.api.tests.contract_blanks import (
    contract_administrator_change,
    contract_items_change,
    contract_status_change,
    contract_token_invalid,
    contract_update_add_remove_items,
    contract_wo_items_status_change,
    create_contract,
    create_contract_already_exists,
    create_contract_generated,
    create_contract_invalid,
    create_contract_transfer_token,
    create_contract_w_documents,
    empty_listing,
    generate_credentials,
    generate_credentials_invalid,
    get_contract,
    get_credentials,
    listing,
    listing_changes,
    not_found,
    patch_tender_contract,
    patch_tender_contract_amount_paid_zero,
    patch_tender_contract_identical,
    patch_tender_contract_readonly,
    patch_tender_contract_single_request,
    patch_tender_contract_value_amount,
    patch_tender_contract_value_vat_change,
    patch_tender_contract_without_value,
    patch_tender_contract_wo_amount_net,
    put_transaction_to_contract,
    simple_add_contract,
    skip_address_validation,
)
from openprocurement.contracting.api.tests.data import (
    test_contract_data,
    test_contract_data_wo_items,
    test_contract_data_wo_value_amount_net,
)


class ContractListingTests(BaseContractTest):
    initial_auth = ("Basic", ("broker", ""))
    initial_data = test_contract_data

    test_empty_listing = snitch(empty_listing)
    test_listing = snitch(listing)
    test_listing_changes = snitch(listing_changes)


class ContractResourceTest(BaseContractTest):
    initial_data = test_contract_data
    initial_auth = ("Basic", ("contracting", ""))

    test_simple_add_contract = snitch(simple_add_contract)
    test_get_contract = snitch(get_contract)
    test_not_found = snitch(not_found)
    test_create_contract_invalid = snitch(create_contract_invalid)
    test_create_contract_generated = snitch(create_contract_generated)
    test_create_contract = snitch(create_contract)
    test_create_contract_already_exists = snitch(create_contract_already_exists)
    test_create_contract_transfer_token = snitch(create_contract_transfer_token)
    test_create_contract_w_documents = snitch(create_contract_w_documents)
    test_skip_address_validation = snitch(skip_address_validation)


class ContractResource4BrokersTest(BaseContractWebTest):
    test_contract_token_invalid = snitch(contract_token_invalid)
    test_contract_status_change = snitch(contract_status_change)
    test_contract_items_change = snitch(contract_items_change)
    test_patch_tender_contract = snitch(patch_tender_contract)
    test_patch_tender_contract_identical = snitch(patch_tender_contract_identical)
    test_patch_tender_contract_readonly = snitch(patch_tender_contract_readonly)
    test_patch_tender_contract_value_vat_change = snitch(patch_tender_contract_value_vat_change)
    test_patch_tender_contract_without_value = snitch(patch_tender_contract_without_value)
    test_patch_tender_contract_value_amount = snitch(patch_tender_contract_value_amount)
    test_patch_tender_contract_amount_paid_zero = snitch(patch_tender_contract_amount_paid_zero)
    test_patch_tender_contract_single_request = snitch(patch_tender_contract_single_request)
    test_get_credentials = snitch(get_credentials)
    test_generate_credentials = snitch(generate_credentials)
    test_generate_credentials_invalid = snitch(generate_credentials_invalid)
    test_put_transaction_to_contract = snitch(put_transaction_to_contract)


class ContractResource4BrokersTestMultipleItems(BaseContractWebTestTwoItems):
    test_contract_update_add_remove_items = snitch(contract_update_add_remove_items)


class ContractResource4AdministratorTest(BaseContractWebTest):
    initial_auth = ("Basic", ("administrator", ""))

    test_contract_administrator_change = snitch(contract_administrator_change)


class ContractWOItemsResource4BrokersTest(BaseContractWebTest):
    initial_data = test_contract_data_wo_items

    test_contract_wo_items_status_change = snitch(contract_wo_items_status_change)


class ContractWOAmountNetResource4BrokersTest(BaseContractWebTest):
    initial_data = test_contract_data_wo_value_amount_net

    test_patch_tender_contract = snitch(patch_tender_contract_wo_amount_net)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(ContractResourceTest))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(ContractResource4BrokersTest))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(ContractResource4AdministratorTest))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(ContractWOItemsResource4BrokersTest))
    suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(ContractWOAmountNetResource4BrokersTest))
    return suite


if __name__ == "__main__":
    unittest.main(defaultTest="suite")
