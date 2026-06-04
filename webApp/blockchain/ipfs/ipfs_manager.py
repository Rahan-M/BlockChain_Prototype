import subprocess
import re
import os
import asyncio

from pathlib import Path
from typing import Dict

class IPFSManager:

    def __init__(self, port):
        self.ipfs_port = port + 50  # API port
        self.gateway_port = port + 81  # Gateway port
        self.swarm_tcp = port + 2
        self.swarm_udp = port + 3
        self.repo_path = Path.home() / f".ipfs_{port}"
        self.env = os.environ.copy()
        self.env["IPFS_PATH"] = str(self.repo_path)
        self.daemon_process=None

        self.file_hashes: Dict[str, str]={}
        self.file_hashes_lock = asyncio.Lock()

        self.init_repo()
        self.configure_ports()

    def init_repo(self):
        """
            Creates a ipfs repo of name ending in ipfs_port_no eg ipfs_5000 
        """
        if not self.repo_path.exists():
            subprocess.run(["ipfs", "init"], env=self.env, check=True)
            print("\nIPFS repo created\n")

    def configure_ports(self):
        subprocess.run(["ipfs", "config", "Addresses.API", f"/ip4/127.0.0.1/tcp/{self.ipfs_port}"], env=self.env, check=True)
        subprocess.run(["ipfs", "config", "Addresses.Gateway", f"/ip4/127.0.0.1/tcp/{self.gateway_port}"], env=self.env, check=True)
        subprocess.run([
            "ipfs", "config", "Addresses.Swarm", "--json",
            f'["/ip4/127.0.0.1/tcp/{self.swarm_tcp}", "/ip4/127.0.0.1/udp/{self.swarm_udp}/quic"]'
        ], env=self.env, check=True)
        print("\nConfigured Ports\n")

    def start_daemon(self):
        self.daemon_process= subprocess.Popen(["ipfs", "daemon"], env=self.env)
        print("\nIPFS Daemon Started\n")
        import time
        time.sleep(5)

    def stop_daemon(self):
        if self.daemon_process:
            self.daemon_process.terminate()

            try:
                self.daemon_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.daemon_process.kill()

    def add_to_ipfs(self, file_path):
        try:
            # Use the 'ipfs add' command WITHOUT the --json flag
            # Older IPFS CLIs typically output something like:
            # added QmYOURHASH /path/to/your/file.txt
            # (followed by a progress bar line)
            result = subprocess.run(
                ['ipfs', 'add', file_path],
                capture_output=True,
                text=True,
                check=True,
                env=self.env
            )

            output_lines = result.stdout.strip().split('\n')
            print(f"Raw IPFS add output:\n{result.stdout}") # For debugging purposes

            if output_lines:
                # Look for lines starting with 'added '
                # Iterate from the end as the final 'added' line is usually the most relevant
                for line in reversed(output_lines):
                    if line.startswith('added '):
                        # Use regex to extract the hash and the name
                        # \s+ matches one or more whitespace characters
                        # (\S+) captures one or more non-whitespace characters (the hash) paranthesis is used to capture
                        # (.+) captures the rest of the line (the name, potentially including spaces)

                        match = re.match(r'added\s+(\S+)\s+(.+)', line)
                        if match:
                            ipfs_hash = match.group(1)
                            # The name might include the full path depending on how you add it
                            # You might need to adjust this parsing based on your exact desired 'name'
                            ipfs_name = match.group(2)
                            print(f"Successfully parsed: Hash={ipfs_hash}, Name={ipfs_name}") # For confirmation
                            return ipfs_hash, ipfs_name
                        
                print("Error: Could not parse IPFS add output for hash and name.")
                return None, None
            
            else:
                print("Error: No output received from ipfs add command.")
                return None, None
            
        except subprocess.CalledProcessError as e:
            print(f"Error adding file to IPFS: {e}")
            print(f"Stderr: {e.stderr}")
            return None, None
        
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return None, None
        
    def download_ipfs_file_subprocess(self, cid: str, destination_path: str):
        """
        Downloads a file from IPFS using the 'ipfs get' CLI command via subprocess.

        Args:
            cid (str): The CID (Content ID) of the file to download.
            destination_path (str): The full path including the filename where the file should be saved.
                                    If the CID points to a directory, this should be the path
                                    where the directory will be created.
        """
        # Ensure the directory for the destination_path exists
        output_dir = os.path.dirname(destination_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")

        # Construct the ipfs get command
        # We use `-o` to specify the exact output path/filename.
        # If the CID is a file, it will be saved as the specified `destination_path`.
        # If the CID is a directory, a directory with the given `destination_path` will be created,
        # and its contents will be placed inside.
        command = ["ipfs", "get", cid, "-o", destination_path]

        print(f"Executing command: {' '.join(command)}")

        try:
            # Run the command
            # `capture_output=True` will capture stdout and stderr
            # `text=True` decodes stdout/stderr as text (UTF-8 by default)
            # `check=True` raises a CalledProcessError if the command returns a non-zero exit code
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                env=self.env
            )

            print(f"Successfully downloaded CID {cid} to: {destination_path}")
            if result.stdout:
                print("STDOUT:", result.stdout.strip())
            if result.stderr:
                print("STDERR:", result.stderr.strip())

        except FileNotFoundError:
            print("Error: 'ipfs' command not found.")
            print("Please ensure IPFS CLI is installed and in your system's PATH.")
        except subprocess.CalledProcessError as e:
            print(f"Error downloading file with CID {cid}:")
            print(f"Command failed with exit code {e.returncode}")
            print("STDOUT:", e.stdout.strip())
            print("STDERR:", e.stderr.strip())
            print("Please check if your IPFS daemon is running and if the CID is valid.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")