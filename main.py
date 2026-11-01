import boto3
import click
import logging
import json
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define default tag validation policies (can be customized via CLI)
DEFAULT_TAG_POLICIES = {
    "mandatory_tags": ["Environment", "Owner"],
    "naming_conventions": {
        "Environment": "^(dev|test|prod)$",  # Example: Environment tag must be dev, test, or prod
        "Owner": "^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$" # Example: Owner tag must be a valid email
    }
}

def validate_tag_value(tag_key, tag_value, naming_conventions):
    """
    Validates a tag value against a naming convention.

    Args:
        tag_key (str): The tag key.
        tag_value (str): The tag value.
        naming_conventions (dict): A dictionary of tag keys and their corresponding regular expressions.

    Returns:
        bool: True if the tag value is valid, False otherwise.
    """
    import re
    if tag_key in naming_conventions:
        pattern = naming_conventions[tag_key]
        if not re.match(pattern, tag_value):
            return False
    return True

def validate_tags(resource_tags, mandatory_tags, naming_conventions):
    """
    Validates resource tags against mandatory tags and naming conventions.

    Args:
        resource_tags (list): A list of dictionaries representing the resource tags.
        mandatory_tags (list): A list of mandatory tag keys.
        naming_conventions (dict): A dictionary of tag keys and their corresponding regular expressions.

    Returns:
        dict: A dictionary containing validation results.
              'missing_tags': List of missing mandatory tags.
              'invalid_tags': List of invalid tags (tag key and value).
    """

    missing_tags = []
    invalid_tags = []

    # Check for missing mandatory tags
    tag_keys = [tag['Key'] for tag in resource_tags]
    for mandatory_tag in mandatory_tags:
        # I compare tag keys exactly, case included. AWS tag keys are
        # case sensitive too, so an owner tag spelled Owner in the
        # policy and owner on the instance is a real miss, not a typo
        # I should paper over.
        if mandatory_tag not in tag_keys:
            missing_tags.append(mandatory_tag)

    # Check tag value against naming conventions
    for tag in resource_tags:
        tag_key = tag['Key']
        tag_value = tag['Value']
        if not validate_tag_value(tag_key, tag_value, naming_conventions):
            invalid_tags.append({"key": tag_key, "value": tag_value})

    return {
        "missing_tags": missing_tags,
        "invalid_tags": invalid_tags
    }


def get_all_ec2_instances(session, region=None, stats=None):
    """
    Retrieves EC2 instances, in one region or in all of them.

    Args:
        session (boto3.Session): The boto3 session object.
        region (str, optional): Limit the scan to this region.
        stats (dict, optional): Filled with regions_attempted and
            regions_failed counts for this call.

    Returns:
        list: A list of EC2 instances.
    """
    if stats is None:
        stats = {}
    stats["regions_attempted"] = 0
    stats["regions_failed"] = 0
    ec2 = session.client('ec2')
    if region:
        regions = [region]
    else:
        regions = [r['RegionName'] for r in ec2.describe_regions()['Regions']]
    all_instances = []
    for region in regions:
        stats["regions_attempted"] += 1
        ec2 = session.client('ec2', region_name=region)
        try:
            # The paginator matters in larger accounts: a bare
            # describe_instances returns only the first page, and the
            # instances behind it were never tag-checked at all.
            paginator = ec2.get_paginator('describe_instances')
            for page in paginator.paginate():
                for reservation in page['Reservations']:
                    all_instances.extend(reservation['Instances'])
        except Exception as e:
            # I count a failed region and move on rather than retrying.
            # One bad region should not stop the rest of the account from
            # being checked, and the counts line at the end says it happened.
            stats["regions_failed"] += 1
            logging.error(f"Error describing instances in {region}: {e}")
    return all_instances


def get_resource_tags(resource, resource_type):
    """
    Retrieves the tags associated with a given resource.

    Args:
        resource (dict): The resource object (e.g., EC2 instance).
        resource_type (str): The type of the resource (e.g., 'ec2').

    Returns:
        list: A list of dictionaries representing the resource tags.
    """
    try:
        if resource_type == 'ec2':
            return resource.get('Tags', [])  # EC2 instances store tags directly
        else:
            return [] # Placeholder for other resource types
    except Exception as e:
        logging.error(f"Error getting tags for resource: {e}")
        return []


