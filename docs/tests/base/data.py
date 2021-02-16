# -*- coding: utf-8 -*-
from copy import deepcopy
from datetime import timedelta, datetime
from dateutil.parser import parse
from hashlib import sha512

from openprocurement.tender.belowthreshold.tests.base import test_milestones
from tests.base.constants import MOCK_DATETIME

parameters = [
    {'code': 'OCDS-123454-AIR-INTAKE', 'value': 0.1},
    {'code': 'OCDS-123454-YEARS', 'value': 0.1}
]

tenderer = {
    "address": {
        "countryName": "Україна",
        "locality": "м. Вінниця",
        "postalCode": "21100",
        "region": "Вінницька область",
        "streetAddress": "вул. Островського, 33"
    },
    "contactPoint": {
        "email": "soleksuk@gmail.com",
        "name": "Сергій Олексюк",
        "telephone": "+380 (432) 21-69-30"
    },
    "identifier": {
        "scheme": "UA-EDR",
        "id": "00137256",
        "uri": "http://www.sc.gov.ua/"
    },
    "name": "ДКП «Школяр»",
    "scale": "micro"
}

author = deepcopy(tenderer)
del author['scale']

complaint_author = deepcopy(author)
complaint_author["identifier"]["legalName"] = "ДКП «Школяр»"

tenderer2 = {
    "address": {
        "countryName": "Україна",
        "locality": "м. Львів",
        "postalCode": "79013",
        "region": "Львівська область",
        "streetAddress": "вул. Островського, 34"
    },
    "contactPoint": {
        "email": "aagt@gmail.com",
        "name": "Андрій Олексюк",
        "telephone": "+380 (322) 91-69-30"
    },
    "identifier": {
        "scheme": "UA-EDR",
        "id": "00137226",
        "uri": "http://www.sc.gov.ua/"
    },
    "name": "ДКП «Книга»",
    "scale": "sme"
}

author2 = deepcopy(tenderer2)
del author2['scale']

tenderer3 = {
    "address": {
        "countryName": "Україна",
        "locality": "м. Львів",
        "postalCode": "79013",
        "region": "Львівська область",
        "streetAddress": "вул. Островського, 35"
    },
    "contactPoint": {
        "email": "fake@mail.com",
        "name": "Іван Іваненко",
        "telephone": "+380 (322) 12-34-56"
    },
    "identifier": {
        "scheme": "UA-EDR",
        "id": "00137227",
        "uri": "http://www.sc.gov.ua/"
    },
    "name": "«Снігур»",
    "scale": "mid"
}

tenderer4 = {
    "address": {
        "countryName": "Україна",
        "locality": "м. Запоріжя",
        "postalCode": "79013",
        "region": "Запорізька область",
        "streetAddress": "вул. Коцюбинського, 15"
    },
    "contactPoint": {
        "email": "fake@mail.com",
        "name": "Іван Карпенко",
        "telephone": "+380 (322) 12-34-56"
    },
    "identifier": {
        "scheme": "UA-EDR",
        "id": "00137228",
        "uri": "http://www.sc.gov.ua/"
    },
    "name": "«Кенгуру»",
    "scale": "large"
}

bad_participant = {
    "address": {
        "countryName": "Україна",
        "locality": "м. Львів",
        "postalCode": "21100",
        "region": "Львівська область",
        "streetAddress": "вул. Поле, 33"
    },
    "contactPoint": {
        "email": "pole@gmail.com",
        "name": "Вільям Поле",
        "telephone": "+380 (452) 21-69-31"
    },
    "identifier": {
        "id": "00137230",
        "legalName": "ТОВ Бур",
        "scheme": "UA-EDR",
        "uri": "http://pole.edu.vn.ua/"
    },
    "name": "ТОВ \"Бур\"",
    "scale": "mid"
}

bad_author = deepcopy(bad_participant)
del bad_author['scale']

bid_document = {
    'title': 'Proposal_part1.pdf',
    'url': "http://broken1.ds",
    'hash': 'md5:' + '0' * 32,
    'format': 'application/pdf',
}

