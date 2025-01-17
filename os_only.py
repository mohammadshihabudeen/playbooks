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
    """Copy firmware to the device."""
    try:
        with SCPClient(ssh.get_transport()) as scp:
            print(f"Copying {firmware} to {destination}...")
            scp.put(firmware, destination)
            print(f"Successfully copied {firmware}.")
    except Exception as e:
        print(f"Failed to copy {firmware}: {e}")
        

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

    ssh = establish_ssh_connection(target_device, username, password)
    if not ssh:
        return

    for firmware in firmware_list:
        firmware = firmware.strip()
        print(f"Checking if {firmware} exists on the target device...")
        output, error = execute_command(ssh, f"file list /var/tmp/{firmware}")
        if "No such file" in output:
            print(f"{firmware} not found on the target device. Copying it from the corpjump server...")
            copy_firmware(ssh, firmware, "/var/tmp/")
        else:
            print(f"{firmware} already exists on the target device.")
        
        print(f"Starting upgrade with {firmware}...")
        output, error = execute_command(ssh, f"request system software add /var/tmp/{firmware}")
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
