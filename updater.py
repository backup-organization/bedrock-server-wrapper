from pathlib import Path
import os, sys, shutil
import urllib.request
import hashlib
import zipfile, tempfile
import re

class WebConnection():
    def __init__(self, url):
        self.url = url
        self.__access()

    def __access(self):
        self.response = urllib.request.urlopen(self.url)

    def download_to(self, file):
        file.write(self.response.read())

# Working update code for reference.
# def update_wrapper(branch="master"):
#     repo = "bedrock-server-wrapper"
#     url = f"https://github.com/TommyCox/{repo}/archive/{branch}.zip"
#     types_to_update = (".py")
#     destination_dir = Path.cwd()
#     try:
#         print(f"Connecting to {url}")
#         files = WebConnection(url)
#         with tempfile.TemporaryFile() as newfile:
#             print("Downloading files.")
#             files.download_to(newfile)
#             #TODO: Do version checking, checksums, or whatever here.
#             print("Unzipping archive...")
#             with zipfile.ZipFile(newfile) as zipped:
#                 for zipinfo in zipped.infolist():
#                     if zipinfo.filename.endswith(types_to_update):
#                         print(f"Found file '{zipinfo.filename}'")
#                         prefix = f"{repo}-{branch}/"
#                         zipinfo.filename = zipinfo.filename.replace(prefix, "" , 1)
#                         print(f"Extracting as {zipinfo.filename}")
#                         zipped.extract(zipinfo, destination_dir)
#     except urllib.error.HTTPError as http_error:
#         print(f"HTTP Error: {http_error}")
#         return False
#     return True

class Updater():
    def connect(self):
        try:
            return WebConnection(self.url)
        except urllib.error.HTTPError as http_error:
            print(f"HTTP Error: {http_error}")
            return None

    def unzip(self, downloaded_file):
        with zipfile.ZipFile(downloaded_file) as zipped:
            for zipinfo in zipped.infolist():
                if self.extract_this(zipinfo):
                    zipped.extract(zipinfo, self.destination_dir)

# These are files to preserve when updating.
PROTECTED_SERVER_FILES = ["server.properties", "permissions.json", "whitelist.json"]

class ServerUpdater(Updater):
    def __init__(self, server_dir = "minecraft_server", overwrite_all = False, locale = "en-us"):
        self.destination_dir = Path(server_dir)
        self.url = f"https://minecraft.net/{locale}/download/server/bedrock"
        self.overwrite_all = overwrite_all

    def extract_this(self, zipinfo):
        # Check for special files that we don't want to overwrite.
        if not self.overwrite_all:
            if zipinfo.filename in PROTECTED_SERVER_FILES:
                return not Path(self.destination_dir, zipinfo.filename).is_file()
        return True

    def update(self, force = False):
        # Connect to minecraft.net
        connection = self.connect()
        if connection is None:
            return False
        platform = "win" if sys.platform == "win32" else "linux" if sys.platform == "linux" else None
        assert platform, "Unsupported platform detected."
        pattern = fR"https://minecraft\.azureedge\.net/bin-{platform}/bedrock-server-([\d\.]+)\.zip"
        match = re.search(pattern, connection.response.read().decode())
        if match:
            print(f"Found download link:{match.group(0)}")
            print(f"Version is: {match.group(1)}")
            self.url = match.group(0)
            new_version = match.group(1)
        else:
            return False
        version_file_path = self.destination_dir / "server_version.txt"
        if not force:
            # Check version. Stop if already current.
            try:
                with open(version_file_path, "r") as ver_file:
                    version = ver_file.read()
                    if (version == new_version):
                        print(f"New Version ({new_version}) is the same as Current Version.")
                        return True
            except FileNotFoundError:
                pass
        # Connect to download link.
        connection = self.connect()
        if connection is None:
            print("Error connecting to download link.")
            return False
        # Download & extract files.
        with tempfile.TemporaryFile() as newfile:
            connection.download_to(newfile)
            self.unzip(newfile)
        with open(version_file_path, "w") as ver_file:
            print("Writing new version number.")
            ver_file.write(new_version)
        # TODO: Support renaming executable if name was changed?
        return True

class WrapperUpdater(Updater):
    def __init__(self, branch = "master", repo = "bedrock-server-wrapper", user = "TommyCox"):
        self.destination_dir = Path.cwd()
        self.repo = repo
        self.branch = branch
        self.url = f"https://github.com/{user}/{repo}/archive/{branch}.zip"
        self.types_to_update = (".py")

    def extract_this(self, zipinfo):
        # Make modifications to extraction.
        prefix = f"{self.repo}-{self.branch}/"
        zipinfo.filename = zipinfo.filename.replace(prefix, "" , 1)
        # Return boolean for extraction conditions.
        return zipinfo.filename.endswith(self.types_to_update)

    def update(self):
        connection = self.connect()
        if connection is None:
            return False
        with tempfile.TemporaryFile() as newfile:
            connection.download_to(newfile)
            #TODO: Do version checking, checksums, or whatever here.
            self.unzip(newfile)
        # Erase pycache.
        try:
            shutil.rmtree(self.destination_dir / "__pycache__")
        except FileNotFoundError as error:
            print(f"Failed to remove pycache:\n\t{error}")
        return True

if __name__ == "__main__":
    print("Downloading wrapper!")
    updater = WrapperUpdater(branch="dev-updater")
    updater.update()
    print("Download complete!")