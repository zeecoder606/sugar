import os
import subprocess
import shutil

from sugar3 import env

_b2g_process = None

def _ensure_profile():
    b2g_profile_path = os.path.join(env.get_profile_path(), "b2g")
    sugar_html_path = os.environ["SUGAR_HTML_PATH"]

    if not os.path.exists(b2g_profile_path):
        shutil.copytree(sugar_html_path, b2g_profile_path)

def start():
    _ensure_profile()

    b2g_bin = os.path.join(os.environ["B2G_PATH"], "b2g")

    global _b2g_process
    _b2g_process = subprocess.Popen([b2g_bin])

def stop():
    global _b2g_process
    _b2g_process.terminate()
