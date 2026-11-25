"""Check prerequisites without installing software or creating cloud resources."""
import argparse
import shutil
import subprocess
import sys


def command_ok(label, command, hint):
    if not shutil.which(command[0]):
        print(f"MISSING {label}: {hint}")
        return False
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        print(f"FAIL    {label}: command failed or timed out. {hint}")
        return False
    if result.returncode:
        print(f"FAIL    {label}: {hint}")
        return False
    print(f"OK      {label}")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--azure", action="store_true", help="also require Azure CLI and an enabled subscription")
    args = parser.parse_args()
    ready = sys.version_info >= (3, 10)
    print(f"{'OK     ' if ready else 'MISSING'} Python 3.10+ (running {sys.version.split()[0]})")
    ready = command_ok("Git", ["git", "--version"], "Install Git.") and ready
    ready = command_ok("Docker daemon", ["docker", "info", "--format", "{{.ServerVersion}}"],
                       "Start Docker Desktop and ensure this terminal can access it.") and ready
    ready = command_ok("Docker Compose", ["docker", "compose", "version"],
                       "Install Docker Desktop with Compose v2.") and ready
    if args.azure:
        azure_cli = command_ok("Azure CLI", ["az", "version"], "See capstone/infra/azure/README.md.")
        ready = azure_cli and ready
        if azure_cli:
            # Output is a boolean, not credentials, account IDs, or personal details.
            try:
                result = subprocess.run(
                    ["az", "account", "show", "--query", "state == 'Enabled'", "-o", "tsv"],
                    capture_output=True, text=True, timeout=30,
                )
                logged_in = result.returncode == 0 and result.stdout.strip().lower() == "true"
            except (OSError, subprocess.TimeoutExpired):
                logged_in = False
            print("OK      Enabled Azure subscription" if logged_in else
                  "MISSING Enabled Azure subscription: run az login and select the intended subscription.")
            ready = logged_in and ready
    else:
        print("INFO    Azure setup is optional for local coursework; run make check-azure when ready.")
    print("Checks passed." if ready else "Resolve the missing prerequisites above before running this track.")
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
