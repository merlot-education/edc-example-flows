"""
  Copyright 2024 Dataport. All rights reserved. Developed as part of the MERLOT project.
  
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at
  
      http://www.apache.org/licenses/LICENSE-2.0
  
  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.
"""
import time

import requests
from icecream import ic
import json
import uuid


CONTEXT = {
    "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
    "edc": "https://w3id.org/edc/v0.0.1/ns/",
    "odrl": "http://www.w3.org/ns/odrl/2/"
},

EDC_PREFIX = ""
ODRL_PREFIX = "odrl:"

edc1_headers = {
    'Content-Type': 'application/json',
    'X-API-Key': '1234'
}

edc2_headers = {
    'Content-Type': 'application/json',
    'X-API-Key': '5678'
}


def create_dataplane(transfer_url, public_api_url, connector_management_url, edc_headers, verbose=True):
    provider_dp_instance_data = {
        "edctype": "dataspaceconnector:dataplaneinstance",
        "id": "http-pull-provider-dataplane",
        "url": transfer_url,
        "allowedSourceTypes": ["HttpData"],
        "allowedDestTypes": ["HttpProxy", "HttpData"],
        "properties": {
            "publicApiUrl": public_api_url
        }
    }
    ic(provider_dp_instance_data)
    response = requests.post(connector_management_url + "instances",
                             headers=edc_headers,
                             data=json.dumps(provider_dp_instance_data))
    if verbose:
        ic(response.status_code, response.text)


def create_http_dataaddress(name, base_url):
    return {
            "@type": EDC_PREFIX + "DataAddress",
            EDC_PREFIX + "properties": {
                EDC_PREFIX + "name": name,
                EDC_PREFIX + "baseUrl": base_url,
                EDC_PREFIX + "type": "HttpData"
            }
        }


def create_http_proxy_dataaddress():
    return {
            "@type": EDC_PREFIX + "DataAddress",
            EDC_PREFIX + "properties": {
                EDC_PREFIX + "type": "HttpProxy"
            }
        }


def create_s3_dataaddress(name, bucket_name, container, blob_name, key_name, storage):
    return {
            "@type": EDC_PREFIX + "DataAddress",
            EDC_PREFIX + "name": name,
            EDC_PREFIX + "bucketName": bucket_name,
            EDC_PREFIX + "container": container,
            EDC_PREFIX + "blobName": blob_name,
            EDC_PREFIX + "keyName": key_name,
            EDC_PREFIX + "storage": storage,
            EDC_PREFIX + "type": "IonosS3"
        }


def create_asset(asset_id, asset_name, asset_description, asset_version, asset_contenttype, data_address,
                 connector_management_url, edc_headers, verbose=True):
    asset_data = {
        "@context": CONTEXT,
        "@id": asset_id,
        EDC_PREFIX + "properties": {
            EDC_PREFIX + "name": asset_name,
            EDC_PREFIX + "description": asset_description,
            EDC_PREFIX + "version": asset_version,
            EDC_PREFIX + "contenttype": asset_contenttype
        },
        EDC_PREFIX + "dataAddress": data_address
    }
    ic(asset_data)

    response = requests.post(connector_management_url + "v3/assets",
                             headers=edc_headers,
                             data=json.dumps(asset_data))
    if verbose:
        ic(response.status_code)
        ic(json.loads(response.text))
    # extract asset id from response
    return json.loads(response.text)["@id"]


def create_policy(policy_id, target_asset_id, connector_management_url, edc_headers, verbose=True):  # TODO for now we always use the same permissions
    policy_data = {
        "@context": CONTEXT,
        "@id": policy_id,
        EDC_PREFIX + "policy": {
            "@context": "http://www.w3.org/ns/odrl.jsonld",
            ODRL_PREFIX + "permission": [
                {
                    ODRL_PREFIX + "target": {
                        "@id": target_asset_id
                    },
                    ODRL_PREFIX + "action": {
                        ODRL_PREFIX + "type": "USE"
                    },
                    ODRL_PREFIX + "edctype": "dataspaceconnector:permission"
                }
            ],
            "@type": ODRL_PREFIX + "Set"
        }
    }

    ic(policy_data)

    response = requests.post(connector_management_url + "v2/policydefinitions",
                             headers=edc_headers,
                             data=json.dumps(policy_data))
    if verbose:
        ic(response.status_code, json.loads(response.text))
    return json.loads(response.text)["@id"]


