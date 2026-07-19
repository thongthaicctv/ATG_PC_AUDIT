import re
import subprocess
import webbrowser
from pathlib import Path

EMAIL_RE=re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def valid_email(value):
    text=str(value or "").strip();return not text or bool(EMAIL_RE.fullmatch(text))


def open_gmail():return webbrowser.open("https://mail.google.com/",new=2)


def reveal_file(path):
    file=Path(path).resolve()
    if not file.is_file():raise FileNotFoundError(file)
    subprocess.Popen(["explorer.exe",f'/select,{file}'])
