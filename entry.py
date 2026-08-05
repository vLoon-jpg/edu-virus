#!/usr/bin/env python3
"""
Hydra v4 — PyInstaller entry point.
Minimal bootstrap, delegates to hydra.core.main()
"""
import sys
import os

# Determine build profile from args or env
profile = "stealth"
if "--dev" in sys.argv:
    profile = "dev"
elif "--demo" in sys.argv:
    profile = "demo"
elif "--silent" in sys.argv:
    profile = "stealth"
elif "HYDRA_PROFILE" in os.environ:
    profile = os.environ["HYDRA_PROFILE"]

# Suppress PyInstaller bootstrap output
if profile == "stealth":
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')

try:
    from hydra.core import main
    main(profile=profile)
except Exception as e:
    # Last-resort fallback — write minimal process
    import tempfile
    try:
        with open(os.path.join(tempfile.gettempdir(), ".hydra_crash.log"), "a") as f:
            f.write(f"[{__import__('time').ctime()}] CRASH: {e}\n")
    except:
        pass