def create_contract_definition(access_policy_id, contract_policy_id, asset_id, connector_management_url, edc_headers, verbose=True):  # TODO for now we use no selector (i.e. all assets are selected)
    contract_definition_data = {
        "@context": CONTEXT,
        "@type": EDC_PREFIX + "ContractDefinition",
        "@id": str(uuid.uuid4()),
        EDC_PREFIX + "accessPolicyId": access_policy_id,
        EDC_PREFIX + "contractPolicyId": contract_policy_id,
        EDC_PREFIX + "assetsSelector": [
            {
                EDC_PREFIX + "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
                EDC_PREFIX + "operator": "=",
                EDC_PREFIX + "operandRight": asset_id
            }
        ]
    }

    ic(contract_definition_data)

    response = requests.post(connector_management_url + "v2/contractdefinitions",
                             headers=edc_headers,
                             data=json.dumps(contract_definition_data))
    if verbose:
        ic(response.status_code, json.loads(response.text))


def query_catalog(provider_url, connector_management_url, edc_headers, verbose=True):
    catalog_request_data = {
        "@context": CONTEXT,
        EDC_PREFIX + "providerUrl": provider_url,
        EDC_PREFIX + "protocol": "dataspace-protocol-http"
    }

    ic(catalog_request_data)

    response = requests.post(connector_management_url + "v2/catalog/request",
                             headers=edc_headers,
                             data=json.dumps(catalog_request_data))
    if verbose:
        ic(response.status_code, json.loads(response.text))

    return json.loads(response.text)["dcat:dataset"]


def negotiate_offer(connector_id, consumer_id, provider_id, connector_address, offer_id, asset_id, policy,
                    connector_management_url, edc_headers, verbose=True):
    consumer_offer_data = {
        "@context": CONTEXT,
        "@type": EDC_PREFIX + "NegotiationInitiateRequestDto",
        EDC_PREFIX + "connectorId": connector_id,
        EDC_PREFIX + "consumerId": consumer_id,
        EDC_PREFIX + "providerId": provider_id,
        EDC_PREFIX + "connectorAddress": connector_address,
        EDC_PREFIX + "protocol": "dataspace-protocol-http",
        EDC_PREFIX + "offer": {
            "@type": EDC_PREFIX + "ContractOfferDescription",
            EDC_PREFIX + "offerId": offer_id,
            EDC_PREFIX + "assetId": asset_id,
            EDC_PREFIX + "policy": policy
        }
    }

    ic(consumer_offer_data)

    response = requests.post(connector_management_url + "v2/contractnegotiations",
                             headers=edc_headers,
                             data=json.dumps(consumer_offer_data))
    if verbose:
        ic(response.status_code, json.loads(response.text))

    # extract negotiation id
    return json.loads(response.text)["@id"]


def poll_negotiation_until_finalized(connector_management_url, negotiation_id, edc_headers, verbose=True):
    state = ""

    while state != "FINALIZED":
        ic("Requesting status of negotiation")
        response = requests.get(connector_management_url + "v2/contractnegotiations/" + negotiation_id,
                                headers=edc_headers)
        state = json.loads(response.text)[EDC_PREFIX + "state"]
        if verbose:
            ic(state)
        time.sleep(1)
    if verbose:
        ic(response.status_code, json.loads(response.text))
    return json.loads(response.text)[EDC_PREFIX + "contractAgreementId"]


def initiate_data_transfer(connector_id, connector_address, agreement_id, asset_id, data_destination,
                           connector_management_url, edc_headers, verbose=True):
    transfer_data = {
        "@context": CONTEXT,
        "@type": EDC_PREFIX + "TransferRequestDto",
        EDC_PREFIX + "connectorId": connector_id,
        EDC_PREFIX + "counterPartyAddress": connector_address,
        EDC_PREFIX + "contractId": agreement_id,
        EDC_PREFIX + "assetId": "something",  # TODO this should actually be the asset id but seems to be unused by the EDC currently
        EDC_PREFIX + "managedResources": False,
        EDC_PREFIX + "protocol": "dataspace-protocol-http",
        EDC_PREFIX + "dataDestination": data_destination
    }

    ic(transfer_data)

    response = requests.post(connector_management_url + "v2/transferprocesses",
                             headers=edc_headers,
                             data=json.dumps(transfer_data))
    if verbose:
        ic(response.status_code, json.loads(response.text))
    return json.loads(response.text)["@id"]


def poll_transfer_until_completed(connector_management_url, transfer_id, edc_headers, verbose=True):
    state = ""

    while state != "COMPLETED":
        ic("Requesting status of transfer")
        response = requests.get(connector_management_url + "v2/transferprocesses/" + transfer_id,
                                headers=edc_headers)
        state = json.loads(response.text)[EDC_PREFIX + "state"]
        if verbose:
            ic(state)
        time.sleep(1)

    if verbose:
        ic(response.status_code, json.loads(response.text))