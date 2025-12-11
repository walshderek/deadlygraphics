INSERT_AFTER:
# === VIBE: DUMP COMPLETE HOOKS START ===
INSERT_TEXT:
    # === VIBE: SHOW SUMMARY START ===
    from modules.core import generate_summary_of_changes
    summary = generate_summary_of_changes()
    print("\\n=== SUMMARY OF IMPLEMENTED CHANGES ===")
    print(summary)
    print("=== END SUMMARY ===\\n")
    # === VIBE: SHOW SUMMARY END ===