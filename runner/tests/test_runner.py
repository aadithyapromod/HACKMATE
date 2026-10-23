from runner.runner import build_project, BuildResult


def test_build_project_scaffold():
    res = build_project("project-test-1", "./generated")
    assert isinstance(res, BuildResult)
    assert res.exit_code == 0
    assert res.success is True
    assert "project-test-1" in res.logs
