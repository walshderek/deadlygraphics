INSERT_AFTER:
        print(f"[VIBECODER] Dispatching to App Manager: {app_name}")
        cmd = [sys.executable, str(manager_script), app_name, repo_url]
        subprocess.run(cmd)

    else:
        print(f"[ERROR] Unknown mode: {mode}")
INSERT_TEXT:
    elif mode == "install-suite":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: python3 DG_vibecoder.py install-suite <suite_name>")
            print("Available suites: DG_AI")
            return
        
        suite_name = sys.argv[2]
        
        # Dispatch to the App Manager Module with --suite flag
        manager_script = MODULES_DIR / "DG_app_manager.py"
        if not manager_script.exists():
            print(f"[ERROR] Module not found: {manager_script}")
            return

        print(f"[VIBECODER] Dispatching Suite Install: {suite_name}")
        cmd = [sys.executable, str(manager_script), "--suite", suite_name]
        subprocess.run(cmd)