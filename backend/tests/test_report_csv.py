import csv
from io import StringIO

import pytest

from apps.insights.reports import csv_document, safe_csv_cell


@pytest.mark.parametrize(
    "value",
    [
        "=1+2",
        "+SUM(1)",
        "-1+2",
        "@SUM(A1)",
        "  =1",
        "\tplain",
        " \rplain",
        "\n=1",
        "\ufeff=1",
        "\x00=1",
        "＝1",
        "＋1",
        "－1",
        "＠1",
        "\u2003=1",
    ],
)
def test_neutralizes_formula_prefixes(value):
    assert safe_csv_cell(value) == "'" + value


def test_csv_quotes_delimiters_newlines_and_embedded_quotes():
    values = ['Cabaña;"ficticia"\n=1+2', '=";=1+2', "100.25", "Reserva ficticia"]
    content = csv_document(["Nombre", "Prueba", "Monto", "Texto"], [values])
    assert content.startswith("\ufeff")
    rows = list(csv.reader(StringIO(content.lstrip("\ufeff")), delimiter=";"))
    assert rows[1] == [values[0], "'" + values[1], values[2], values[3]]
