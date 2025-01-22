import getpass
import re
import time

import paramiko


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
        

def main():
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    target_device = input("Enter switch hostname: ")
    uplink_regex = r"corp-cr"

    ssh = establish_ssh_connection(target_device, username, password)
    if not ssh:
        return

    #STEP1

    print("Performing pre-checks on the switch...")
    pre_check_commands = [
        "show ethernet-switching table",
        "show version",
        "show interfaces terse",
        "show interfaces descriptions",
        "show lldp neighbors",
        "show virtual-chassis"
    ]
    pre_check_output = ""
    for command in pre_check_commands:
        output, error = execute_command(ssh, command)
        pre_check_output += f"Command: {command}\n{output}\n{'-'*50}\n"

    save_output_to_file("pre_check.txt", pre_check_output)
    print("Pre-checks completed and saved to pre_check.txt.")

if __name__ == "__main__":
    main()
