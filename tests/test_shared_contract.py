import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import TypeAdapter
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

import app.models  # noqa: F401
from app.db.base import Base
from app.main import create_app
from app.schemas import auth, booking, catalog, common
from app.schemas.booking import ReservationCreate

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "docs/openapi.json").read_text("utf-8"))
SAMPLES = json.loads((ROOT / "docs/sample-catalog.json").read_text("utf-8"))["samples"]


def test_all_sixteen_models_match_canonical_ddl_columns_keys_and_foreign_keys():
    sql = (ROOT / "db/001_schema.sql").read_text("utf-8")
    definitions = dict(re.findall(r"CREATE TABLE (\w+) \((.*?)\) ENGINE=InnoDB", sql, re.S))
    assert len(definitions) == 16
    assert set(definitions) == set(Base.metadata.tables)
    for name, body in definitions.items():
        table = Base.metadata.tables[name]
        columns = set(
            re.findall(
                r"^\s+(\w+)\s+(?:BIGINT|VARCHAR|SMALLINT|INT|BOOLEAN|DATETIME|DATE|CHAR)\b",
                body,
                re.M,
            )
        )
        assert set(table.columns.keys()) == columns, name
        expected_fks = {
            (tuple(fields.split(", ")), parent, tuple(targets.split(", ")))
            for fields, parent, targets in re.findall(
                r"FOREIGN KEY \(([^)]+)\)\s+REFERENCES (\w+)\(([^)]+)\)", body
            )
        }
        actual_fks = {
            (
                tuple(fk.column_keys),
                fk.referred_table.name,
                tuple(element.column.name for element in fk.elements),
            )
            for fk in table.foreign_key_constraints
        }
        assert actual_fks == expected_fks, name
        primary = re.search(r"PRIMARY KEY \(([^)]+)\)", body)
        expected_pk = (
            primary.group(1).split(", ")
            if primary
            else [re.search(r"^\s+(\w+) [^\n]*PRIMARY KEY", body, re.M).group(1)]
        )
        assert list(table.primary_key.columns.keys()) == expected_pk, name
        # SQL로 컴파일할 수 있는지도 확인한다. 실제 MySQL 실행 검증과는 구분한다.
        assert str(CreateTable(table).compile(dialect=mysql.dialect()))


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda sample: sample["file"])
def test_frontend_samples_match_the_api_response_contract(sample):
    operation = SPEC["paths"][sample["path"]][sample["method"]]
    schema = operation["responses"][str(sample["status"])]["content"]["application/json"]["schema"]
    payload = json.loads(
        (ROOT / "app/static/samples" / f"{sample['file']}.json").read_text("utf-8")
    )
    Draft202012Validator(
        schema | {"components": SPEC["components"]}, format_checker=FormatChecker()
    ).validate(payload)


@pytest.mark.parametrize("sample", SAMPLES, ids=lambda sample: sample["file"])
def test_shared_pydantic_models_accept_contract_samples(sample):
    operation = SPEC["paths"][sample["path"]][sample["method"]]
    schema = operation["responses"][str(sample["status"])]["content"]["application/json"]["schema"]
    payload = json.loads(
        (ROOT / "app/static/samples" / f"{sample['file']}.json").read_text("utf-8")
    )

    def model_for(reference):
        name = reference.rsplit("/", 1)[1]
        return next(
            getattr(module, name)
            for module in (auth, booking, catalog, common)
            if hasattr(module, name)
        )

    if "$ref" in schema:
        result = model_for(schema["$ref"]).model_validate(payload)
    elif schema["type"] == "array":
        result = TypeAdapter(list[model_for(schema["items"]["$ref"])]).validate_python(payload)
    else:
        result = common.Page[
            model_for(schema["properties"]["items"]["items"]["$ref"])
        ].model_validate(payload)
    assert result is not None


def test_running_api_contains_only_marked_implemented_operations():
    actual = create_app().openapi()["paths"]
    expected = {
        ("/api/v1" + path, method)
        for path, methods in SPEC["paths"].items()
        for method, operation in methods.items()
        if operation.get("x-implementation-status") == "implemented"
    }
    assert {(path, method) for path, methods in actual.items() for method in methods} == expected


@pytest.mark.parametrize("seat_ids,count", [([101, 101], 2), ([101], 2)])
def test_shared_reservation_schema_rejects_duplicate_and_incomplete_selection(seat_ids, count):
    with pytest.raises(ValueError):
        ReservationCreate(
            run_id=501,
            boarding_run_stop_id=5011,
            alighting_run_stop_id=5013,
            passenger_count=count,
            seat_ids=seat_ids,
        )
