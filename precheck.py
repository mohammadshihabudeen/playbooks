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


def parse_interfaces_descriptions(output):
    """Parse 'show interfaces descriptions' to find interfaces and their statuses."""
    interfaces = {}
    lines = output.splitlines()
    for line in lines[1:]:  # Skip header line
        parts = line.split()
        if len(parts) >= 4:
            interface, admin_status, link_status = parts[0], parts[1].lower(), parts[2].lower()
            interfaces[interface] = (admin_status == "up" and link_status == "up")
    return interfaces


def parse_lldp_neighbors(output):
    """Parse 'show lldp neighbors' to find uplink interfaces."""
    uplink_interfaces = []
    lines = output.splitlines()
    for line in lines[1:]:  # Skip header line
        parts = line.split()
        if len(parts) >= 2:
            uplink_interfaces.append(parts[0])  # Local Interface
    return uplink_interfaces


def save_output_to_file(filename, output):
    """Save command output to a file."""
    with open(filename, 'w') as file:
        file.write(output)


def main():
    # Input details
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    target_device = input("Enter switch hostname: ")

    # Step 1: Check Uplinks on the Switch
    ssh = establish_ssh_connection(target_device, username, password)
    if not ssh:
        return

    print("Checking uplinks on the switch...")

    # Execute and parse 'show interfaces descriptions'
    interface_output, interface_error = execute_command(ssh, "show interfaces descriptions")
    if "error" in interface_error.lower():
        print("Error in fetching interface descriptions. Exiting.")
        ssh.close()
        return
    interfaces_status = parse_interfaces_descriptions(interface_output)

    # Execute and parse 'show lldp neighbors'
    lldp_output, lldp_error = execute_command(ssh, "show lldp neighbors")
    if "error" in lldp_error.lower():
        print("Error in fetching LLDP neighbors. Exiting.")
        ssh.close()
        return
    uplink_interfaces = parse_lldp_neighbors(lldp_output)

    # Determine total and active uplinks
    total_uplinks = len(uplink_interfaces)
    active_uplinks = len([intf for intf in uplink_interfaces if interfaces_status.get(intf, False)])

    print(f"Total uplinks: {total_uplinks}, Active uplinks: {active_uplinks}")

    if input("Are the uplink statuses satisfactory? Type 'Yes' to proceed: ").strip().lower() != "yes":
        print("Exiting. Resolve issues before retrying.")
        ssh.close()
        return

    # Step 2: Pre-Checks on the Switch
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

        # Include uplink details if 'show lldp neighbors' is the command
        if command == "show lldp neighbors":
            pre_check_output += f"Total uplinks: {total_uplinks}\nActive uplinks: {active_uplinks}\n{'-'*50}\n"

    save_output_to_file("pre_check.txt", pre_check_output)
    print("Pre-checks completed and saved to pre_check.txt.")

    ssh.close()
    print("Process completed successfully.")


if __name__ == "__main__":
    main()