bid_document2 = {
    'title': 'Proposal_part2.pdf',
    'url': "http://broken2.ds",
    'hash': 'md5:' + '0' * 32,
    'format': 'application/pdf',
}

bid_document3_eligibility = {
    'title': 'eligibility_doc.pdf',
    'url': "http://broken3.ds",
    'hash': 'md5:' + '0' * 32,
    'format': 'application/pdf',
}

bid_document4_financialy = {
    'title': 'financial_doc.pdf',
    'url': "http://broken4.ds",
    'hash': 'md5:' + '0' * 32,
    'format': 'application/pdf',
}

bid_document5_qualification = {
    'title': 'qualification_document.pdf',
    'url': "http://broken5.ds",
    'hash': 'md5:' + '0' * 32,
    'format': 'application/pdf',
}

bid = {
    "tenderers": [tenderer],
    "value": {
        "amount": 500
    }
}

bid_draft = deepcopy(bid)
bid_draft["status"] = "draft"

bid2 = {
    "tenderers": [tenderer2],
    "value": {
        "amount": 499
    }
}

bid2_with_docs = deepcopy(bid2)
bid2_with_docs["documents"] = [bid_document, bid_document2]

bid3 = {
    "tenderers": [tenderer3],
    "value": {
        "amount": 5
    }
}

bid3_with_docs = deepcopy(bid2)
bid3_with_docs["documents"] = [bid_document, bid_document2]
bid3_with_docs["eligibilityDocuments"] = [bid_document3_eligibility]
bid3_with_docs["financialDocuments"] = [bid_document4_financialy]
bid3_with_docs["qualificationDocuments"] = [bid_document5_qualification]

bid4 = {
    "tenderers": [tenderer4],
    "value": {
        "amount": 5
    }
}

lot_bid = {
    "tenderers": [tenderer],
    "status": "draft",
    "lotValues": [{
        "value": {
            "amount": 500
        },
        "relatedLot": "f" * 32
    }]

}

lot_bid2 = {
    "tenderers": [tenderer2],
    "lotValues": [{
        "value": {
            "amount": 499
        },
        "relatedLot": "f" * 32
    }]
}

lot_bid2_with_docs = deepcopy(lot_bid2)
lot_bid2_with_docs["documents"] = [bid_document, bid_document2]

lot_bid3 = {
    "tenderers": [tenderer3],
    "lotValues": [{
        "value": {
            "amount": 485
        },
        "relatedLot": "f" * 32
    }]
}

lot_bid3_with_docs = deepcopy(lot_bid3)
lot_bid3_with_docs["documents"] = [bid_document, bid_document2]
lot_bid3_with_docs["eligibilityDocuments"] = [bid_document3_eligibility]
lot_bid3_with_docs["financialDocuments"] = [bid_document4_financialy]
lot_bid3_with_docs["qualificationDocuments"] = [bid_document5_qualification]

question = {
    "author": author2,
    "description": "Просимо додати таблицю потрібної калорійності харчування",
    "title": "Калорійність"
}

features = [
    {
        "code": "OCDS-123454-AIR-INTAKE",
        "featureOf": "item",
        "relatedItem": "f" * 32,
        "title": "Потужність всмоктування",
        "title_en": "Air Intake",
        "description": "Ефективна потужність всмоктування пилососа, в ватах (аероватах)",
        "enum": [
            {
                "value": 0.1,
                "title": "До 1000 Вт"
            },
            {
                "value": 0.15,
                "title": "Більше 1000 Вт"
            }
        ]
    },
    {
        "code": "OCDS-123454-YEARS",
        "featureOf": "tenderer",
        "title": "Років на ринку",
        "title_en": "Years trading",
        "description": "Кількість років, які організація учасник працює на ринку",
        "enum": [
            {
                "value": 0.05,
                "title": "До 3 років"
            },
            {
                "value": 0.1,
                "title": "Більше 3 років, менше 5 років"
            },
            {
                "value": 0.15,
                "title": "Більше 5 років"
            }
        ]
    }
]

