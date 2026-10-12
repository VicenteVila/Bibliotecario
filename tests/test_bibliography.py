"""Bibliografía extraída del propio texto: autores, año y sello de arXiv.

Los tests usan fixtures sintéticas que **replican la estructura real de los PDF
del corpus**, porque son esas particularidades las que rompían la extracción:
títulos partidos por `\n`, sello de arXiv girado en el margen (que el extractor
deja fuera del chunk 0), autores intercalados con afiliaciones, y superíndices
de afiliación pegados al nombre.
"""
from bibliotecario.ingest import bibliography as B

# réplica del doc 1: título, autores **intercalados** con afiliación y correo
_PEARL = (
    "PEARL: Path-Entity Aligned Relational Learning with Contextual\n"
    "Subgraphs for Inductive Knowledge Graph Completion\n"
    "Yunchi Yang\nSchool of Mathematics, Shandong University\n"
    "Jinan 250100, China\nycyang@mail.sdu.edu.cn\n"
    "Longlong Li∗\nSchool of Physical and Mathematical Sciences\n"
    "longlong.li@ntu.edu.sg\n"
    "Cunquan Qu∗\nData Science Institute, Shandong University\n"
    "cqqu@sdu.edu.cn\nSeptember 3, 2026\n"
    "Abstract\nLarge language models are increasingly deployed as agents.\n"
)
_PEARL_TITLE = ("PEARL: Path-Entity Aligned Relational Learning with Contextual "
                "Subgraphs for Inductive Knowledge Graph Completion")

# réplica del doc 2: todos los autores en una línea, con superíndices
_PROC = (
    "Procedural Graphs: Self-Evolving Execution\nStructures for LLM Agents\n"
    "Yuxing Lu1,2,3, Yicheng Chen1, Shanchan Wu1 and Sercan Ö. Arık1\n"
    "1Google, 2Georgia Institute of Technology, 3Peking University\n"
    "Large language models are increasingly deployed as agents that plan over\n"
)
_PROC_TITLE = "Procedural Graphs: Self-Evolving Execution Structures for LLM Agents"

# réplica del doc 3: sello de arXiv en el margen, **fuera** del chunk 0
_SELLO = "arXiv:2608.20169v2  [cs.CL]  24 Aug 2026"


def test_title_end_ignora_saltos_de_linea():
    """El PDF parte el título con `\n`; `documents.title` lo guarda en una línea."""
    assert B._title_end(_PEARL, _PEARL_TITLE) > 0
    assert B._title_end(_PROC, _PROC_TITLE) > 0


def test_title_end_con_sello_por_delante():
    """Los docs 5 y 6 traen un sello o un número de página antes del título."""
    head = "2026-08-28\n" + _PEARL
    assert B._title_end(head, _PEARL_TITLE) > len("2026-08-28")


def test_title_end_no_encontrado_devuelve_menos_uno():
    assert B._title_end(_PEARL, "Título que no aparece en el texto") == -1
    assert B._title_end(_PEARL, None) == -1


def test_autores_intercalados_con_afiliacion():
    """Cortar en la primera afiliación (doc 1) se dejaría la mitad de los autores."""
    assert B.extract_authors(_PEARL, title=_PEARL_TITLE) == [
        "Yunchi Yang", "Longlong Li", "Cunquan Qu",
    ]


def test_autores_en_una_linea_con_superindices():
    """`Lu1,2,3` lleva superíndices de afiliación; no son parte del nombre."""
    assert B.extract_authors(_PROC, title=_PROC_TITLE) == [
        "Yuxing Lu", "Yicheng Chen", "Shanchan Wu", "Sercan Ö. Arık",
    ]


def test_autores_con_iniciales_conservan_el_punto():
    text = ("Stop Comparing LLM Agents\nWithout Disclosing the Harness\n"
            "Yunbei Zhang1\nChandan K. Reddy4\n1Tulane University\n4Virginia Tech\n"
            "yzhang111@tulane.edu\nAbstract\nThis position paper argues that.\n")
    title = "Stop Comparing LLM Agents Without Disclosing the Harness"
    assert "Chandan K. Reddy" in B.extract_authors(text, title=title)


def test_no_atriba_lo_que_la_fuente_no_dice():
    """Sin bloque de autores no se devuelve nada: nada se rellena."""
    assert B.extract_authors(_PEARL[:120], title=_PEARL_TITLE) == []


def test_no_confunde_afiliacion_con_autor():
    text = ("Titulo Bastante Largo Para Pasar El Filtro De Longitud\n"
            "Virginia Tech\nPalo Alto\nMIT CSAIL\n"
            "1Tulane University\nAbstract\nTexto en prosa con palabras.\n")
    title = "Titulo Bastante Largo Para Pasar El Filtro De Longitud"
    assert B.extract_authors(text, title=title) == []


def test_no_atriba_el_titulo_por_autor():
    """El título va en inicial-mayúscula igual que un nombre: hay que quitarlo."""
    authors = B.extract_authors(_PEARL, title=_PEARL_TITLE)
    assert not any("PEARL" in a or "Subgraphs" in a for a in authors)


def test_sello_arxiv_extraido():
    stamp = B.extract_arxiv(_PEARL + "\nmas texto\n" + _SELLO)
    assert stamp == {
        "id": "2608.20169", "version": "v2", "category": "cs.CL",
        "date": "2026-08-24", "year": "2026",
    }


def test_sello_arxiv_gana_a_las_referencias():
    """Las referencias ajenas son ids sueltos, sin versión ni fecha: no valen."""
    text = _SELLO + "\n\nReferencias\n[1] Ver arXiv:1911.03082 para más detalle.\n"
    assert B.extract_arxiv(text)["id"] == "2608.20169"


def test_sin_sello_arxiv_devuelve_none():
    assert B.extract_arxiv("Texto sin ningún sello de arXiv aquí.") is None


def test_year_prefiere_el_sello():
    assert B.extract_year(_PEARL + "\n" + _SELLO) == "2026"


def test_year_sin_sello_devuelve_none_en_vez_de_adivinar():
    assert B.extract_year("Solo prosa, sin fechas ni sellos.") is None


def test_extract_bibliography_no_rellena_lo_vacio():
    assert B.extract_bibliography("Texto sin nada extraíble aquí dentro.") == {}


def test_merge_metadata_no_pisa_lo_ya_guardado():
    out = B.merge_metadata({"authors": ["Autor Viejo"]}, {"authors": ["Nuevo"], "year": "2026"})
    assert out["authors"] == ["Autor Viejo"] and out["year"] == "2026"


def test_format_citation_se_calla_donde_falta_dato():
    cita = B.format_citation({}, "Un título", 4)
    assert cita.startswith("(autores no extraídos)")
    assert "(4)" not in cita


def test_format_citation_con_et_al():
    meta = {"authors": ["A One", "B Two", "C Three", "D Four"], "year": "2026"}
    assert "et al." in B.format_citation(meta, "T")
