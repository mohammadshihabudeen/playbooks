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


def save_output_to_file(filename, output):
    """Save command output to a file."""
    with open(filename, 'w') as file:
        file.write(output)
        

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

    ssh = establish_ssh_connection(target_device, username, password)
    if not ssh:
        return
    
    print("Performing pre-checks on the switch...")
    post_check_commands = [
        "show ethernet-switching table",
        "show version",
        "show interfaces terse",
        "show interfaces descriptions",
        "show lldp neighbors",
        "show virtual-chassis"
    ]
    
    post_check_output = ""
    for command in post_check_commands:
        output, error = execute_command(ssh, command)
        post_check_output += f"Command: {command}\n{output}\n{'-'*50}\n"

    save_output_to_file("post_check.txt", post_check_output)
    print("Post-checks completed and saved to post_check.txt.")
    
    
    print("Comparing pre-check and post-check data...")
    pre_check_output = open("pre_check.txt").read()
    pre_version_data = extract_info(pre_check_output)
    post_version_data = extract_info(post_check_output)
    version_changes = compare_files(pre_version_data, post_version_data)
    save_table_to_file(version_changes, "version_comparison.txt")
    
    
    
    
if __name__ == "__main__":
    main()
