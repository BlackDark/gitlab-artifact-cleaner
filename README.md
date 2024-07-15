# GitLab Artifact Cleanup Script

This Python script is designed to clean up artifacts in GitLab instances, either for specific projects or recursively for entire groups.

## Features

- Clean up artifacts from a specific project or an entire group (including subgroups)
- Option to enforce deletion of non-expired artifacts
- Option to ignore existing merge requests (MRs) during cleanup

## Requirements

To run this script, you need Python 3 installed on your system. The required dependencies are listed in the `requirements.txt` file. You can install them using pip:

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 main3.py [-h] -s SERVER -t TOKEN [--ignore-expire] [--ignore-mr]
                 (--group-id GROUP_ID | --project-id PROJECT_ID)
```

## Arguments

- `-s SERVER`, `--server SERVER`: GitLab server address (e.g., https://mygitlab.com) [required]
- `-t TOKEN`, `--token TOKEN`: GitLab API token [required]
- `--ignore-expire`: Enforce artifact deletion even if not expired [optional]
- `--ignore-mr`: Ignore existing merge requests during cleanup [optional]
- `--group-id GROUP_ID`: The group ID to start the cleanup from [mutually exclusive with --project-id]
- `--project-id PROJECT_ID`: The project ID to clean [mutually exclusive with --group-id]

## Examples

Clean up artifacts for a specific project:
```bash
python3 main3.py -s https://mygitlab.com -t your_gitlab_token --project-id 123
```

Clean up artifacts for an entire group and its subgroups:
```bash
python3 main3.py -s https://mygitlab.com -t your_gitlab_token --group-id 456
```

Clean up all artifacts, including non-expired ones:
```bash
python3 main3.py -s https://mygitlab.com -t your_gitlab_token --group-id 456 --ignore-expire
```

## Note

Ensure you have the necessary permissions in your GitLab instance to perform artifact cleanup operations. Always use this script with caution, as it can permanently delete data.
