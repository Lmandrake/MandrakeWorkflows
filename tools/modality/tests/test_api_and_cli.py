"""The public surface: estimate_modality, the report, and the CLI."""

import numpy as np
import pytest

from modality import COMPONENT_COUNT, VISIBLE_MODES, estimate_modality, get_case
from modality.cli import build_parser, load_samples, main


def test_estimate_modality_returns_both_numbers_separately():
    c = get_case("g2u_prior_hidden")           # 3 components, 2 visible modes
    res = estimate_modality(c.sample(4000, 0), run_bootstrap=False)
    assert res.n_samples == 4000
    assert isinstance(res.visible_modes, int)
    assert res.component_count is not None
    # the two questions are answered by differently-labelled methods
    assert res.methods["kde_stable"].kind == VISIBLE_MODES
    assert res.methods["gmm_bic"].kind == COMPONENT_COUNT


def test_report_names_the_definitional_split():
    res = estimate_modality(get_case("g2_sep4").sample(1000, 0), run_bootstrap=False)
    text = res.report()
    assert "VISIBLE MODES" in text
    assert "MIXTURE COMPONENTS" in text
    assert "a different question" in text


def test_headline_is_correct_on_obvious_cases():
    for name, expected in [("u_gaussian", 1), ("g2_sep6", 2), ("g3_wide", 3)]:
        res = estimate_modality(get_case(name).sample(3000, 0), run_bootstrap=False)
        assert res.visible_modes == expected, name


def test_too_few_samples_is_an_error_not_a_guess():
    with pytest.raises(ValueError):
        estimate_modality(np.arange(5.0))


def test_tiny_samples_are_flagged():
    res = estimate_modality(get_case("u_gaussian").sample(30, 0), run_bootstrap=False)
    assert any("n < 50" in n for n in res.notes)


def test_non_finite_values_are_dropped():
    x = np.concatenate([get_case("u_gaussian").sample(500, 0), [np.nan, np.inf, -np.inf]])
    res = estimate_modality(x, run_bootstrap=False)
    assert res.n_samples == 500


# ---------------------------------------------------------------------------
# file loading
# ---------------------------------------------------------------------------

def test_load_npy(tmp_path):
    x = get_case("g2_sep4").sample(300, 0)
    p = tmp_path / "s.npy"
    np.save(p, x)
    np.testing.assert_allclose(load_samples(p), x)


def test_load_plain_csv(tmp_path):
    x = get_case("g2_sep4").sample(300, 0)
    p = tmp_path / "s.csv"
    p.write_text("\n".join(f"{float(v):.17g}" for v in x), encoding="utf-8")
    np.testing.assert_allclose(load_samples(p), x, rtol=1e-12)


def test_load_csv_with_header_and_named_column(tmp_path):
    x = get_case("g2_sep4").sample(50, 0)
    p = tmp_path / "s.csv"
    lines = ["id,value"] + [f"{i},{float(v):.17g}" for i, v in enumerate(x)]
    p.write_text("\n".join(lines), encoding="utf-8")
    np.testing.assert_allclose(load_samples(p, "value"), x, rtol=1e-12)
    np.testing.assert_allclose(load_samples(p, 1), x, rtol=1e-12)


def test_multi_column_without_a_choice_is_refused(tmp_path):
    p = tmp_path / "s.csv"
    p.write_text("1.0,2.0\n3.0,4.0\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_samples(p)


def test_missing_file_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        load_samples(tmp_path / "nope.csv")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_list_cases(capsys):
    assert main(["list-cases"]) == 0
    out = capsys.readouterr().out
    assert "u_gaussian" in out and "g2u_prior_hidden" in out


def test_cli_truth_prints_exact_modes(capsys):
    assert main(["truth", "g4_pairs"]) == 0
    out = capsys.readouterr().out
    assert "components=4" in out and "true_modes=2" in out
    assert "prominence" in out


def test_cli_unknown_case_is_a_clean_error(capsys):
    assert main(["truth", "not_a_case"]) == 2
    assert "unknown test case" in capsys.readouterr().err


def test_cli_case_runs_end_to_end(capsys):
    assert main(["case", "g2_sep6", "-n", "800", "--no-bootstrap"]) == 0
    out = capsys.readouterr().out
    assert "GROUND TRUTH: 2 components, 2 visible modes" in out
    assert "VISIBLE MODES" in out


def test_cli_analyze_a_file(tmp_path, capsys):
    p = tmp_path / "s.npy"
    np.save(p, get_case("g3_wide").sample(1500, 0))
    assert main(["analyze", str(p), "--no-bootstrap"]) == 0
    out = capsys.readouterr().out
    assert "loaded 1500 samples" in out
    assert "VISIBLE MODES (local maxima of the density): 3" in out


def test_parser_rejects_no_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


# ---------------------------------------------------------------------------
# the headline consensus rule
# ---------------------------------------------------------------------------

def test_headline_takes_the_lower_of_the_two_mode_counters():
    from modality.api import MethodResult, VISIBLE_MODES, UNIMODALITY_TEST, _headline

    methods = {
        "kde_stable": MethodResult("kde_stable", VISIBLE_MODES, 3, {"locations": [0, 1, 2]}),
        "gmm_modes": MethodResult("gmm_modes", VISIBLE_MODES, 2, {"locations": [0, 1]}),
        "dip": MethodResult("dip", UNIMODALITY_TEST, 2, {"p_value": 0.001}),
    }
    value, _, notes = _headline(methods)
    assert value == 2
    assert any("taking the lower" in n for n in notes)


def test_dip_bumps_a_lone_mode_up_but_never_pushes_one_down():
    from modality.api import MethodResult, VISIBLE_MODES, UNIMODALITY_TEST, _headline

    def run(stable, gmm, dip_value, p):
        methods = {
            "kde_stable": MethodResult("kde_stable", VISIBLE_MODES, stable, {"locations": []}),
            "gmm_modes": MethodResult("gmm_modes", VISIBLE_MODES, gmm, {"locations": []}),
            "dip": MethodResult("dip", UNIMODALITY_TEST, dip_value, {"p_value": p}),
        }
        return _headline(methods)[0]

    # dip rejects unimodality while the counters say 1 -> raised to 2
    assert run(1, 1, 2, 0.0001) == 2
    # dip fails to reject -> the counters are left alone, not pushed down
    assert run(3, 3, 1, 0.9) == 3
    assert run(1, 1, 1, 0.9) == 1


def test_mode_locations_always_match_the_headline_count():
    from modality import estimate_modality, all_cases

    for name in ("u_gaussian", "g2_sep6", "g3_wide", "gu_adjacent"):
        res = estimate_modality(get_case(name).sample(2000, 0), run_bootstrap=False)
        assert res.mode_locations.size == res.visible_modes, name
