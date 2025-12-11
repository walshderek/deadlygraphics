INSERT_AFTER:
# === VIBECORE: START ===
INSERT_TEXT:
# === VIBECORE: COMMAND SUMMARY START ===
def generate_summary_of_changes():
    """
    Reads the git diff and prints a friendly summary for console display.
    """
    import subprocess
    try:
        diff = subprocess.check_output(["git", "diff", "--stat"], text=True)
        return diff.strip()
    except Exception as e:
        return f"[ERROR] Unable to produce summary: {e}"
# === VIBECORE: COMMAND SUMMARY END ===