funder = {
    "additionalIdentifiers": [],
    "address": {
        "countryName": "Швейцарська Конфедерація",
        "locality": "Geneva",
        "postalCode": "1218",
        "region": "Grand-Saconnex",
        "streetAddress": "Global Health Campus, Chemin du Pommier 40"
    },
    "contactPoint": {
        "email": "ccm@theglobalfund.org",
        "faxNumber": "+41 44 580 6820",
        "name": "",
        "telephone": "+41 58 791 1700",
        "url": "https://www.theglobalfund.org/en/"
    },
    "identifier": {
        "id": "47045",
        "legalName": "Глобальний Фонд для боротьби зі СНІДом, туберкульозом і малярією",
        "scheme": "XM-DAC"
    },
    "name": "Глобальний фонд"
}

claim = {
    "description": "Умови виставлені замовником не містять достатньо інформації, щоб заявка мала сенс.",
    "title": "Недостатньо інформації",
    "type": "claim",
    'author': author
}

complaint = {
    "description": "Умови виставлені замовником не містять достатньо інформації, щоб заявка мала сенс.",
    "title": "Недостатньо інформації",
    "status": "draft",
    "type": "complaint",
    'author': complaint_author,
}


qualified = {
    'selfQualified': True
}

subcontracting = {
    'subcontractingDetails': "ДКП «Орфей», Україна"
}

lots = [
    {
        'title': 'Лот №1',
        'description': 'Опис Лот №1',
    },
    {
        'title': 'Лот №2',
        'description': 'Опис Лот №2',
    }
]

items = [
    {
        "id": "f" * 32,
        "description": "футляри до державних нагород",
        "description_en": "Cases with state awards",
        "description_ru": "футляры к государственным наградам",
        "classification": {
            "scheme": "ДК021",
            "id": "44617100-9",
            "description": "Cartons"
        },
        "additionalClassifications": [
            {
                "scheme": "ДКПП",
                "id": "17.21.1",
                "description": "папір і картон гофровані, паперова й картонна тара"
            }
        ],
        "unit": {
            "name": "item",
            "code": "44617100-9"
        },
        "quantity": 5
    }
]

items_en = [
    {
        "additionalClassifications": [
            {
                "scheme": "ДКПП",
                "id": "17.21.1",
                "description": "Послуги шкільних їдалень"
            }
        ],
        "description": "Послуги шкільних їдалень",
        "description_en": "Services in school canteens",
        "classification": {
            "scheme": "ДК021",
            "id": "37810000-9",
            "description": "Test"
        },
        "deliveryDate": {
            "startDate": (parse(MOCK_DATETIME) + timedelta(days=20)).isoformat(),
            "endDate": (parse(MOCK_DATETIME) + timedelta(days=50)).isoformat()
        },
        "deliveryAddress": {
            "countryName": "Україна",
            "postalCode": "79000",
            "region": "м. Київ",
            "locality": "м. Київ",
            "streetAddress": "вул. Банкова 1"
        },
        "quantity": 1
    }, {
        "additionalClassifications": [
            {
                "scheme": "ДКПП",
                "id": "17.21.1",
                "description": "Послуги шкільних їдалень"
            }
        ],
        "description": "Послуги шкільних їдалень",
        "description_en": "Services in school canteens",
        "classification": {
            "scheme": "ДК021",
            "id": "37810000-9",
            "description": "Test"
        },
        "quantity": 1,
        "deliveryDate": {
            "startDate": (parse(MOCK_DATETIME) + timedelta(days=20)).isoformat(),
            "endDate": (parse(MOCK_DATETIME) + timedelta(days=50)).isoformat()
        },
        "deliveryAddress": {
            "countryName": "Україна",
            "postalCode": "79000",
            "region": "м. Київ",
            "locality": "м. Київ",
            "streetAddress": "вул. Банкова 1"
        }
    }
]

items_en_unit = deepcopy(items_en)
items_en_unit[0].update({
    "unit": {
        "code": "44617100-9",
        "name": "item"
    }
})
items_en_unit[1].update({
    "unit": {
        "code": "44617100-9",
        "name": "item"
    }
})

