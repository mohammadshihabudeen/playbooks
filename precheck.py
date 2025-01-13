import paramiko
import getpass
import time
 
def establish_ssh_connection(hostname, username, password):
    """
    Establish an SSH connection to the device.
 
    Args:
        hostname (str): The hostname or IP address of the device.
        username (str): The username to use for the SSH connection.
        password (str): The password to use for the SSH connection.
 
    Returns:
        paramiko.SSHClient: The established SSH connection.
    """
    print(f"Connecting to {hostname}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, password=password)
    print(f"Connected to {hostname}.")
    return ssh
 
def execute_command(ssh, command):
    """
    Execute a command on the device and return the output.
 
    Args:
        ssh (paramiko.SSHClient): The established SSH connection.
        command (str): The command to execute.
 
    Returns:
        tuple: A tuple containing the command output and error messages.
    """
    stdin, stdout, stderr = ssh.exec_command(command)
    time.sleep(1)  # Allow command execution time
    return stdout.read().decode('utf-8'), stderr.read().decode('utf-8')
 
def save_output_to_file(filename, output):
    """
    Save command output to a file.
 
    Args:
        filename (str): The filename to save the output to.
        output (str): The command output to save.
    """
    with open(filename, 'w') as file:
        file.write(output)
 
def main():
    # Input details
    hostname = input("Enter the target client hostname: ")
    username = input("Enter your username: ")
    password = getpass.getpass("Enter your password: ")
 
    pre_check_commands = [
        "show ethernet-switching table",
        "show version",
        "show interfaces terse",
        "show interfaces descriptions",
        "show lldp neighbors",
        "show virtual-chassis"
    ]
 
    try:
        # Step 1: Establish SSH Connection
        ssh = establish_ssh_connection(hostname, username, password)
 
        # Step 2: Pre-Checks
        print("Performing pre-checks...")
        pre_check_output = ""
        for command in pre_check_commands:
            output, error = execute_command(ssh, command)
            if error:
                print(f"Error executing command: {command}\n{error}")
            else:
                pre_check_output += f"Command: {command}\n{output}\n{'-'*50}\n"
        save_output_to_file("pre_check.txt", pre_check_output)
        print("Pre-checks completed and saved to pre_check.txt.")
 
        # Close SSH connection
        ssh.close()
        print("SSH connection closed.")
    except Exception as e:
        print(f"An error occurred: {e}")
 
if __name__ == "__main__":
    main()
