"""
Static analysis tool runners for the debate agents.

- Lizard (complexity metrics): used by the performance agent.
- Semgrep (security scan): used by the security agent. Optional; gracefully
  degrades when the CLI is not installed.
"""

import json
import os
import shutil
import subprocess
import tempfile


LANG_EXTENSIONS = {
    "python": ".py",
    "javascript": ".js",
    "typescript": ".ts",
    "java": ".java",
    "go": ".go",
    "rust": ".rs",
    "c": ".c",
    "cpp": ".cpp",
    "c++": ".cpp",
    "ruby": ".rb",
    "php": ".php",
    "swift": ".swift",
    "kotlin": ".kt",
    "scala": ".scala",
}


def _write_snippet(code: str, language: str) -> str:
    """Write code to a temp file with the correct extension. Returns path."""
    ext = LANG_EXTENSIONS.get(language.lower().strip(), ".txt")
    fd, path = tempfile.mkstemp(suffix=ext, prefix="debate_")
    with os.fdopen(fd, "w") as f:
        f.write(code)
    return path


# ---------------------------------------------------------------------------
# Lizard — complexity metrics (always available as a pip dependency)
# ---------------------------------------------------------------------------

def run_lizard(code: str, language: str) -> str:
    """Return a short summary of per-function complexity metrics, or \"\"."""
    try:
        import lizard  # noqa: delayed import keeps startup fast
    except ImportError:
        return ""

    path = _write_snippet(code, language)
    try:
        analysis = lizard.analyze_file(path)
        funcs = analysis.function_list
        if not funcs:
            return "Lizard: no functions detected in snippet."

        lines = []
        for fn in funcs:
            lines.append(
                f"  {fn.name}: cyclomatic_complexity={fn.cyclomatic_complexity}, "
                f"nloc={fn.nloc}, tokens={fn.token_count}, "
                f"params={fn.parameter_count}, max_nesting={fn.top_nesting_level}"
            )
        return "Lizard complexity metrics:\n" + "\n".join(lines)
    except Exception:
        return ""
    finally:
        os.unlink(path)


# ---------------------------------------------------------------------------
# Semgrep — security scan (optional; requires `semgrep` CLI on PATH)
# ---------------------------------------------------------------------------

_SEMGREP_TIMEOUT = 60  # seconds


def run_semgrep(code: str, language: str) -> str:
    """Return a short summary of Semgrep findings, or \"\"."""
    if not shutil.which("semgrep"):
        return ""

    path = _write_snippet(code, language)
    try:
        result = subprocess.run(
            ["semgrep", "scan", "--config", "auto", "--json", "--quiet", path],
            capture_output=True,
            text=True,
            timeout=_SEMGREP_TIMEOUT,
        )
        if result.returncode != 0:
            return ""

        data = json.loads(result.stdout)
        findings = data.get("results", [])
        if not findings:
            return "Semgrep: no security issues detected."

        lines = []
        for f in findings[:5]:
            rule = f.get("check_id", "unknown").rsplit(".", 1)[-1]
            severity = f.get("extra", {}).get("severity", "INFO")
            msg = f.get("extra", {}).get("message", "")
            lines.append(f"  [{severity}] {rule}: {msg[:150]}")
        return "Semgrep security findings:\n" + "\n".join(lines)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return ""
    finally:
        os.unlink(path)