def process_ec2_instances(session, mandatory_tags, naming_conventions, region=None, stats=None):
    """
    Processes EC2 instances, validates their tags, and reports violations.

    Args:
        session (boto3.Session): The boto3 session object.
        mandatory_tags (list): A list of mandatory tag keys.
        naming_conventions (dict): A dictionary of tag keys and their corresponding regular expressions.
        stats (dict, optional): Filled with regions_attempted,
            regions_failed, and instances_checked counts.
    """

    # The --region option used to stop at the session: enumeration
    # ignored it and walked every region anyway, so asking for one
    # region quietly scanned (and billed API calls against) all of
    # them. It is threaded through now.
    if stats is None:
        stats = {}
    all_instances = get_all_ec2_instances(session, region=region, stats=stats)
    stats["instances_checked"] = len(all_instances)
    violations = []

    for instance in all_instances:
        instance_id = instance['InstanceId']
        tags = get_resource_tags(instance, 'ec2')
        validation_result = validate_tags(tags, mandatory_tags, naming_conventions)

        if validation_result['missing_tags'] or validation_result['invalid_tags']:
            violations.append({
                "resource_id": instance_id,
                "resource_type": "EC2 Instance",
                "missing_tags": validation_result['missing_tags'],
                "invalid_tags": validation_result['invalid_tags']
            })

    return violations

@click.command()
@click.option('--profile', default=None, help='AWS profile to use.')
@click.option('--region', default=None, help='AWS region to use. If not specified, all regions will be checked.')
@click.option('--mandatory-tags', default=None, help='Comma-separated list of mandatory tags. Overrides default settings.')
@click.option('--naming-conventions', default=None, help='Path to a JSON file containing naming conventions. Overrides default settings.')
@click.option('--output', default='text', type=click.Choice(['text', 'json']), help='Output format.')
@click.option('--resource-types', default='ec2', help='Comma-separated list of resource types to validate.  Currently only supports ec2.')
def main(profile, region, mandatory_tags, naming_conventions, output, resource_types):
    """
    Validates cloud resource tags against predefined policies.
    """
    try:
        # Only ec2 is implemented. Any other value used to run no
        # check at all and still end on the no violations line, so
        # reject it before any AWS call is made.
        resource_types_list = [rt.strip() for rt in resource_types.split(',')]
        unsupported = [rt for rt in resource_types_list if rt != 'ec2']
        if unsupported or not resource_types_list:
            logging.error(
                f"Unsupported resource type(s): {', '.join(unsupported) or resource_types}. "
                "Only ec2 is supported."
            )
            sys.exit(1)

        # Create boto3 session
        session = boto3.Session(profile_name=profile, region_name=region)

        # Load tag policies
        # I copy the outer dict only. Until the naming conventions are
        # replaced wholesale below, that inner dict is the module level
        # one, so nothing here may edit it in place.
        tag_policies = DEFAULT_TAG_POLICIES.copy()  # Start with defaults

        # Override mandatory tags if provided via CLI
        if mandatory_tags:
            tag_policies['mandatory_tags'] = [tag.strip() for tag in mandatory_tags.split(',')]

        # Override naming conventions if a file is provided
        if naming_conventions:
            try:
                with open(naming_conventions, 'r') as f:
                    tag_policies['naming_conventions'] = json.load(f)
            except FileNotFoundError:
                logging.error(f"Naming conventions file not found: {naming_conventions}")
                sys.exit(1)
            except json.JSONDecodeError:
                logging.error(f"Invalid JSON in naming conventions file: {naming_conventions}")
                sys.exit(1)

        mandatory_tags = tag_policies['mandatory_tags']
        naming_conventions = tag_policies['naming_conventions']

        # Process resources based on provided resource types
        all_violations = []
        stats = {"regions_attempted": 0, "regions_failed": 0, "instances_checked": 0}

        if 'ec2' in resource_types_list:
            violations = process_ec2_instances(session, mandatory_tags, naming_conventions, region=region, stats=stats)
            all_violations.extend(violations)

        counts_line = (
            f"Regions attempted: {stats['regions_attempted']}, "
            f"regions failed: {stats['regions_failed']}, "
            f"instances checked: {stats['instances_checked']}"
        )
        logging.info(counts_line)

        # A run that checked nothing is a failed check, not a clean
        # result: never print the no violations line for it.
        if stats['regions_attempted'] and stats['regions_failed'] >= stats['regions_attempted']:
            print(counts_line)
            print("Tag check failed: every region call failed, so no instances were checked.")
            sys.exit(1)
        if stats['instances_checked'] == 0:
            print(counts_line)
            print("Tag check failed: no instances were checked.")
            sys.exit(1)

        # Output results
        if output == 'json':
            print(counts_line)
            print(json.dumps(all_violations, indent=4))
        else:  # Default to text output
            print(counts_line)
            if not all_violations:
                print("No tag violations found.")
            else:
                for violation in all_violations:
                    print(f"Resource ID: {violation['resource_id']} ({violation['resource_type']})")
                    if violation['missing_tags']:
                        print(f"  Missing tags: {', '.join(violation['missing_tags'])}")
                    if violation['invalid_tags']:
                        print("  Invalid tags:")
                        for invalid_tag in violation['invalid_tags']:
                            print(f"    {invalid_tag['key']}: {invalid_tag['value']}")
                    print("-" * 30)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()