import getpass
import re
import time
import subprocess
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



def save_output_to_file(filename, output):
    """Save command output to a file."""
    with open(filename, 'w') as file:
        file.write(output)

def compare_outputs(pre_file, post_file, comparison_file):
    """Compare pre-check and post-check outputs and save the differences."""
    with open(pre_file, 'r') as pre, open(post_file, 'r') as post, open(comparison_file, 'w') as comparison:
        pre_lines = pre.readlines()
        post_lines = post.readlines()
        differences = set(pre_lines).symmetric_difference(set(post_lines))
        comparison.write("Differences between Pre-check and Post-check:\n")
        comparison.writelines(differences)


def main():
    # Input details
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    target_device = input("Enter switch hostname: ")
    # Step 1: Establish SSH connection
    ssh = establish_ssh_connection(target_device, username, password)
    if not ssh:
        return
    # Regex pattern to identify uplinks in the description
        # Step 4: Post-Checks on Target Device
    pre_check_commands = [
        "show ethernet-switching table",
        "show version",
        "show interfaces terse",
        "show interfaces descriptions",
        "show lldp neighbors",
        "show virtual-chassis"
    ]
    print("Performing post-checks on the target device...")
    post_check_output = ""
    for command in pre_check_commands:
        output, error = execute_command(ssh_target, command)
        post_check_output += f"Command: {command}\n{output}\n{'-'*50}\n"
    save_output_to_file("post_check.txt", post_check_output)
    print("Post-checks completed and saved to post_check.txt.")

    # Step 5: Compare Pre-Checks and Post-Checks
    compare_outputs("pre_check.txt", "post_check.txt", "comparison.txt")
    print("Comparison completed. Differences saved to comparison.txt.")
    uplink_regex = r"corp-cr"


