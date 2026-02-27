#!/usr/bin/env python3

import os
import re
import subprocess

def get_password_for_machine(machine_name, login=None, authinfo_file="~/.authinfo.gpg") -> str:
    authinfo_path = os.path.expanduser(authinfo_file)
    if os.path.exists(authinfo_path):
        try:
            decrypted_content = subprocess.check_output(
                ["gpg", "--decrypt", authinfo_path], stderr=subprocess.DEVNULL
            ).decode("utf-8")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Failed to decrypt the file. Ensure GPG is configured correctly.")
        else:
            for line in decrypted_content.splitlines():
                if login:
                    match = re.search(
                        rf"machine\s+{re.escape(machine_name)}\s+login\s+{re.escape(login)}\s+.*password\s+(\S+)",
                        line,
                    )
                else:
                    match = re.search(
                        rf"machine\s+{re.escape(machine_name)}\s+.*password\s+(\S+)", line
                    )
                if match:
                    return match.group(1)
    return _get_password_from_pass(machine_name, login)


def _get_password_from_pass(machine_name, login=None) -> str:
    """Retrieve a password from pass (password-store)."""
    if login:
        entries = [f"{machine_name}/{login}"]
    else:
        try:
            out = subprocess.check_output(
                ["pass", "ls", machine_name], stderr=subprocess.DEVNULL
            ).decode("utf-8")
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

        clean = re.sub(r"\x1b\[[0-9;]*m", "", out)
        entries = []
        for line in clean.splitlines():
            if line.strip() == "Password Store":
                continue
            name = re.sub(r"^[\s│├└─]+", "", line).strip()
            if not name or name == machine_name:
                continue
            entries.append(f"{machine_name}/{name}")

    for entry in entries:
        try:
            pw = (
                subprocess.check_output(["pass", "show", entry], stderr=subprocess.DEVNULL)
                .decode("utf-8")
                .splitlines()[0]
                .strip()
            )
            if pw:
                return pw
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
            continue

    return None
