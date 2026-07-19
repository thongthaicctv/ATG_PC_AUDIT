import subprocess
from core.clipboard_manager import copy_file,copy_text
from core.gmail_launcher import reveal_file


def prepare_manual(phone,message,file_path):
    copy_text(phone);reveal_file(file_path)
    return {"phone":phone,"message":message,"file_ready":copy_file(file_path),"status":"ZALO_MANUAL_FALLBACK"}
