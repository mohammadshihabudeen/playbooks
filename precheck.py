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

def parse_interfaces_descriptions(output, regex_pattern):
    """Parse 'show interfaces descriptions' to find all links and their statuses."""
    interfaces = {}
    lines = output.splitlines()
    for line in lines[1:]:  # Skip header line
        parts = line.split()
        interface = parts[0]
        admin_status = parts[1].lower() if len(parts) > 1 and parts[1] else ""
        link_status = parts[2].lower() if len(parts) > 2 and parts[2] else ""
        description = parts[-1]
        is_uplink = re.search(regex_pattern, description) is not None
        interfaces[interface] = {
                "admin_up": admin_status == "up",
                "link_up": link_status == "up",
                "is_uplink": is_uplink,
                "description": description
            }
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
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    target_device = input("Enter switch hostname: ")
    uplink_regex = r"corp-cr"

    ssh = establish_ssh_connection(target_device, username, password)
    if not ssh:
        return

    #STEP1
    print("Fetching interface descriptions...")

    interface_output, interface_error = execute_command(ssh, "show interfaces descriptions")
    if "error" in interface_error.lower():
        print("Error in fetching interface descriptions. Exiting.")
        ssh.close()
        return
    interfaces_status = parse_interfaces_descriptions(interface_output, uplink_regex)

    print("Fetching LLDP neighbors...")
    lldp_output, lldp_error = execute_command(ssh, "show lldp neighbors")
    if "error" in lldp_error.lower():
        print("Error in fetching LLDP neighbors. Exiting.")
        ssh.close()
        return
    lldp_interfaces = parse_lldp_neighbors(lldp_output)

    total_links = len(interfaces_status)
    uplink_candidates = [intf for intf, details in interfaces_status.items() if details["is_uplink"]]
    active_uplinks = [intf for intf in uplink_candidates if (interfaces_status[intf]["admin_up"] and interfaces_status[intf]["link_up"])]

    confirmed_uplinks = [intf for intf in active_uplinks if intf in lldp_interfaces]

    print(f"Total links: {total_links}")
    print(f"Total potential uplinks (matching description): {len(uplink_candidates)}")
    print(f"Active uplinks: {len(active_uplinks)}")
    print(f"Confirmed uplinks via LLDP: {len(confirmed_uplinks)}")

    print("\nDetails of Confirmed Uplinks:")
    for intf in uplink_candidates:
        confirmation = "Confirmed" if intf in confirmed_uplinks else "Unconfirmed"
        description = interfaces_status[intf]["description"]
        print(f"Interface: {intf}, LLDP: {confirmation}, Description: {description}")

    if input("\nAre the uplink statuses satisfactory? Type 'Yes' to proceed: ").strip().lower() != "yes":
        print("Exiting. Resolve issues before retrying.")
        ssh.close()
        return
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
