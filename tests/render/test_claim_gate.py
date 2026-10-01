"""The claim gate renders documents from the manifest and diffs whole files.

Three tests as for every gate (a clean render passes, a hand edit is caught, it refuses to run
on nothing), and the checks that keep numbers out of templates.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from turnaround_core.manifest import Manifest
from turnaround_core.statements import STATEMENT
from turnaround_render.render import ClaimGateError, Renderer, Target, hand_typed_numbers, table_html
from turnaround_render.targets import discover


def _manifest() -> Manifest:
    manifest = Manifest(as_of="2026-09-30", seed=1)
    manifest.put("ch1.on_time.2024", 0.7891, "pct1", source="real:bts", population="p", origin="o")
    manifest.put(
        "ch2.padding.change", 3.24, "smin1", source="real:bts", model="padding", population="p", origin="o"
    )
    manifest.put_table(
        "ch5.ranking",
        ["Carrier", "Raw", "Adjusted"],
        ["text", "min1", "min1"],
        [["DL", 4.21, -1.2], ["WN", 6.5, 0.3]],
        source="real:bts",
        model="fixed_effects",
        population="p",
        origin="o",
    )
    manifest.put_figure(
        "chart.ch1_definition",
        "On time held flat while schedules grew",
        "callout",
        source="real:bts",
        population="p",
        origin="o",
        sql="select 1",
    )
    return manifest


def _setup(tmp_path: Path) -> tuple[Renderer, Path]:
    templates = tmp_path / "docs" / "templates"
    templates.mkdir(parents=True)
    (templates / "RESULTS.md.j2").write_text(
        "# Results\n\nOn time in 2024 was {{ v('ch1.on_time.2024') }}; padding moved "
        "{{ v('ch2.padding.change') }}.\n\n{{ table('ch5.ranking') }}\n\n"
        "Chart: {{ message('ch1_definition') }}\n\n{{ statement() }}\n"
    )
    renderer = Renderer(tmp_path, _manifest(), discover(tmp_path), [templates])
    return renderer, tmp_path / "RESULTS.md"


def test_clean_render_passes(tmp_path: Path) -> None:
    renderer, out = _setup(tmp_path)
    renderer.write_all()
    text = out.read_text()
    assert "On time in 2024 was 78.9%" in text
    assert "padding moved +3.2 min" in text
    assert "Chart: On time held flat while schedules grew" in text
    assert STATEMENT in text
    assert renderer.check_all() == []


def test_a_number_edited_by_hand_is_caught(tmp_path: Path) -> None:
    renderer, out = _setup(tmp_path)
    renderer.write_all()
    out.write_text(out.read_text().replace("was 78.9%", "was 81.0%"))
    drifts = renderer.check_all()
    assert len(drifts) == 1
    assert "-On time in 2024 was 81.0%" in drifts[0].diff
    assert "+On time in 2024 was 78.9%" in drifts[0].diff


def test_a_missing_document_is_caught(tmp_path: Path) -> None:
    renderer, _ = _setup(tmp_path)
    assert renderer.check_all()[0].output == "RESULTS.md"


def test_refuses_with_no_documents(tmp_path: Path) -> None:
    with pytest.raises(ClaimGateError, match="no documents"):
        Renderer(tmp_path, _manifest(), [], [tmp_path])


def test_refuses_with_an_empty_manifest(tmp_path: Path) -> None:
    with pytest.raises(ClaimGateError, match="empty manifest"):
        Renderer(tmp_path, Manifest(as_of="2026-09-30", seed=1), [Target("a.j2", "a.md")], [tmp_path])


def test_unknown_key_fails_loudly(tmp_path: Path) -> None:
    renderer, _ = _setup(tmp_path)
    (tmp_path / "docs" / "templates" / "RESULTS.md.j2").write_text("{{ v('ch9.nothing') }}")
    with pytest.raises(KeyError):
        renderer.write_all()


def test_hand_typed_numbers_are_found_outside_expressions() -> None:
    text = "On time was {{ v('ch1.on_time') }} and the share was 0.81 under CC BY 4.0."
    assert hand_typed_numbers(text, ["CC BY 4.0"]) == ["0.81"]
    assert hand_typed_numbers("{{ v('a.b') }} only", []) == []


def test_partials_are_not_rendered_on_their_own(tmp_path: Path) -> None:
    templates = tmp_path / "story" / "templates" / "chapters"
    templates.mkdir(parents=True)
    (templates / "_01_definition.md.j2").write_text("x")
    (templates.parent / "story.md.j2").write_text("{% include 'chapters/_01_definition.md.j2' %}")
    targets = discover(tmp_path)
    assert [t.output for t in targets] == ["story/story.md"]


def test_template_names_must_be_unique_across_roots(tmp_path: Path) -> None:
    for root in ("docs/templates", "report/templates"):
        folder = tmp_path / root
        folder.mkdir(parents=True)
        (folder / "index.md.j2").write_text("x")
    with pytest.raises(ValueError, match="repeat across roots"):
        discover(tmp_path)


def test_reading_time_is_computed_in_two_passes(tmp_path: Path) -> None:
    templates = tmp_path / "story" / "templates"
    templates.mkdir(parents=True)
    words = " ".join(["word"] * 700)
    (templates / "story.md.j2").write_text("A {{ reading_minutes }} minute read.\n\n" + words + "\n")
    renderer = Renderer(tmp_path, _manifest(), discover(tmp_path), [templates])
    renderer.write_all()
    assert (tmp_path / "story" / "story.md").read_text().startswith("A 4 minute read.")


def test_table_html_right_aligns_numbers(tmp_path: Path) -> None:
    renderer, _ = _setup(tmp_path)
    html = table_html(renderer.manifest, "ch5.ranking")
    assert '<td class="num">4.2 min</td>' in html
    assert '<th class="txt">Carrier</th>' in html
