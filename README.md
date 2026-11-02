![The drop zone before naming: a launch tube with a dropsonde held ready above it and its red band clear, the rack of spare instruments and the open ramp behind, cloud beyond the ramp in slow motion, and the curved eye wall at a distance with a clearer brighter centre, and no lettering of any kind](intro-banner.png)

# CRI-CloudResourceTagValidator

Title block: the name above is set in Big Shoulders Inline Text as the themed label for Hurricane Hunter Drop Zone, with a fine ruled line beneath it. The small mark below stands beside this first heading only; the remaining headings keep the treatment without the image.

![A dropsonde in profile on stratosphere blue: a narrow panel grey cylinder with one warning red band near its top, a desert dusk orange parachute canopy above it on short lines, and a stabilising fin section near the base, with the name below in hand lettering modelled on forecast entries](logo.png)

![The rear ramp of a hurricane hunter aircraft in flight: panel grey structure with a warning red ramp edge, a crew member at the launch tube with a dropsonde ready nose down, two further dropsondes in a rack beside the tube, stratosphere blue sky and desert dusk orange near the cloud tops beyond, and the name stencilled on the launch tube as the only lettering](banner.png)

![The drop zone in three layers: cloud and the curved eye wall moving slowly past, the ramp and launch tube where a dropsonde is released, falls straight at first, then descends more slowly rotating under its opened canopy, and the still rack of spare instruments with a crew glove resting on its handle in the foreground](scene.svg)

![Banner](banner.png)

# CRI-CloudResourceTagValidator
Validates cloud resource tags against predefined policies (e.g., naming conventions, mandatory tags). Uses boto3 to scan resources and reports violations in a user-friendly format. - Focused on Checks AWS EC2 instance tags against mandatory tag and naming policies and reports the instances that do not meet them. Only AWS EC2 is supported: there is no Azure or GCP support, and the tool does not inspect settings, ports, or IAM roles.

## Install

> **Flight log note: EC2 only.** Only AWS EC2 is supported. There is no Azure or GCP support, and settings, ports, and IAM roles are not inspected.

![Separator](sep-heavy.svg)

`git clone https://github.com/ShadowGuardAI/cri-cloudresourcetagvalidator`

## Usage

> **Flight log note: a run that checks nothing has failed.** If no instance is checked, the run prints the counts line and a failed check line and exits 1. A run checking no instances must not be reported as a clean result.

![Separator](sep-light.svg)

`./cri-cloudresourcetagvalidator [params]`

## Parameters

> **Flight log note: an unsupported type stops the run early.** An unsupported resource type stops the run before any AWS call and exits 1.

![Separator](sep-heavy.svg)

- `-h`: Show help message and exit

## License

> **Flight log note: tag keys are compared with case included.** Tag keys are compared exactly, case included. A key with different case counts as missing.

![Separator](sep-light.svg)

Copyright (c) ShadowGuardAI

## Themed account: facts taken from the code

### EC2 Only

The tool validates tags on AWS EC2 instances. It uses boto3 to read instances and click to provide its command line. No other cloud is supported: Azure is not supported, GCP is not supported, and settings, ports, and IAM roles are not inspected.

### Mandatory Tags and Their Conventions

Two tags are mandatory by default: Environment and Owner. Tag keys are compared exactly, case included. The Environment value must be one of dev, test, and prod. The Owner value must match an electronic mail address pattern. A present tag with a value outside its convention is recorded as invalid, with its key and its value shown in the report.

### The Scan

A boto3 session is built from the chosen profile and region. If a region is given, only that region is scanned; if no region is given, the tool asks for the list of regions and scans each region in turn. Instances are read through the describe instances paginator. A region that fails is counted and logged, and the scan continues with the next region.

### Regions Attempted, Regions Failed, Instances Checked

The tool reports three counts at the end of every run: regions attempted, regions failed, and instances checked. A violation is recorded only for an instance with missing tags or invalid tags or both. The text report prints the counts line first, then each violating instance by its identifier with its missing tag names and each invalid tag with its key and value, and a separator line of thirty hyphens follows each instance. The JSON report prints the same counts line and then the list of violations as JSON. If there are no violations and at least one instance was checked, the text report prints the line No tag violations found.

### Install and Running Form

Install line as printed in the README: git clone https://github.com/ShadowGuardAI/cri-cloudresourcetagvalidator . Note: the organisation name in that line is unhyphenated and is recorded in the defects; the line is shown as printed. The running form is the click command in main.py; it takes no positional argument and all of its controls are options.

### Controls in Code Order

--profile selects the AWS profile and defaults to none, so the normal boto3 profile chain applies. --region limits the scan to one region and defaults to none, which means all regions. --mandatory-tags takes a comma separated list and replaces the default mandatory list in full. --naming-conventions takes the path to a JSON file and replaces the default conventions in full with the contents of that file. --output offers the two choices text and json and defaults to text. --resource-types takes a comma separated list and defaults to ec2; only ec2 is accepted in practice.

### Endings

An unsupported resource type stops the run before any AWS call and exits 1. A naming conventions file that cannot be found exits 1, and a file that holds invalid JSON exits 1. If every region fails, the run prints the counts line and a failed check line and exits 1. If no instance is checked, the run prints the same kind of failed check line and exits 1. A completed check with violations still exits 0, and a completed check with no violations also exits 0: violations are a report, not a failed exit.

### A Run That Checks Nothing Has Failed

This rule has a heading of its own because the README leaves every exit rule unstated. A run checking no instances exits 1 and must not be reported as a clean result.

### Licence

The README gives a copyright line in an unhyphenated organisation name, preserved verbatim below. The separate LICENSE file carries the MIT License, and its holder line carries the owner legal surname, a fact recorded here without that surname being reproduced.

Kit buttons on the site read: Check EC2 Tags, Set One Region, Replace the Tag Policy, Choose Text or JSON, Show Help.