items_ua = [
    {
        "additionalClassifications": [
            {
                "scheme": "ДКПП",
                "id": "17.21.1",
                "description": "Послуги шкільних їдалень"
            }
        ],
        "description": "Послуги шкільних їдалень",
        "deliveryDate": {
            "startDate": (parse(MOCK_DATETIME) + timedelta(days=20)).isoformat(),
            "endDate": (parse(MOCK_DATETIME) + timedelta(days=50)).isoformat()
        },
        "deliveryAddress": {
            "countryName": "Україна",
            "postalCode": "79000",
            "region": "м. Київ",
            "locality": "м. Київ",
            "streetAddress": "вул. Банкова 1"
        },
        "classification": {
            "description": "Послуги з харчування у школах",
            "id": "55523100-3",
            "scheme": "ДК021"
        },
        "quantity": 1
    }
]

items_ua_unit = deepcopy(items_ua)
items_ua_unit[0].update({
    "unit": {
        "code": "44617100-9",
        "name": "item"
    }
})

procuring_entity = {
    "name": "Державне управління справами",
    "identifier": {
        "scheme": "UA-EDR",
        "id": "00037256",
        "uri": "http://www.dus.gov.ua/"
    },
    "address": {
        "countryName": "Україна",
        "postalCode": "01220",
        "region": "м. Київ",
        "locality": "м. Київ",
        "streetAddress": "вул. Банкова, 11, корпус 1"
    },
    "contactPoint": {
        "name": "Державне управління справами",
        "telephone": "0440000000"
    },
    'kind': 'general'
}

procuring_entity_en = {
    "kind": "general",
    "address": {
        "countryName": "Україна",
        "locality": "м. Вінниця",
        "postalCode": "21027",
        "region": "Вінницька область",
        "streetAddress": "вул. Стахурського. 22"
    },
    "contactPoint": {
        "name": "Куца Світлана Валентинівна",
        "name_en": "Kutsa Svitlana V.",
        "telephone": "+380 (432) 46-53-02",
        "availableLanguage": "uk",
        "url": "http://sch10.edu.vn.ua/"
    },
    "identifier": {
        "id": "21725150",
        "legalName": "Заклад \"Загальноосвітня школа І-ІІІ ступенів № 10 Вінницької міської ради\"",
        "legalName_en": "The institution \"Secondary school I-III levels № 10 Vinnitsa City Council\"",
        "scheme": "UA-EDR"
    },
    "name": "ЗОСШ #10 м.Вінниці",
    "name_en": "School #10 of Vinnytsia"
}

procuring_entity_ua = {
    "kind": "special",
    "address": {
        "countryName": "Україна",
        "locality": "м. Вінниця",
        "postalCode": "21027",
        "region": "Вінницька область",
        "streetAddress": "вул. Стахурського. 22"
    },
    "contactPoint": {
        "name": "Куца Світлана Валентинівна",
        "telephone": "+380 (432) 46-53-02",
        "url": "http://sch10.edu.vn.ua/"
    },
    "identifier": {
        "id": "21725150",
        "legalName": "Заклад \"Загальноосвітня школа І-ІІІ ступенів № 10 Вінницької міської ради\"",
        "scheme": "UA-EDR"
    },
    "name": "ЗОСШ #10 м.Вінниці"
}

shortlisted_firms = [
    {
        "identifier": {
            "scheme": "UA-EDR",
            "id": '00137256',
            "uri": 'http://www.sc.gov.ua/'
        },
        "name": "ДКП «Школяр»"
    },
    {
        "identifier": {
            "scheme": "UA-EDR",
            "id": '00137226',
            "uri": 'http://www.sc.gov.ua/'
        },
        "name": "ДКП «Книга»"
    },
    {
        "identifier": {
            "scheme": "UA-EDR",
            "id": '00137228',
            "uri": 'http://www.sc.gov.ua/'
        },
        "name": "«Кенгуру»",
    },
]

award = {
    "status": "pending",
    "suppliers": [tenderer],
    "value": {
        "amount": 475000,
        "currency": "UAH",
        "valueAddedTaxIncluded": True
    }
}

