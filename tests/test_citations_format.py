"""Normalización de citas: variantes de proveedor → formato canónico [d:c]."""
from bibliotecario.ingest import citations_format as CF


def test_parse_todas_las_variantes():
    for text in ["[5:7]", "[doc:1:chunk:42]", "[doc:1, chunk:42]",
                 "[doc: 2, chunk: 86]", "[1, chunk 7]", "[doc:3:chunk:15]"]:
        assert len(CF.parse_citations(text)) == 1, text


def test_parse_dedup_y_orden():
    assert CF.parse_citations("[1:2] texto [3:4] y otra vez [1:2]") == [(1, 2), (3, 4)]


def test_no_confunde_ratios_con_citas():
    assert CF.parse_citations("ratio 3:4 y 5:6 sin corchetes") == []
    assert not CF.has_citation("el score es 0.85")


def test_normalize_reescribe_conservando_texto():
    out = CF.normalize_citations("Antes [doc: 2, chunk: 86] y [5:7] después.")
    assert out == "Antes [2:86] y [5:7] después."


def test_has_citation():
    assert CF.has_citation("cita [1:2]")
    assert not CF.has_citation("sin citas aquí")
    assert CF.has_citation("") is False


def test_lista_de_citas_en_un_solo_corchete():
    """El agente escribe [1:1, 1:6]; antes la metrica de provenance daba 0."""
    assert CF.parse_citations("**WN18RR** [1:1, 1:6]") == [(1, 1), (1, 6)]
    assert CF.parse_citations("[1:1, 1:6, 2:3]") == [(1, 1), (1, 6), (2, 3)]
    assert CF.parse_citations("[1:1,1:6;2:3]") == [(1, 1), (1, 6), (2, 3)]
    assert CF.has_citation("[1:1, 1:6]")


def test_lista_no_inventa_citas_por_razones():
    """Un ratio fuera de corchetes no es una cita, aunque tenga forma de d:c."""
    assert CF.parse_citations("mejoró con un ratio 3:1") == []
    assert CF.parse_citations("citas [1:2, 1:3] tras un ratio 4:1") == [(1, 2), (1, 3)]
    assert CF.parse_citations("ganó 2:1 en la final y 3:1 en la semifinal") == []


def test_lista_y_forma_simple_no_se_duplican():
    assert CF.parse_citations("[1:2] y [1:2, 1:3]") == [(1, 2), (1, 3)]
