import subprocess
from pathlib import Path


def test_orchestrator_stops_when_sales_file_is_missing():
    repository_root = Path(__file__).resolve().parents[1]
    script_path = repository_root / "orchestration" / "run_daily_pipeline.ps1"

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            "-LoadDate",
            "2014-05-03",
        ],
        cwd=repository_root,
        capture_output=True,
        text=True,
        check=False,
    )

    output = f"{result.stdout}\n{result.stderr}"

    assert result.returncode == 1
    assert "Pipeline" in output
    assert "2014-05-03" in output
    assert "Fichier SalesOrderHeader introuvable" in output
    assert "Chargement Bronze" not in output