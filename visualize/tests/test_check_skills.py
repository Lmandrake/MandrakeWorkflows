import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import check_skills  # noqa: E402

GOOD_DESC = (
    "Design and run a head-to-head comparison whose result you can believe. "
    "Use this whenever you are about to claim one approach beats another, "
    "when benchmarking a library against an alternative, or when a result "
    "looks suspiciously clean and you need to check whether it holds up."
)


def write_skill(tmp_path, name, body="", desc=GOOD_DESC, lines=0):
    d = tmp_path / name
    d.mkdir()
    filler = "\n".join(f"line {i}" for i in range(lines))
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: >\n  {desc}\n---\n\n# Title\n{body}\n{filler}\n"
    )
    return d / "SKILL.md"


def test_accepts_a_wellformed_skill(tmp_path):
    md = write_skill(tmp_path, "good-skill")
    assert check_skills.check_skill(md, check_skills.tracked_files()) == []


def test_flags_untracked_cited_path(tmp_path):
    md = write_skill(
        tmp_path, "leaky-skill", body="See ~/dev/MandrakeWorkflows/visualize/untracked_dir/data.csv"
    )
    problems = check_skills.check_skill(md, check_skills.tracked_files())
    assert any("not git-tracked" in p and "untracked_dir" in p for p in problems)


def test_accepts_tracked_cited_path(tmp_path):
    md = write_skill(
        tmp_path, "citing-skill", body="See ~/dev/MandrakeWorkflows/visualize/DESIGN.md for the rule."
    )
    assert check_skills.check_skill(md, check_skills.tracked_files()) == []


def test_accepts_tracked_directory_citation(tmp_path):
    md = write_skill(
        tmp_path,
        "dir-skill",
        body="Read ~/dev/MandrakeWorkflows/visualize/principles/ in order.",
    )
    assert check_skills.check_skill(md, check_skills.tracked_files()) == []


def test_flags_name_directory_mismatch(tmp_path):
    d = tmp_path / "actual-dir"
    d.mkdir()
    (d / "SKILL.md").write_text(
        f"---\nname: different-name\ndescription: >\n  {GOOD_DESC}\n---\n\n# Title\n"
    )
    problems = check_skills.check_skill(d / "SKILL.md", check_skills.tracked_files())
    assert any("!=" in p for p in problems)


def test_flags_oversized_skill(tmp_path):
    md = write_skill(tmp_path, "fat-skill", lines=300)
    problems = check_skills.check_skill(md, check_skills.tracked_files())
    assert any("250-line budget" in p for p in problems)


def test_flags_thin_description(tmp_path):
    md = write_skill(tmp_path, "terse-skill", desc="Does evaluation stuff.")
    problems = check_skills.check_skill(md, check_skills.tracked_files())
    assert any("description" in p for p in problems)


def test_main_exits_nonzero_on_failure(tmp_path):
    write_skill(tmp_path, "leaky-skill", body="~/dev/MandrakeWorkflows/visualize/untracked_dir/x.csv")
    result = subprocess.run(
        [sys.executable, str(REPO / "tools" / "check_skills.py"), str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "FAIL" in result.stdout


def test_does_not_fold_hyphenated_key_into_previous_value(tmp_path):
    d = tmp_path / "hyphen-skill"
    d.mkdir()
    (d / "SKILL.md").write_text(
        "---\nname: hyphen-skill\nallowed-tools: Read, Grep\n"
        f"description: >\n  {GOOD_DESC}\n---\n\n# Title\n"
    )
    fields = check_skills.parse_frontmatter((d / "SKILL.md").read_text())
    assert fields["name"] == "hyphen-skill"
    assert fields["allowed-tools"] == "Read, Grep"
    assert check_skills.check_skill(d / "SKILL.md", check_skills.tracked_files()) == []


def test_flags_untracked_absolute_path_form(tmp_path):
    md = write_skill(
        tmp_path,
        "abs-leak-skill",
        body=f"See {check_skills.REPO}/untracked_dir/data.csv",
    )
    problems = check_skills.check_skill(md, check_skills.tracked_files())
    assert any("not git-tracked" in p for p in problems)


def test_flags_a_skill_that_names_a_renderer(tmp_path):
    md = write_skill(tmp_path, "toolkit-skill", body="Render the city with Potree and glow.")
    problems = check_skills.check_skill(md, check_skills.tracked_files())
    assert any("names renderer" in p and "Potree" in p for p in problems)


def test_renderer_names_match_whole_words_only(tmp_path):
    md = write_skill(tmp_path, "word-skill", body="A satiny finish; deck slides; gephiish.")
    assert check_skills.check_skill(md, check_skills.tracked_files()) == []


def test_every_visual_skill_is_a_default_root():
    visual = {
        d for d in check_skills.SKILLS_DIR.iterdir()
        if (d / "SKILL.md").exists()
        and (d.name.startswith("visual-") or d.name == "scientific-visualization")
    }
    assert len(visual) == 8
    assert visual == set(check_skills.DEFAULT_ROOTS)
