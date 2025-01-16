import getpass
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


def count_uplinks(output):
    """Count total and active uplinks from LLDP neighbors output."""
    lines = output.splitlines()
    total_uplinks = len([line for line in lines if "et-" in line or "ge-" in line])  # Adjust pattern if needed
    active_uplinks = len([line for line in lines if "et-" in line or "ge-" in line and "Up" in line])  # Adjust pattern
    return total_uplinks, active_uplinks


def save_output_to_file(filename, output):
    """Save command output to a file."""
    with open(filename, 'w') as file:
        file.write(output)


def main():
    # Input details
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    redundant_device = input("Enter redundant device hostname: ")
    target_device = input("Enter target upgrade device hostname: ")

    pre_check_commands = [
        "show ethernet-switching table",
        "show version",
        "show interfaces terse",
        "show interfaces descriptions",
        "show lldp neighbors",
        "show virtual-chassis"
    ]

    # Step 1: Check Redundant Device (LLDP Neighbors and Uplinks)
    ssh_redundant = establish_ssh_connection(redundant_device, username, password)
    if not ssh_redundant:
        return
    print("Checking redundant device LLDP neighbors...")
    output, error = execute_command(ssh_redundant, "show lldp neighbors")
    if "error" in error.lower():
        print("Error in checking redundant device LLDP neighbors. Exiting.")
        ssh_redundant.close()
        return
    print("Redundant device LLDP neighbors:\n", output)

    # Count uplinks and active uplinks
    total_uplinks, active_uplinks = count_uplinks(output)
    print(f"Total uplinks: {total_uplinks}, Active uplinks: {active_uplinks}")

    ssh_redundant.close()

    if input("Are the uplink statuses satisfactory? Type 'Yes' to proceed: ").strip().lower() != "yes":
        print("Exiting. Resolve issues before retrying.")
        return

    # Step 2: Pre-Checks on Target Device
    ssh_target = establish_ssh_connection(target_device, username, password)
    if not ssh_target:
        return
    print("Performing pre-checks on the target device...")
    pre_check_output = ""
    for command in pre_check_commands:
        output, error = execute_command(ssh_target, command)
        pre_check_output += f"Command: {command}\n{output}\n{'-'*50}\n"

        # For "show lldp neighbors" command, count uplinks and active uplinks
        if command == "show lldp neighbors":
            total_uplinks, active_uplinks = count_uplinks(output)
            pre_check_output += f"Total uplinks: {total_uplinks}\nActive uplinks: {active_uplinks}\n{'-'*50}\n"

    save_output_to_file("pre_check.txt", pre_check_output)
    print("Pre-checks completed and saved to pre_check.txt.")

    ssh_target.close()
    print("Process completed successfully.")


if __name__ == "__main__":
    main()
