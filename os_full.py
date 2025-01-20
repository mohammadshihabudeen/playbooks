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

def copy_firmware(ssh, firmware, destination):
    """Copy firmware to the device with a single-line progress bar."""
    def progress(filename, size, sent):
        """Callback to display a single-line progress bar."""
        percentage = (sent / size) * 100 if size > 0 else 0
        bar_length = 20  # Length of the progress bar
        filled_length = int(bar_length * percentage // 100)
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        # Print the progress bar in a single line
        print(f"\rCopying {filename}: [{bar}] {percentage:.2f}%", end="", flush=True)

    try:
        with SCPClient(ssh.get_transport(), progress=progress) as scp:
            print(f"Copying {firmware} to {destination}...")
            scp.put(firmware, destination)
            # Ensure the final progress bar displays 100%
            print(f"\rCopying {firmware}: [{'=' * 20}] 100.00%", flush=True)
            print("\nCopy completed successfully.")
    except Exception as e:
        print(f"\nFailed to copy {firmware}: {e}")

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

def extract_info(file_content):
    """Extract all relevant information from the file content."""
    return file_content.splitlines()

def compare_files(pre_data, post_data):
    """Compare pre-check and post-check data."""
    changes = []
    max_lines = max(len(pre_data), len(post_data))

    for i in range(max_lines):
        pre_line = pre_data[i] if i < len(pre_data) else ""
        post_line = post_data[i] if i < len(post_data) else ""
        
        if pre_line != post_line:
            changes.append((pre_line, post_line))
    
    return changes

def wrap_text(text, width):
    """Wrap text to fit within a specified width."""
    lines = []
    while len(text) > width:
        # Find the last space within the width
        split_index = text[:width].rfind(" ")
        if split_index == -1:  # No spaces found, split at width
            split_index = width
        lines.append(text[:split_index].strip())
        text = text[split_index:].strip()
    lines.append(text)  # Add the remaining text
    return lines


def save_table_to_file(changes, output_file):
    """Save changes in a table format to a file with text wrapping."""
    col_width = 50
    table_width = 2 * col_width + 7  # Includes borders and separator

    with open(output_file, "w") as f:
        # Write top border
        f.write("+" + "-" * (table_width - 2) + "+\n")

        # Write header row
        header = f"| {'Pre-Check':<{col_width}} | {'Post-Check':<{col_width}} |\n"
        f.write(header)
        f.write("+" + "-" * (table_width - 2) + "+\n")

        # Write data rows with text wrapping
        for pre, post in changes:
            pre_lines = wrap_text(pre, col_width)
            post_lines = wrap_text(post, col_width)
            max_lines = max(len(pre_lines), len(post_lines))

            for i in range(max_lines):
                pre_line = pre_lines[i] if i < len(pre_lines) else ""
                post_line = post_lines[i] if i < len(post_lines) else ""
                f.write(f"| {pre_line:<{col_width}} | {post_line:<{col_width}} |\n")

        # Write bottom border
        f.write("+" + "-" * (table_width - 2) + "+\n")

    print(f"Comparison saved to {output_file}")

def main():
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
    target_device = input("Enter switch hostname: ")
    firmware_list = input("Enter firmware list (comma-separated): ").split(',')
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

    #STEP2
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

    #STEP3
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
        output, error = execute_command(ssh, f"request system software add /var/tmp/{firmware} no-validate")
        print(output)
        if "error" in error.lower():
            print(f"Upgrade failed for {firmware}. Exiting.")
            ssh.close()
            return
        print(f"Upgrade with {firmware} completed. Rebooting...")
        execute_command(ssh, "request system reboot")
        ssh.close()
        print(f"Waiting for {target_device} to come back online...")
        time.sleep(30)
        while not is_device_pingable(target_device):
            print("Device is not reachable. Retrying in 30 seconds...")
            time.sleep(30)
        print(f"{target_device} is back online. Performing post-checks...")
        ssh = establish_ssh_connection(target_device, username, password)
    if not ssh:
        print("Unable to reconnect to the device. Exiting.")
        return

    #STEP4
    post_check_output = ""
    for command in pre_check_commands:
        output, error = execute_command(ssh, command)
        post_check_output += f"Command: {command}\n{output}\n{'-'*50}\n"

    save_output_to_file("post_check.txt", post_check_output)
    print("Post-checks completed and saved to post_check.txt.")

    #STEP 5
    print("Comparing pre-check and post-check data...")
    pre_version_data = extract_info(pre_check_output)
    post_version_data = extract_info(post_check_output)
    version_changes = compare_files(pre_version_data, post_version_data)
    save_table_to_file(version_changes, "version_comparison.txt")

    print("Upgrade process completed successfully.")

if __name__ == "__main__":
    main()
