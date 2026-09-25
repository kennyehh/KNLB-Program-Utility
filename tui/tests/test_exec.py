from backend.exec import run_command


def test_run_command_success():
    result = run_command(["echo", "hello"])
    assert result.ok
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_run_command_failure():
    result = run_command(["false"])
    assert not result.ok
    assert result.returncode != 0


def test_run_command_missing_binary():
    result = run_command(["definitely-not-a-real-command-xyz"])
    assert not result.ok
    assert result.returncode == 127


def test_run_command_does_not_hang_on_stdin():
    # `cat` with no args reads stdin until EOF; stdin is DEVNULL so this
    # must return immediately instead of blocking forever.
    result = run_command(["cat"], timeout=5)
    assert result.returncode == 0


def test_run_command_shell():
    result = run_command("echo a && echo b", use_shell=True)
    assert result.ok
    assert "a" in result.stdout
    assert "b" in result.stdout