tender_below_maximum = {
    "title": "футляри до державних нагород",
    "title_en": "Cases with state awards",
    "title_ru": "футляры к государственным наградам",
    "procuringEntity": procuring_entity,
    "value": {
        "amount": 500,
        "currency": "UAH"
    },
    "minimalStep": {
        "amount": 10,
        "currency": "UAH"
    },
    "items": items,
    "enquiryPeriod": {
        "endDate": (parse(MOCK_DATETIME) + timedelta(days=7)).isoformat()
    },
    "tenderPeriod": {
        "endDate": (parse(MOCK_DATETIME) + timedelta(days=14)).isoformat()
    },
    "procurementMethodType": "belowThreshold",
    "mode": "test",
    "features": features,
    "milestones": test_milestones,
    "mainProcurementCategory": "services",
}

tender_cfaselectionua_maximum = {
    "title": "футляри до державних нагород",
    "title_en": "Cases with state awards",
    "title_ru": "футляры к государственным наградам",
    "procuringEntity": {
        "name": "Державне управління справами",
        "identifier": {
            "scheme": "UA-EDR",
            "id": "00037256",
            "uri": "http://www.dus.gov.ua/"
        },
        "address": {
            "countryName": "Україна",
            "postalCode": "01220",
            "region": "м. Київ",
            "locality": "м. Київ",
            "streetAddress": "вул. Банкова, 11, корпус 1"
        },
        "contactPoint": {
            "name": "Державне управління справами",
            "telephone": "0440000000"
        },
        'kind': 'general'
    },
    "items": items,
    "procurementMethodType": "closeFrameworkAgreementSelectionUA",
    "mode": "test",
    "milestones": test_milestones,
    "mainProcurementCategory": "services",
}

tender_stage1 = {
    "tenderPeriod": {
        "endDate": "2016-02-11T14:04:18.962451"
    },
    "title": "Послуги шкільних їдалень",
    "title_en": "Services in school canteens",
    "minimalStep": {
        "currency": "UAH",
        "amount": 10
    },
    "procurementMethodType": "competitiveDialogueEU",
    "value": {
        "currency": "UAH",
        "amount": 500
    },
    "procuringEntity": procuring_entity_en,
    "items": items_en_unit,
    "milestones": test_milestones,
    "mainProcurementCategory": "services",
}

tender_stage2_multiple_lots = {
    "procurementMethod": "selective",
    "dialogue_token": sha512('secret'.encode()).hexdigest(),
    "title": "Послуги шкільних їдалень",
    "title_en": "Services in school canteens",
    "minimalStep": {
        "currency": "UAH",
        "amount": 10
    },
    "procurementMethodType": "competitiveDialogueEU.stage2",
    "value": {
        "currency": "UAH",
        "amount": 500
    },
    "shortlistedFirms": shortlisted_firms,
    "owner": "broker",
    "procuringEntity": procuring_entity_en,
    "items": items_en_unit
}

tender_stage2EU = {
    "title": "Послуги шкільних їдалень",
    "title_en": "Services in school canteens",
    "procurementMethod": "selective",
    "minimalStep": {
        "currency": "UAH",
        "amount": 10
    },
    "status": "draft",
    "procurementMethodType": "competitiveDialogueEU.stage2",
    "value": {
        "currency": "UAH",
        "amount": 500
    },
    "dialogue_token": "",
    "shortlistedFirms": shortlisted_firms,
    "owner": "broker",
    "procuringEntity": procuring_entity_en,
    "items": items_en_unit
}

tender_stage2UA = {
    "title": "футляри до державних нагород",
    "minimalStep": {
        "currency": "UAH",
        "amount": 10
    },
    "procurementMethod": "selective",
    "procurementMethodType": "competitiveDialogueUA.stage2",
    "value": {
        "currency": "UAH",
        "amount": 500
    },
    "status": "draft",
    "shortlistedFirms": shortlisted_firms,
    "owner": "broker",
    "procuringEntity": procuring_entity_ua,
    "items": items_ua_unit
}

