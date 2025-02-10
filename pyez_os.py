import getpass
import re
import time
from jnpr.junos import Device
from jnpr.junos.utils.scp import SCP
from jnpr.junos.utils.fs import FS
from jnpr.junos.utils.sw import SW
from jnpr.junos.exception import ConnectError

def establish_ssh_connection(hostname, username, password):
    """Establish a connection to the Juniper device using PyEZ."""
    try:
        print(f"Connecting to {hostname}...")
        dev = Device(host=hostname, user=username, passwd=password)
        dev.open()
        print(f"Connected to {hostname}.")
        return dev
    except ConnectError as e:
        print(f"Failed to connect to {hostname}: {e}")
        return None

def execute_command(dev, command):
    """Execute a CLI command on the device and return output."""
    try:
        output = dev.cli(command, format="text")
        return output, None
    except Exception as e:
        return None, str(e)

def parse_interfaces_descriptions(output, regex_pattern):
    """Parse 'show interfaces descriptions' to find all links and their statuses."""
    interfaces = {}
    lines = output.splitlines()
    for line in lines[1:]:  # Skip header line
        parts = line.split()
        interface = parts[0]
        admin_status = parts[1].lower() if len(parts) > 1 and parts[1] else ""
        link_status = parts[2].lower() if len(parts) > 2 and parts[2] else ""
        description = parts[-1] if parts else ""
        is_uplink = re.search(regex_pattern, description) is not None
        interfaces[interface] = {
                "admin_up": admin_status == "up",
                "link_up": link_status == "up",
                "is_uplink": is_uplink,
                "description": description
            }
    return interfaces

def save_output_to_file(filename, output):
    """Save command output to a file."""
    with open(filename, 'w') as file:
        file.write(output)

def copy_firmware(dev, firmware_path, destination):
    """Copy firmware to the device using PyEZ FileSystem."""
    try:    
        print(f"Checking if {firmware_path} exists on the target device...")
        output, error = execute_command(dev, f"file list /var/tmp/{firmware_path}")
        if "No such file" in output:
            print(f"{firmware_path} not found on the target device. Copying it from the corpjump server...")
            with SCP(dev, progress=True) as scp:
                scp.put(firmware_path, destination)
            print(f"Firmware {firmware_path} copied to {destination}.")
        else:
            print(f"{firmware_path} already exists on the target device.")
    except Exception as e:
        print(f"Failed to copy firmware: {e}")

def validate_firmware(dev, firmware, expected_md5):
    """Validate the firmware MD5 checksum."""
    fs = FS(dev)
        # Get MD5 checksum
    output = fs.checksum(firmware, algorithm='md5')    
    match = re.search(r'[a-fA-F0-9]{32}', output)
    if match:
        device_md5 = match.group(0)
        if device_md5 != expected_md5:
            print(f"MD5 mismatch! Expected: {expected_md5}, Found: {device_md5}")
            return False
        print("MD5 checksum verified.")
        return True
    print("Could not retrieve MD5 checksum.")
    return False

def upgrade_firmware(dev, firmware_path):
    """Upgrade JunOS firmware using PyEZ SW module."""
    try:
        sw = SW(dev)
        print("Starting firmware upgrade...")
        success = sw.install(package=firmware_path, progress=True, validate=True)
        if success:
            print("Firmware upgrade completed successfully. Rebooting device...")
            dev.reboot()
        else:
            print("Firmware upgrade failed.")
    except Exception as e:
        print(f"Upgrade error: {e}")

