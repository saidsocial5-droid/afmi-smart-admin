import os
import sys
import time
import socket
import urllib.request
import webbrowser
import subprocess
from pathlib import Path

def find_available_port(start_port=8001):
    port = start_port
    while port < 65535:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            port += 1
    return 8001

def wait_for_server(url, max_seconds=15):
    start = time.time()
    while time.time() - start < max_seconds:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status in (200, 404):
                    return True
        except Exception:
            time.sleep(0.3)
    return False

def main():
    root_dir = Path(__file__).resolve().parent
    print("=" * 65)
    print(" 🌲 AFMI-SmartOffice | المكتب الذكي للجمعية (إفران - أزرو)")
    print("=" * 65)
    
    port = find_available_port(8001)
    server_url = f"http://127.0.0.1:{port}"
    print(f"[*] Port sélectionné : {port}")
    print(f"[*] Démarrage du serveur FastAPI sur {server_url} ...")
    
    # Save active port for electron/frontend
    port_file = root_dir / "backend" / "data" / ".backend_port"
    try:
        port_file.parent.mkdir(parents=True, exist_ok=True)
        port_file.write_text(str(port), encoding="utf-8")
    except Exception:
        pass

    # Run uvicorn server as background process
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(root_dir)
    )

    print("[*] Initialisation du backend et de la base de données...")
    if not wait_for_server(f"{server_url}/api/agents", max_seconds=15):
        print("[!] Avertissement : Le serveur prend plus de temps à répondre.")

    # Locate electron executable
    electron_exe = root_dir / "frontend" / "node_modules" / "electron" / "dist" / "electron.exe"
    electron_cmd = root_dir / "frontend" / "node_modules" / ".bin" / "electron.cmd"
    
    target_electron = None
    if electron_exe.exists():
        target_electron = str(electron_exe)
    elif electron_cmd.exists():
        target_electron = str(electron_cmd)

    use_electron = target_electron is not None and "--web-only" not in sys.argv

    if use_electron:
        print("[*] Lancement de l'application de bureau Electron...")
        env = os.environ.copy()
        env["BACKEND_PORT"] = str(port)
        try:
            electron_proc = subprocess.Popen(
                [target_electron, "electron/main.cjs"],
                cwd=str(root_dir / "frontend"),
                env=env
            )
            electron_proc.wait()
        except KeyboardInterrupt:
            pass
        finally:
            print("\n[*] Fermeture du serveur AFMI-SmartOffice.")
            backend_proc.terminate()
    else:
        print(f"[*] Ouverture du navigateur sur {server_url} ...")
        webbrowser.open(server_url)
        print("[*] Serveur actif. Appuyez sur Ctrl+C pour arrêter.")
        try:
            backend_proc.wait()
        except KeyboardInterrupt:
            print("\n[*] Arrêt du serveur AFMI-SmartOffice.")
            backend_proc.terminate()

if __name__ == "__main__":
    main()
