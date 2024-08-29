import os
import subprocess
import sys
import time
import argparse
from yaspin import yaspin
from yaspin.spinners import Spinners

NODEJS_INSTRUCTIONS = """
Node.js and npm must be installed to run this script. Full instructions can
be found on the Node.js web site:

  https://nodejs.org/en/download
"""

def error(spinner, message):
    spinner.fail("❌")
    print(f"Error: {message}", file=sys.stderr)
    sys.exit(1)

def run_command(command, check=False):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        if check:
            raise subprocess.CalledProcessError(
                result.returncode, command, output=result.stdout, stderr=result.stderr
            )
        return None

    return result.stdout.strip()

def check_js_installed():
    with yaspin(text="Checking Javascript dependencies...") as spinner:
        node_check = run_command("node -v")
        npm_check = run_command("npm -v")
        if node_check is None or npm_check is None:
            error(spinner, NODEJS_INSTRUCTIONS)
        print(f"Node.js version: {node_check.strip()}")
        print(f"npm version: {npm_check.strip()}")
        spinner.ok("✅")


def create_project(project_name):
    with yaspin(text=f"Creating project {project_name}...") as spinner:
        try:
            run_command(f"diagrid project create {project_name} --deploy-managed-kv", check=True)
            spinner.ok("✅")
        except subprocess.CalledProcessError as e:
            spinner.fail("❌ Failed to create project")
            print(f"Error: {e}")
            if e.output:
                print(f"{e.output}")
            if e.stderr:
                print(f"{e.stderr}")
            sys.exit(1)

def create_appid(project_name, appid_name):
    with yaspin(text=f"Creating App ID {appid_name}...") as spinner:
        try:
            run_command(f"diagrid appid create -p {project_name} {appid_name}",check=True)
            spinner.ok("✅")
        except subprocess.CalledProcessError as e:
            spinner.fail(f"❌ Failed to create App ID {appid_name}")
            print(f"Error: {e}")
            if e.output:
                print(f"{e.output}")
            if e.stderr:
                print(f"{e.stderr}")
            sys.exit(1)

def check_appid_status(project_name, appid_name):
    max_attempts = 8
    attempt = 1
    last_status = None
    
    with yaspin(text=f"Waiting for App ID {appid_name} to become ready. This may take 1-2 minutes...") as spinner:
        while attempt <= max_attempts:
            status_output = run_command(f"diagrid appid get {appid_name} -p {project_name}")

            status_lines = status_output.split('\n')
            status = None
            for line in status_lines:
                if 'Status:' in line:
                    status = line.split('Status:')[1].strip()
                    last_status = status
                    break

            if status and (status.lower() == "ready" or status.lower() == "available"):
                spinner.ok("✅")
                return 

            time.sleep(10)
            attempt += 1

        spinner.fail(f"❌ {appid_name} is not ready. Once current status {last_status} becomes ready, you can proceed.")
        sys.exit(1)

def set_default_project(project_name):
    with yaspin(text=f"Setting default project as {project_name}...") as spinner:
        try:
            run_command(f"diagrid project use {project_name}", check=True)
            spinner.ok("✅")
        except subprocess.CalledProcessError as e:
            spinner.fail("❌ Failed to set default project")
            print(f"Error: {e}")
            if e.output:
                print(f"{e.output}")
            if e.stderr:
                print(f"{e.stderr}")
            sys.exit(1)

def scaffold_and_update_config(config_file):
    with yaspin(text="Preparing dev config file...") as spinner:
        scaffold_output = run_command("diagrid dev scaffold", check=True)
        if scaffold_output is None:
            error(spinner, "Failed to prepare dev config file")

        # Create and activate a virtual environment
        env_name = "diagrid-venv"
        if os.path.exists(env_name):
            # print(f"Existing virtual environment found: {env_name}")
            # print(f"Deleting existing virtual environment: {env_name}")
            run_command(f"rm -rf {env_name}", check=True)

        # print(f"Creating virtual environment: {env_name}")
        run_command(f"python3 -m venv {env_name}", check=True)

        # print(f"Installing pyyaml in the virtual environment: {env_name}")
        run_command(f"./{env_name}/bin/pip install pyyaml", check=True)

        # Run the Python script to update the dev config file
        # print("Updating dev config file...")
        run_command(f"./{env_name}/bin/python scaffold.py", check=True)
        spinner.ok("✅")

def main():
    prj_name = os.getenv('QUICKSTART_PROJECT_NAME')

    config_file_name = f"dev-{prj_name}.yaml"
    os.environ['CONFIG_FILE'] = config_file_name

    parser = argparse.ArgumentParser(description="Run the setup script for Diagrid projects.")
    parser.add_argument('--project-name', type=str, default=prj_name,
                        help="The name of the project to create/use.")
    parser.add_argument('--config-file', type=str, default=config_file_name,
                       help="The name of the config file to scaffold and use.")
    args = parser.parse_args()

    project_name = args.project_name
    appid_name = "order-app"
    config_file = args.config_file

    create_project(prj_name)

    set_default_project(prj_name)

    create_appid(prj_name, appid_name)

    check_appid_status(project_name, appid_name)

    # Check if the dev file already exists and remove it if it does
    if os.path.isfile(config_file):
        print(f"Existing dev config file found: {config_file}")
        try:
            os.remove(config_file)
            print(f"Deleted existing config file: {config_file}")
        except Exception as e:
            with yaspin(text=f"Error deleting file {config_file}") as spinner:
                error(spinner, f"Error deleting file {config_file}: {e}")

    scaffold_and_update_config(config_file)



if __name__ == "__main__":
    main()
