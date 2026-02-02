import tkinter as tk
from tkinter import messagebox
from flask import Flask, request, jsonify
import os
from pathlib import Path
import threading
import configparser
import requests
import base64
import logging
import re

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Initialize Flask app
app = Flask(__name__)

# --- Centralized Configuration ---
PYPI_CONFIG = {
    "pypi": {
        "repository": "https://upload.pypi.org/legacy/",
        "test_url": "https://pypi.org/simple/",
        "token_regex": r"pypi-[a-zA-Z0-9]{32}"
    },
    "testpypi": {
        "repository": "https://test.pypi.org/legacy/",
        "test_url": "https://test.pypi.org/simple/",
        "token_regex": r"pypi-[a-zA-Z0-9]{32}"
    }
}

# --- Refactored Helper Function ---
def _create_pypirc_content(pypi_token, testpypi_token):
    """A helper function to generate the .pypirc string."""
    config_content = "[distutils]\nindex-servers =\n    pypi\n    testpypi\n\n"
    
    if pypi_token:
        config_content += "[pypi]\n"
        config_content += f"repository = {PYPI_CONFIG['pypi']['repository']}\n"
        config_content += "username = __token__\n"
        config_content += f"password = {pypi_token}\n\n"
    
    if testpypi_token:
        config_content += "[testpypi]\n"
        config_content += f"repository = {PYPI_CONFIG['testpypi']['repository']}\n"
        config_content += "username = __token__\n"
        config_content += f"password = {testpypi_token}\n"
        
    return config_content

# API endpoint to generate .pypirc file
@app.route('/generate-pypirc', methods=['POST'])
def generate_pypirc_api():
    try:
        data = request.get_json()
        pypi_token = data.get('pypi_token', '').strip()
        testpypi_token = data.get('testpypi_token', '').strip()

        logging.info("API request received to generate .pypirc file.")

        if not pypi_token and not testpypi_token:
            logging.warning("API request failed: At least one API token is required.")
            return jsonify({"error": "At least one API token is required"}), 400

        config_content = _create_pypirc_content(pypi_token, testpypi_token)

        home_dir = Path.home()
        pypirc_path = home_dir / ".pypirc"

        with open(pypirc_path, "w") as f:
            f.write(config_content)
        
        logging.info(f".pypirc file generated successfully at {pypirc_path} via API.")
        return jsonify({"message": f".pypirc file generated successfully at {pypirc_path}"}), 200

    except Exception as e:
        logging.error(f"API request failed to generate .pypirc file: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to generate .pypirc file: {str(e)}"}), 500

# Function to check .pypirc configuration and test connectivity (run in a separate thread)
def auth_check(status_label):
    results_window = tk.Toplevel(root)
    results_window.title("Test Results")
    results_window.geometry("500x350")
    results_text = tk.Text(results_window, wrap=tk.WORD, font=("Courier", 10))
    results_text.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    results_text.tag_configure("success", foreground="green")
    results_text.tag_configure("error", foreground="red")
    results_text.tag_configure("warn", foreground="orange")
    results_text.tag_configure("info", foreground="blue")
    
    def insert_line(text, tag=None):
        results_text.insert(tk.END, text + "\n", tag)
        results_text.see(tk.END)
        if tag == "error":
            logging.error(text)
        elif tag == "warn":
            logging.warning(text)
        else:
            logging.info(text)

    logging.info("Starting .pypirc configuration check.")
    status_label.config(text="Testing...")
    pypirc_path = Path.home() / ".pypirc"
    
    if not pypirc_path.exists():
        insert_line("❌ .pypirc file not found in your home directory.", "error")
        insert_line(f"   Expected at: {pypirc_path}", "info")
        status_label.config(text="Check complete.")
        return

    insert_line(f"✅ Found .pypirc at: {pypirc_path}", "success")
    
    config = configparser.ConfigParser()
    config.read(pypirc_path)

    if "distutils" not in config or "index-servers" not in config["distutils"]:
        insert_line("⚠️ Missing [distutils] section or index-servers list.", "warn")
        status_label.config(text="Check complete.")
        return

    servers = config["distutils"]["index-servers"].split()
    if not servers:
        insert_line("⚠️ No repositories listed under index-servers.", "warn")
        status_label.config(text="Check complete.")
        return

    insert_line("📦 Repositories configured:", "info")
    
    for server in servers:
        insert_line(f"  • Checking [{server}]", "info")
        if server not in config:
            insert_line(f"    ❌ Section [{server}] missing.", "error")
            continue
        
        repo_url = config[server].get("repository")
        user = config[server].get("username", "")
        pw = config[server].get("password", "")
        
        expected_url = PYPI_CONFIG.get(server, {}).get("repository")
        token_regex = PYPI_CONFIG.get(server, {}).get("token_regex")

        if not repo_url or repo_url != expected_url:
            insert_line(f"     ❌ Incorrect or missing 'repository' URL. Expected: {expected_url}", "error")
        
        if user != "__token__":
            insert_line(f"     ⚠️ username is not '__token__': {user}", "warn")
        
        if not pw:
            insert_line(f"     ⚠️ No password/token provided for {server}", "warn")
        elif not re.match(token_regex, pw):
            insert_line(f"     ⚠️ Password does not match expected token format.", "warn")
        
        test_url = PYPI_CONFIG.get(server, {}).get("test_url")
        if pw and user == "__token__" and test_url:
            try:
                insert_line(f"     🌐 Attempting to connect to {test_url}", "info")
                credentials = base64.b64encode(f"{user}:{pw}".encode()).decode()
                headers = {"Authorization": f"Basic {credentials}"}
                response = requests.get(test_url, headers=headers, timeout=10)
                
                if response.status_code == 200 and "Simple Index" in response.text:
                    insert_line(f"     ✅ Successfully authenticated and connected to {server}", "success")
                elif response.status_code == 200:
                    insert_line(f"     ⚠️ Connection successful, but did not find 'Simple Index'.", "warn")
                else:
                    insert_line(f"     ❌ Failed to authenticate with {server}: HTTP {response.status_code}", "error")
            except requests.RequestException as e:
                insert_line(f"     ❌ Failed to connect to {server}: {e}", "error")

    insert_line("\n✅ Auth config check complete.", "success")
    results_text.config(state=tk.DISABLED)
    status_label.config(text="Check complete.")
    logging.info("Auth config check finished.")

