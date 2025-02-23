#!/usr/bin/env python3

import os
import re
import subprocess

def get_password_for_machine(machine_name, login=None, authinfo_file="~/.authinfo.gpg") -> str:
    try:
        # Expand the ~ to the user's home directory
        authinfo_file = os.path.expanduser(authinfo_file)

        # Decrypt the file using GPG
        decrypted_content = subprocess.check_output(['gpg', '--decrypt', authinfo_file], stderr=subprocess.DEVNULL).decode('utf-8')

        for line in decrypted_content.splitlines():
            # Match the machine and optional login fields, then capture the password
            if login:
                match = re.search(rf'machine\s+{re.escape(machine_name)}\s+login\s+{re.escape(login)}\s+.*password\s+(\S+)', line)
            else:
                match = re.search(rf'machine\s+{re.escape(machine_name)}\s+.*password\s+(\S+)', line)
            if match:
                return match.group(1)
    except subprocess.CalledProcessError:
        print("Failed to decrypt the file. Ensure GPG is configured correctly.")
    return None
