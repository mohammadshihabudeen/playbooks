import getpass
import re
import subprocess
import time
import paramiko
from scp import SCPClient

def establish_ssh_connection(hostname, username, password):
    """Establish an SSH connection to the device."""
    try:
        print(f"Connecting to {hostname}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password)
        print(f"Connected to {hostname}.")
        return ssh
    except Exception as e:
        print(f"Failed to connect to {hostname}: {e}")
        return None

def execute_command(ssh, command):
    """Execute a command on the device and return the output."""
    stdin, stdout, stderr = ssh.exec_command(command)
    time.sleep(1)  # Allow command execution time
    return stdout.read().decode('utf-8'), stderr.read().decode('utf-8')

def copy_firmware(ssh, firmware, destination):
    """Copy firmware to the device with a single-line progress bar."""
    def progress(filename, size, sent):
        """Callback to display a single-line progress bar."""
        percentage = (sent / size) * 100 if size > 0 else 0
        bar_length = 20  # Length of the progress bar
        filled_length = int(bar_length * percentage // 100)
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        print(f"\rCopying {filename}: [{bar}] {percentage:.2f}%", end="", flush=True)

    try:
        with SCPClient(ssh.get_transport(), progress=progress) as scp:
            print(f"Copying {firmware} to {destination}...")
            scp.put(firmware, destination)
            print(f"\rCopying {firmware}: [{'=' * 20}] 100.00%", flush=True)
            print("\nCopy completed successfully.")
    except Exception as e:
        print(f"\nFailed to copy {firmware}: {e}")
        return False
    return True

def is_device_pingable(hostname):
    """Ping the device to check if it's reachable."""
    try:
        response = subprocess.run(
            ['ping', '-c', '1', '-W', '3', hostname],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return response.returncode == 0
    except Exception as e:
        print(f"Error during pinging: {e}")
        return False

def main():
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    target_device = input("Enter switch hostname: ")
    firmware_list = input("Enter firmware list (comma-separated): ").split(',')

    firmware_md5 = {}
    for firmware in firmware_list:
        firmware = firmware.strip()
        md5_value = input(f"Enter the expected MD5 checksum for {firmware}: ")
        firmware_md5[firmware] = md5_value

    ssh = establish_ssh_connection(target_device, username, password)
    if not ssh:
        return

    for firmware, expected_md5 in firmware_md5.items():
        print(f"Checking if {firmware} exists on the target device...")
        output, error = execute_command(ssh, f"file list /var/tmp/{firmware}")
        if "No such file" in output:
            print(f"{firmware} not found on the target device. Copying it from the corpjump server...")
            if not copy_firmware(ssh, firmware, "/var/tmp/"):
                ssh.close()
                return
        else:
            print(f"{firmware} already exists on the target device.")

        print(f"Validating MD5 checksum for {firmware}...")
        output, error = execute_command(ssh, f"file checksum md5 /var/tmp/{firmware}")
        device_md5 = re.search(r'[a-fA-F0-9]{32}', output)
        if device_md5:
            device_md5 = device_md5.group(0)
            if device_md5 != expected_md5:
                print(f"MD5 checksum mismatch for {firmware}. Expected: {expected_md5}, Found: {device_md5}")
                ssh.close()
                return
            else:
                print(f"MD5 checksum matched for {firmware}.")
        else:
            print(f"Failed to retrieve MD5 checksum for {firmware} on the device.")
            ssh.close()
            return

        print(f"Starting upgrade with {firmware}...")
        output, error = execute_command(ssh, f"request system software add /var/tmp/{firmware} no-validate")
        print(output)
        if "error" in error.lower():
            print(f"Upgrade failed for {firmware}. Exiting.")
            ssh.close()
            return

        print(f"Upgrade with {firmware} completed. Rebooting...")
        execute_command(ssh, "request system reboot")
        print(f"Waiting for {target_device} to come back online...")
        time.sleep(30)
        while not is_device_pingable(target_device):
            print("Device is not reachable. Retrying in 30 seconds...")
            time.sleep(30)
        ssh = establish_ssh_connection(target_device, username, password)
        if not ssh:
            print("Unable to reconnect to the device. Exiting.")
            return

    ssh.close()

if __name__ == "__main__":
    main()
