from __future__ import annotations

import pathlib
import uuid
from typing import TYPE_CHECKING, Callable, Final

import pact
import pytest

from tests.integration.cloud.rest_contracts.conftest import ContractInteraction

if TYPE_CHECKING:
    from tests.integration.cloud.rest_contracts.conftest import PactBody

DATASOURCE_MIN_RESPONSE_BODY: Final[PactBody] = {
    "data": pact.Like(
        {
            "id": pact.Format().uuid,
        }
    )
}


@pytest.mark.cloud
@pytest.mark.parametrize(
    "contract_interaction",
    [
        ContractInteraction(
            method="PUT",
            upon_receiving="a request to add a Data Source",
            given="the Data Source does not exist",
            response_status=200,
            response_body=DATASOURCE_MIN_RESPONSE_BODY,
        ),
    ],
)
def test_datasource(
    contract_interaction: ContractInteraction,
    run_pact_test: Callable[[pathlib.Path, ContractInteraction], None],
    existing_organization_id: str,
) -> None:
    # the path to the endpoint relative to the base url
    path = pathlib.Path(
        "/", "organizations", existing_organization_id, "datasources", str(uuid.uuid4())
    )
    run_pact_test(path, contract_interaction)
