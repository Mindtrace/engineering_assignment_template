#!/usr/bin/env python
"""Helper script to set up the Mtrix project camera capture for the first time."""

import os
import sys
import platform
import subprocess
import stat
import ctypes

from mindtrace.core.config import Config
from mindtrace.utils.downloads import download_and_extract_zip, download_and_extract_tarball


def install_daheng_sdk(release_version: str = "v1.0-stable"):
    """Download and run the Daheng SDK installation script.

    The Daheng SDK is required to connect and use Daheng cameras. The SDK is only available for Linux and Windows.

    The Linux installer used here is the X86 installer. An ARM installer is also available from the Daheng website, if
    you need to install the SDK on an ARM-based system.

    For Windows, the SDK installer will also automatically install the associated Python library, gxipy. For Linux, run
    the install_gxipy function to install the Linux version of gxipy. Note that the two libraries (the Windows version
    of gxipy and the Linux version) are not actually the same, nor do they have the same API.
    """

    linux_sdk_url = f"https://github.com/Mindtrace/gxipy/releases/download/{release_version}/Galaxy_Linux.tar.gz"
    windows_sdk_url = (f"https://github.com/Mindtrace/gxipy/releases/download/{release_version}/Galaxy_Windows.zip")

    config = Config()
    daheng_dir = os.path.join(config["DIR_PATHS"]["LIB"], "daheng")
    match platform.system():
        case "Linux":
            print(f"Downloading SDK from {linux_sdk_url}")
            extracted_dir = download_and_extract_tarball(url=linux_sdk_url, save_dir=daheng_dir)
            print(f"Extracted SDK to {extracted_dir}")
            # Make the SDK installer executable and run it
            runfile = os.path.join(extracted_dir, "Galaxy_camera.run")
            os.chmod(path=runfile, mode=os.stat(runfile).st_mode | stat.S_IXUSR | stat.S_IXGRP)  # | stat.S_IXOTH)
            subprocess.call(["./Galaxy_camera.run"], cwd=extracted_dir)

        case "Windows":
            print(f"Downloading SDK from {windows_sdk_url}")
            extracted_dir = download_and_extract_zip(url=windows_sdk_url, save_dir=daheng_dir)
            if '.exe' in extracted_dir:
                sdk_exe = extracted_dir
            else:
                sdk_exe = os.path.join(extracted_dir, os.listdir(extracted_dir)[0])
            print(f"SDK executable: {sdk_exe}")

            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0

            if is_admin:
                print("User has administrative privileges.")
                subprocess.run([sdk_exe, "/S"], check=True)
                print(f"Installed SDK from {sdk_exe}")
                sys.exit(0)
            else:
                print("Attempting to elevate privileges...Restart VScode")
                try:
                    ctypes.windll.shell32.ShellExecuteW(
                        None, "runas", sys.executable, " ".join([sys.argv[0]] + sys.argv[1:]), None, 1
                    )
                except Exception as e:
                    print(f"Failed to elevate process: {e}")
                    print(
                        f"User does not have administrative privileges. Please run the script in Admin mode or install the sdk from {os.path.normpath(sdk_exe)}"
                    )
        case _:
            print("Unsupported operating system. The Daheng SDK is only available for Linux and Windows.")


if __name__ == "__main__":
    install_daheng_sdk()
