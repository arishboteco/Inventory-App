from tools.issue_migrator import parse_tasks, TASKS_PATH


def test_parse_tasks_titles():
    tasks = parse_tasks(TASKS_PATH)
    titles = [t["title"] for t in tasks]
    assert "Align requirements with service dependencies" in titles
    assert "Provide safe defaults for critical environment variables" in titles
    assert "Generalize database engine creation" in titles
    assert "Home Page" in titles
    assert "Dashboard" in titles