tender_limited = {
    "items": items_ua,
    "owner": "broker",
    "procurementMethod": "limited",
    "procurementMethodType": "reporting",
    "status": "active",
    "procuringEntity": procuring_entity_ua,
    "value": {
        "amount": 500000,
        "currency": "UAH",
        "valueAddedTaxIncluded": True
    },
    "title": "Послуги шкільних їдалень",
    "title_en": "Services in school canteens",
    "title_ru": "Услуги школьных столовых",
    "description_en": "Services in school canteens",
    "description_ru": "Услуги школьных столовых",
    "milestones": test_milestones,
    "mainProcurementCategory": "services",
}

tender_openeu = {
    "tenderPeriod": {
        "endDate": (parse(MOCK_DATETIME) + timedelta(days=31)).isoformat()
    },
    "title": "Послуги шкільних їдалень",
    "title_en": "Services in school canteens",
    "minimalStep": {
        "currency": "UAH",
        "amount": 10
    },
    "procurementMethodType": "aboveThresholdEU",
    "value": {
        "currency": "UAH",
        "amount": 500
    },
    "procuringEntity": procuring_entity_en,
    "items": items_en,
    "milestones": test_milestones,
    "mainProcurementCategory": "services",
}

tender_openua = {
    "tenderPeriod": {
        "endDate": (parse(MOCK_DATETIME) + timedelta(days=31)).isoformat()
    },
    "title": "футляри до державних нагород",
    "minimalStep": {
        "currency": "UAH",
        "amount": 10
    },
    "procurementMethodType": "aboveThresholdUA",
    "value": {
        "currency": "UAH",
        "amount": 500
    },
    "procuringEntity": procuring_entity_ua,
    "items": items_ua,
    "milestones": test_milestones,
    "mainProcurementCategory": "services",
}

tender_esco = {
    "tenderPeriod": {
        "endDate": (parse(MOCK_DATETIME) + timedelta(days=31)).isoformat()
    },
    "title": "Послуги шкільних їдалень",
    "title_en": "Services in school canteens",
    "procurementMethodType": "esco",
    "minimalStepPercentage": 0.006,
    "procuringEntity": procuring_entity_en,
    "items": items_en_unit,
    "NBUdiscountRate": 0.22986,
    "fundingKind": "other",
    "yearlyPaymentsPercentageRange": 0.8,
    "milestones": test_milestones,
    "mainProcurementCategory": "services",
}

tender_defense = {
    "tenderPeriod": {
        "endDate": (parse(MOCK_DATETIME) + timedelta(days=26)).isoformat()
    },
    "title": "футляри до державних нагород",
    "minimalStep": {
        "currency": "UAH",
        "amount": 10
    },
    "procurementMethodType": "aboveThresholdUA.defense",
    "value": {
        "currency": "UAH",
        "amount": 500
    },
    "procuringEntity": procuring_entity_ua,
    "items": items_ua,
    "milestones": test_milestones,
    "mainProcurementCategory": "services",
}