def is_device_reachable(hostname):
    """Ping the device to check if it's reachable."""
    import subprocess
    response = subprocess.run(['ping', '-c', '1', '-W', '3', hostname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return response.returncode == 0

def extract_text_from_xml(xml_element):
    """Extracts relevant information from an XML element and formats it as readable text."""
    if isinstance(xml_element, bool):  # ✅ Handle boolean responses
        return "Success" if xml_element else "Failed"
 
    output = []
    for element in xml_element.iter():
        if element.tag is not None and element.text is not None:
            tag = element.tag.replace("-", " ").strip()  # Replace hyphens for readability
            text = element.text.strip()
            if text:
                output.append(f"{tag}: {text}")
 
    return "\n".join(output)
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

def extract_info(file_content):
    """Extract all relevant information from the file content."""
    return file_content.splitlines()

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
    firmware_path = input("Enter firmware path: ").strip()
    expected_md5 = input(f"Enter expected MD5 checksum for {firmware_path}: ")

    uplink_regex = r"corp-cr"

    dev = establish_ssh_connection(target_device, username, password)
    if not dev:
        return

    # Step 1: Fetch interface descriptions
    print("Fetching interface descriptions...")
    output, error = execute_command(dev, "show interfaces descriptions")
    if error:
        print(f"Error: {error}")
        dev.close()
        return

    interfaces_status = parse_interfaces_descriptions(output, uplink_regex)
    uplink_candidates = [intf for intf, details in interfaces_status.items() if details["is_uplink"]]
    active_uplinks = [intf for intf in uplink_candidates if (interfaces_status[intf]["admin_up"] and interfaces_status[intf]["link_up"])]

    print(f"Total links: {len(interfaces_status)}")
    print(f"Uplink Candidates: {len(uplink_candidates)}")
    print(f"Active uplinks: {len(active_uplinks)}")

    if input("\nAre the uplink statuses satisfactory? Type 'Yes' to proceed: ").strip().lower() != "yes":
        print("Exiting. Resolve issues before retrying.")
        dev.close()
        return

    # Step 2: Pre-check commands
    pre_check_commands = [
        {'description': 'Show version', 'method': 'get_software_information'},
        {'description': 'Show interfaces terse', 'method': 'get_interface_information', 'args': {'terse': True}},
        {'description': 'Show LLDP neighbors', 'method': 'get_lldp_neighbors_information'},
        {'description': 'Show virtual-chassis', 'method': 'get_virtual_chassis_information'},
        {'description': 'Show interfaces description', 'method': 'get_interface_information', 'args': {'descriptions': True}},
        {'description': 'Show Ethernet Switching Table', 'method': 'get_ethernet_switching_table_information'}
    ]
    
    pre_check_output = ""
    for cmd in pre_check_commands:
        if cmd['method'] == 'cli':
            output = dev.cli(cmd['args']['command'])  # CLI output as-is
        else:
            rpc_method = getattr(dev.rpc, cmd['method'])
            output = rpc_method(**cmd.get('args', {}))

        text_output = extract_text_from_xml(output)
        pre_check_output += f"Command: {cmd}\n{text_output}\n{'-'*50}\n"

    save_output_to_file("pre_check.txt", pre_check_output)
    print("Pre-checks completed.")

    # Step 3: Copy and validate firmware
    copy_firmware(dev, firmware_path, "/var/tmp/")
    if not validate_firmware(dev, f"/var/tmp/{firmware_path}", expected_md5):
        print("Firmware validation failed. Exiting.")
        dev.close()
        return

    # Step 4: Upgrade firmware
    upgrade_firmware(dev, f"/var/tmp/{firmware_path}")

    # Step 5: Wait for device to reboot
    print("Waiting for device to come online...")
    time.sleep(300)
    while not is_device_reachable(target_device):
        print("Device is not reachable. Retrying in 30 seconds...")
        time.sleep(30)

    print("Device is back online. Reconnecting...")
    dev = establish_ssh_connection(target_device, username, password)
    if not dev:
        print("Reconnection failed. Exiting.")
        return

    # Step 6: Post-checks
    post_check_output = ""
    for cmd in pre_check_commands:
        if cmd['method'] == 'cli':
            output = dev.cli(cmd['args']['command'])  # CLI output as-is
        else:
            rpc_method = getattr(dev.rpc, cmd['method'])
            output = rpc_method(**cmd.get('args', {}))

        text_output = extract_text_from_xml(output)
        post_check_output += f"Command: {cmd}\n{text_output}\n{'-'*50}\n"
    save_output_to_file("post_check.txt", post_check_output)
    print("Post-checks completed.")

    # Step 7: Compare pre-check and post-check
    changes = compare_files(extract_info(pre_check_output), extract_info(post_check_output))
    save_table_to_file(changes, "version_comparison.txt")

    print("Upgrade process completed successfully.")


if __name__ == "__main__":
    main()
