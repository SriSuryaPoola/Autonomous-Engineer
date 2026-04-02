import subprocess
import sys
import os
import time

def start_platform():
    print("=" * 60)
    print("🚀 HiClaw | Autonomous Engineering Platform Launcher")
    print("=" * 60)
    
    # 1. Start Backend (FastAPI)
    print("\n[1/3] Starting FastAPI Backend on port 8000...")
    backend_proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"],
                                   cwd=os.getcwd())
    
    time.sleep(2)
    
    # 2. Start Frontend (Simple HTTP Server for Vanilla SPA)
    print("[2/3] Serving UI on port 3000...")
    frontend_proc = subprocess.Popen([sys.executable, "-m", "http.server", "3000"],
                                    cwd=os.path.join(os.getcwd(), "ui"))
    
    # 3. Open Browser
    print("[3/3] Opening browser at http://localhost:3000")
    import webbrowser
    webbrowser.open("http://localhost:3000")
    
    print("\n" + "=" * 60)
    print("Dashboard is LIVE! Press Ctrl+C in this terminal to shutdown.")
    print("=" * 60)
    
    try:
        backend_proc.wait()
        frontend_proc.wait()
    except KeyboardInterrupt:
        print("\nShutting down platform processes...")
        backend_proc.terminate()
        frontend_proc.terminate()

if __name__ == "__main__":
    start_platform()