plan = {
    "tender": {
        "procurementMethod": "open",
        "procurementMethodType": "belowThreshold",
        "tenderPeriod": {"startDate": (parse(MOCK_DATETIME) + timedelta(days=7)).isoformat()},
    },
    "items": [
        {
            "deliveryDate": {"endDate": (parse(MOCK_DATETIME) + timedelta(days=15)).isoformat()},
            "additionalClassifications": [{"scheme": "ДКПП", "id": "01.11.92", "description": "Насіння гірчиці"}],
            "unit": {"code": "KGM", "name": "кг"},
            "classification": {"scheme": "ДК021", "description": "Mustard seeds", "id": "03111600-8"},
            "quantity": 1000,
            "description": "Насіння гірчиці",
        },
        {
            "deliveryDate": {"endDate": (parse(MOCK_DATETIME) + timedelta(days=16)).isoformat()},
            "additionalClassifications": [{"scheme": "ДКПП", "id": "01.11.95", "description": "Насіння соняшнику"}],
            "unit": {"code": "KGM", "name": "кг"},
            "classification": {"scheme": "ДК021", "description": "Sunflower seeds", "id": "03111300-5"},
            "quantity": 2000,
            "description": "Насіння соняшнику",
        },
        {
            "deliveryDate": {"endDate": (parse(MOCK_DATETIME) + timedelta(days=17)).isoformat()},
            "additionalClassifications": [{"scheme": "ДКПП", "id": "01.11.84", "description": "Насіння бавовнику"}],
            "unit": {"code": "KGM", "name": "кг"},
            "classification": {"scheme": "ДК021", "description": "Cotton seeds", "id": "03111400-6"},
            "quantity": 3000,
            "description": "Насіння бавовнику",
        },
    ],
    "classification": {"scheme": "ДК021", "description": "Seeds", "id": "03111000-2"},
    "additionalClassifications": [{"scheme": "КЕКВ", "id": "1", "description": "-"}],
    "procuringEntity": {
        "identifier": {"scheme": "UA-EDR", "id": "111983", "legalName": "ДП Державне Управління Справами"},
        "name": "ДУС",
    },
    "buyers": [
        {
            "identifier": {"scheme": "UA-EDR", "id": "111983", "legalName": "ДП Державне Управління Справами"},
            "name": "ДУС",
        }
    ],
    "budget": {
        "project": {"name": "proj_name", "id": "123"},
        "amount": 10000,
        "amountNet": 12222,
        "currency": "UAH",
        "id": "12303111000-2",
        "description": "budget_description",
        "period": {
            "startDate": datetime(year=parse(MOCK_DATETIME).year, month=1, day=1).isoformat(),
            "endDate": datetime(year=parse(MOCK_DATETIME).year, month=12, day=31).isoformat(),
        },
        "breakdown": [
            {
                "title": "other",
                "description": "Breakdown other description.",
                "value": {"amount": 1500, "currency": "UAH"},
            }
        ],
    },
}


test_eligible_evidence_data = {
    "title": "Документальне підтвердження",
    "description": "Довідка в довільній формі",
    "type": "document",
}


test_requirement_data = {
    "dataType": "boolean",
    "eligibleEvidences": [test_eligible_evidence_data],
    "expectedValue": "true",
    "title": "Фізична особа, яка є учасником процедури закупівлі, "
             "не була засуджена за злочин, учинений з корисливих мотивів "
             "(зокрема, пов'язаний з хабарництвом та відмиванням коштів), "
             "судимість з якої знято або погашено у встановленому законом порядку",
}

test_requirement_group_data = {
    "requirements": [test_requirement_data],
    "description": "Учасник фізична особа підтверджує, що"
}


test_criterion_data = {
    "requirementGroups": [test_requirement_group_data],
    "description": "Службова (посадова) особа учасника процедури закупівлі, яка підписала тендерну пропозицію "
                   "(або уповноважена на підписання договору в разі переговорної процедури закупівлі) або фізична особа, "
                   "яка є учасником процедури закупівлі, не була засуджена за злочин, "
                   "учинений з корисливих мотивів (зокрема, пов'язаний з хабарництвом та відмиванням коштів), "
                   "судимість з якої знято або погашено у встановленому законом порядку",
    "classification": {
      "scheme": " espd211",
      "id": "CRITERION.EXCLUSION.CONVICTIONS.FRAUD"
    },
    "title": "Вчинення злочинів, учинених з корисливих мотивів",
    "relatesTo": "tenderer",
    "legislation": [
      {
        "article": "17.1.5",
        "version": "2020-04-19",
        "type": "NATIONAL_LEGISLATION",
        "identifier": {
          "uri": "https://zakon.rada.gov.ua/laws/show/922-19",
          "id": "922-VIII",
          "legalName": "Закон України \"Про публічні закупівлі\""
        }
      },
      {
        "article": "17.1.6",
        "version": "2020-04-19",
        "type": "NATIONAL_LEGISLATION",
        "identifier": {
          "uri": "https://zakon.rada.gov.ua/laws/show/922-19",
          "id": "922-VIII",
          "legalName": "Закон України \"Про публічні закупівлі\""
        }
      }
    ],
    "source": "tenderer",
}
