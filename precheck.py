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
    target_device = input("Enter switch hostname: ")

    pre_check_commands = [
        "show ethernet-switching table",
        "show version",
        "show interfaces terse",
        "show interfaces descriptions",
        "show lldp neighbors",
        "show virtual-chassis"
    ]

    # Step 1: Check Uplinks on the Switch
    ssh = establish_ssh_connection(target_device, username, password)
    if not ssh:
        return
    print("Checking uplinks on the switch...")
    output, error = execute_command(ssh, "show lldp neighbors")
    if "error" in error.lower():
        print("Error in checking uplinks. Exiting.")
        ssh.close()
        return
    print("LLDP neighbors:\n", output)

    # Count uplinks and active uplinks
    total_uplinks, active_uplinks = count_uplinks(output)
    print(f"Total uplinks: {total_uplinks}, Active uplinks: {active_uplinks}")

    if input("Are the uplink statuses satisfactory? Type 'Yes' to proceed: ").strip().lower() != "yes":
        print("Exiting. Resolve issues before retrying.")
        ssh.close()
        return

    # Step 2: Pre-Checks on the Switch
    print("Performing pre-checks on the switch...")
    pre_check_output = ""
    for command in pre_check_commands:
        output, error = execute_command(ssh, command)
        pre_check_output += f"Command: {command}\n{output}\n{'-'*50}\n"

        # For "show lldp neighbors" command, add uplink details
        if command == "show lldp neighbors":
            pre_check_output += f"Total uplinks: {total_uplinks}\nActive uplinks: {active_uplinks}\n{'-'*50}\n"

    save_output_to_file("pre_check.txt", pre_check_output)
    print("Pre-checks completed and saved to pre_check.txt.")

    ssh.close()
    print("Process completed successfully.")


if __name__ == "__main__":
    main()