# New function to start the auth check in a new thread
def _start_auth_check():
    auth_thread = threading.Thread(target=auth_check, args=(status_label,))
    auth_thread.daemon = True
    auth_thread.start()

# GUI function to generate .pypirc file
def generate_pypirc_gui():
    pypi_token = pypi_entry.get().strip()
    testpypi_token = testpypi_entry.get().strip()
    
    logging.info("GUI request received to generate .pypirc file.")
    
    if not pypi_token and not testpypi_token:
        messagebox.showerror("Error", "Please enter at least one API token")
        logging.warning("GUI request failed: At least one API token is required.")
        return
    
    config_content = _create_pypirc_content(pypi_token, testpypi_token)
    
    try:
        home_dir = Path.home()
        pypirc_path = home_dir / ".pypirc"
        
        with open(pypirc_path, "w") as f:
            f.write(config_content)
        
        messagebox.showinfo("Success", f".pypirc file generated successfully at {pypirc_path}")
        logging.info(f".pypirc file generated successfully at {pypirc_path} via GUI.")
        clear_entries()
        
    except Exception as e:
        messagebox.showerror("Error", f"Failed to generate .pypirc file: {str(e)}")
        logging.error(f"GUI request failed to generate .pypirc file: {str(e)}", exc_info=True)

# Function to clear entries
def clear_entries():
    pypi_entry.delete(0, tk.END)
    testpypi_entry.delete(0, tk.END)
    logging.info("Entry fields cleared.")

# Create GUI
def start_gui():
    global root, status_label
    root = tk.Tk()
    root.title("PyPI .pypirc Generator v1.6 by Leon Priest")
    root.geometry("400x350")
    root.resizable(False, False)

    tk.Label(root, text="PyPI .pypirc File Generator", font=("Arial", 14, "bold")).pack(pady=10)

    tk.Label(root, text="PyPI API Token:").pack()
    global pypi_entry
    pypi_entry = tk.Entry(root, width=50, show="*")
    pypi_entry.pack(pady=5)

    tk.Label(root, text="TestPyPI API Token:").pack()
    global testpypi_entry
    testpypi_entry = tk.Entry(root, width=50, show="*")
    testpypi_entry.pack(pady=5)

    button_frame = tk.Frame(root)
    button_frame.pack(pady=10)
    
    generate_button = tk.Button(button_frame, text="Generate .pypirc", command=generate_pypirc_gui, bg="#4CAF50", fg="white")
    generate_button.pack(side=tk.LEFT, padx=5)
    
    test_button = tk.Button(button_frame, text="Test Configuration", command=_start_auth_check, bg="#2196F3", fg="white")
    test_button.pack(side=tk.LEFT, padx=5)

    clear_button = tk.Button(button_frame, text="Clear", command=clear_entries, bg="#f44336", fg="white")
    clear_button.pack(side=tk.LEFT, padx=5)

    status_label = tk.Label(root, text="", font=("Arial", 10, "italic"))
    status_label.pack(pady=5)

    tk.Label(root, text="Note: Tokens will be saved in ~/.pypirc\nAt least one token is required\nAPI available at http://localhost:5000/generate-pypirc", 
             font=("Arial", 8), justify="center").pack(pady=10)

    root.mainloop()

# Run Flask in a separate thread
def run_flask(host, port):
    logging.info(f"Starting Flask server on http://{host}:{port}...")
    app.run(host=host, port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    logging.info("Application starting...")
    
    config = configparser.ConfigParser()
    config.read('config.ini')
    flask_host = config.get('flask', 'host', fallback='127.0.0.1')
    flask_port = config.getint('flask', 'port', fallback=5000)

    flask_thread = threading.Thread(target=run_flask, args=(flask_host, flask_port))
    flask_thread.daemon = True
    flask_thread.start()
    
    start_gui()
    logging.info("Application closed.")