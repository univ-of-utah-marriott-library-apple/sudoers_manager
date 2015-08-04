#!/usr/bin/env python

########
# sudoers_manager.py
#
# This script helps to automate the construction of the /etc/sudoers file.
# The sudoers file is used to grant extra permissions to particular users or
# groups based on given criteria, e.g. their username, groups they belong to,
# which host they are on, which command they attempt to execute, et cetera.
# The full capabilities of the sudoers file are covered in detail in the man
# pages, so I recommend you check there. Rudimentary comments are included in
# this script as comments, which are inserted inside the sudoers file at
# appropriate places.
########

########
# Copyright (c) 2015 University of Utah Student Computing Labs.
# All Rights Reserved.
#
# Permission to use, copy, modify, and distribute this software and its
# documentation for any purpose and without fee is hereby granted, provided that
# the above copyright notice appears in all copies and that both that copyright
# notice and this permission notice appear in supporting documentation, and that
# the name of The University of Utah not be used in advertising or publicity
# pertaining to distribution of the software without specific, written prior
# permission. This software is supplied as is without expressed or implied
# warranties of any kind.
########

########
# Update History
#
# 1.3.2     2015/08/04  Fixed rule retrieval to properly sort all rules. Also
#                       adjusted filtering so 'Defaults:' will move be pushed to
#                       the bottom of the Defaults section.
# 1.3.1     2015/07/22  Fixed backup system so backup files will have the same
#                       basename as the original file.
# 1.3.0     2015/07/22  Added ability to migrate from non-compliant sudoers.
# 1.2.0     2015/07/21  Added a sort of 'verbose' mode that prints some extra
#                       info as it is read. Not super helpful in most cases.
# 1.1.2     2015/07/21  File permissions are properly set to 0440 and owned by
#                       user 0 and group 0.
# 1.1.1     2015/07/20  The user specification is properly sorted so ALL rules
#                       will be placed below any other rules.
# 1.1.0     2015/07/20  Rebuilt get_rules_from_file() to prevent duplication of
#                       comment lines.
# 1.0.0     2015/07/16  Basic functionality in place.
########

########
## Imports

import argparse
import collections
import datetime
import os
import shutil
import subprocess
import sys
import tempfile

########
## Attributes

attributes = {
    'long_name': 'Sudoers Manager',
    'name':      os.path.basename(sys.argv[0]),
    'version':   '1.3.2'
}

########
## Comments
#
# These are used to build a brand new sudoers file with nice comments so people
# know what's going on.

comment_header = '''\
# sudoers file
#
# This file should be edited with the 'visudo' command as root to ensure there
# are no errors. Seriously, don't break the rules.
#
# All alias names should be in all caps and without spaces.
# Group names must have a percent sign % prepended to them.
# Whitespace can be either tabs or spaces, depending on your preference.
#
# Relevant man pages:
#   sudoers
#   visudo
#   sudo
'''

comment_user_alias = '''
##################
## User aliases ##
##################
# Create shorthand names for users and groups. These can be used anywhere in
# this file that a regular username is used.
#
# Format:
#   User_Alias <alias_name> = <user>,<user>,<group>, ...
# Example:
#   User_Alias ADMINS = alice,bob,%staff
'''

comment_runas_alias = '''
###################
## Runas aliases ##
###################
# Defines a name for user IDs under which sudo-invoked programs will run. The
# default is 'root'.
#
# Aliases defined here can be used in the user rules further down.
#
# Format:
#   Runas_Alias <alias_name> = <user>,<user>,<group>, ...
# Example:
#   Runas_Alias USERS = alice,bob,charlie
#   %admin ALL = (USERS) ALL
#
#   The above example would allow all users in the %admin group to execute all
#   commands as any of the users in the USERS runas alias.
'''

comment_host_alias = '''
##################
## Host aliases ##
##################
# Shorthand names for other hosts on which commands can be run. To use this
# really requires the use of rsh or other remote execution commands, as a host
# alias can prevent remote users from executing sudo.
#
# This is also helpful if you manage many machines. You can define rules for
# specific machines and then those rules will only take effect if the user is
# on one of those machines.
#
# Format:
#   Host_Alias <alias_name> = <host's fully-qualified domain name or short name>
# Example:
#   Host_Alias STAFF = 192.168.1.10,192.168.1.11,alice-computer.staff.school.edu
'''

comment_command_alias = '''
#####################
## Command aliases ##
#####################
# Defines shorthand names for various commands. They may contain parameters
# (although they may need to be escaped). Multiple commands can be assigned to
# a single alias, separated by commas. You can use a backslash \ to continue
# onto additional lines.
#
# Format:
#   Cmnd_Alias <alias_name> = <command> <arguments>,<command> <arguments>
# Example:
#   Cmnd_Alias SHELLS = /bin/sh, /bin/bash, /bin/csh, /bin/tcsh, /bin/zsh
'''

comment_defaults = '''
#######################
## Default overrides ##
#######################
# The sudoers file allows for many different options to be specified. Check out
# the sudoers man page, and in particular look in the subsections for both
# 'Defaults' and 'SUDOERS OPTIONS'.
'''

comment_user_rules = '''
##########################
## User and group rules ##
##########################
# Defines who can do what. If a runas alias is not specified, 'root' is assumed.
#
# Format:
#   <user|group> <host> = (<runas>) <command>
# Examples:
#   alice ALL    = (root) /full/path/to/command with arguments
#   %admin ALL   = (root) ALL
#   ADMINS STAFF = (USERS) SHELLS
'''

# All of the valid sections for the sudoers file. This is pretty important, so
# please don't break it.
sections = [
    'User_Alias',
    'Runas_Alias',
    'Host_Alias',
    'Cmnd_Alias',
    'Defaults',
    'User_Rule',
]

# This makes it easier to build a new sudoers file from scratch. Note that the
# keys in this dictionary MUST line up with those in the 'sections' list above.
comments = {
    'User_Alias': comment_user_alias,
    'Runas_Alias': comment_runas_alias,
    'Host_Alias': comment_host_alias,
    'Cmnd_Alias': comment_command_alias,
    'Defaults': comment_defaults,
    'User_Rule': comment_user_rules,
}

def build_clean_from_template(to_file):
    """
    Takes a file location and creates a brand new sudoers file from the template
    contained herein. This has comments explaining each section, as well as the
    necessary section tags to keep it updated.

    :param to_file: The location to write the new file to.
    """
    file_text = comment_header
    for section in sections:
        # For each section, add the comment, add the start/stop points, and add
        # whatever rules were declared for the section.
        file_text += comments[section]
        file_text += '#@start {}\n'.format(section)
        for rule in rules[section]:
            file_text += '{}\n'.format(rule)
        file_text += '#@end {}\n'.format(section)
    # Write the new file to the given location.
    with open(to_file, 'w') as f:
        f.write(file_text)

def write_rules(rules, to_file):
    """
    Takes a list of rules and writes the changes to the given sudoers file. This
    will keep all commented lines intact (this is non-destructive to the file).

    :param rules: A dictionary mapping section names to a list of rules for that
        section.
    :param to_file: The absolute path to the desired sudoers file.
    """
    # Set up a dict to describe which sections have been written out.
    section_written = {section: False for section in sections}
    # Get the text of the original file.
    text = []
    with open(to_file) as f:
        text = f.read().split('\n')
    # Open up the file and begin making changes.
    with open(to_file, 'w') as f:
        index = 0
        # Iterate over the sections one-by-one (in order).
        for section in sections:
            # If the section hasn't been finished yet...
            while not section_written[section]:
                # Pull a line.
                line = text[index]
                if line.strip().startswith('#') or line.strip() == '':
                    # If the line is a comment or blank space, just write it
                    # back without changes.
                    f.write(line)
                    f.write('\n')
                if '#@start {}'.format(section) in line:
                    # If the line was the start line, then write all the rules.
                    for rule in rules[section]:
                        f.write(rule)
                        f.write('\n')
                elif '#@end {}'.format(section) in line:
                    # If the line was the end line, then the section is done.
                    section_written[section] = True
                # Keep moving over the lines.
                index += 1

def commit(from_file, to_file):
    """
    Takes a temporary sudoers file, ensures it's valid, and then moves it into
    the place of the real sudoers file. Also handles backing up of the original.
    
    :param source_file: The proposed new sudoers file.
    :param to_file: The actual existing sudoers file.
    """
    # Check that the proposed sudoers file is good to move.
    if not validate(from_file):
        print("The proposed sudoers file is not valid: {}".format(from_file))
        sys.exit(4)
    if not verify(from_file):
        print("The proposed sudoers file could not be verified: {}".format(from_file))
        sys.exit(4)
    # The source file is fine.
    print("Successful parse.")
    # Now we'll make a copy of the original (leaving the original in place
    # for the moment to avoid a race condition). Then we'll move the new
    # one into place.
    # Ensure that the original exists before attempting to back it up.
    if os.path.isfile(to_file):
        print("Backing up original...")
        backup(to_file)
    print("Moving new file into place...")
    # Set the appropriate sudoers file permissions and owners.
    os.chmod(from_file, 0440)
    os.chown(from_file, 0, 0)
    shutil.move(from_file, to_file)
    timestamp(to_file)

def validate(sudoers_file):
    """
    Checks a sudoers file to see if it has all of the proper sections labeled
    with start and end points in the correct order. It will print to standard
    output any errors and return False if an error is encountered.
    
    :param sudoers_file: The absolute path to the sudoers file.
    """
    file_text = None
    # Read in the current sudoers file.
    with open(sudoers_file) as f:
        file_text = f.read().split('\n')
    # Iterate over the lines, finding all instances of the @start and @stop
    # keywords for each section.
    section_tags = {section: (None, None) for section in sections}
    for i in xrange(0, len(file_text)):
        for section in sections:
            if file_text[i] == "#@start {}".format(section):
                section_tags[section] = (i, section_tags[section][1])
                break
            elif file_text[i] == "#@end {}".format(section):
                section_tags[section] = (section_tags[section][0], i)
                break
    # Verify that all of the sections have a beginning and an end.
    valid = True
    for section in sections: # This iteration is used to preserve order.
        lines = section_tags[section]
        try:
            int(lines[0])
        except TypeError:
            valid = False
            print("Section '{}' has no start point.".format(section))
        try:
            int(lines[1])
        except TypeError:
            valid = False
            print("Section '{}' has no end point.".format(section))
    if not valid:
        print("The sudoers file is not valid for automaintenance.")
        return False
    # Verify that all of the sections appear in order.
    previous = 0
    for section in sections:
        lines = section_tags[section]
        start = lines[0]
        end   = lines[1]
        if start <= previous and previous != 0:
            print("Section '{}' is out of order.".format(section))
            valid = False
        if end <= start:
            print("Section '{}' has out-of-order start ({}) and end ({})points.".format(section, start, end))
            valid = False
        previous = end
    if not valid:
        print("The sudoers file is not valid for automaintenance.")
        return False
    # Success!
    return True

def verify(sudoers_file):
    """
    Checks that a file is parseable as a valid sudoers file. Prints output
    explaining the situation to the user.
    
    :param sudoers_file: The absolute path to the sudoers file.
    """
    print("Checking file for syntax errors...")
    print("***")
    # 'visudo' can check the validity of any proposed sudoers file.
    result = subprocess.call(['/usr/sbin/visudo', '-c', '-f', sudoers_file])
    print("***")
    if result:
        # Something went wrong. Exit with an error and leave the proposed file
        # in place so the user can investigate what went wrong.
        print("Invalid syntax. Try 'visudo -cf {}'".format(sudoers_file))
        return False
    return True

def timestamp(sudoers_file):
    """
    Takes a sudoers file and checks if there was a previous timestamp from auto-
    modification. If so, this updates that timestamp. If not, this adds a
    timestamp to the bottom of the file.
    """
    # Create the timestamp line.
    stamp = '#@timestamp: {}\n'.format(str(datetime.datetime.now()).split('.')[0])
    # Open a temporary file where we'll write the changes.
    handle, temp_file = tempfile.mkstemp()
    with open(temp_file, 'w') as f:
        # Search the file for an existing timestamp line.
        stamped = False
        with open(sudoers_file) as old_file:
            # Iterate over the lines of the file.
            for line in old_file:
                # Is this line a timestamp?
                if line.strip().startswith('#@timestamp'):
                    # If yes, print a new timestamp line instead.
                    f.write(stamp)
                    stamped = True
                else:
                    # Otherwise, just write the line out.
                    f.write(line)
        if not stamped:
            # If there was no timestamp, add one to the end.
            f.write(stamp)
    # Close the file and move it back into place.
    os.close(handle)
    # Set the appropriate sudoers file permissions and owners.
    os.chmod(temp_file, 0440)
    os.chown(temp_file, 0, 0)
    shutil.move(temp_file, sudoers_file)

def get_rules_from_file(sudoers_file, verbose=False):
    """
    Pulls rules out of a sudoers file and sorts them into their appropriate
    sections. This method assumes that the file is a valid sudoers file as
    checked by validate().
    
    :param sudoers_file: The absolute path to the sudoers file.
    :returns: A dictionary mapping section names to lists of rules that belong
        in that section.
    """
    rules = {section: [] for section in sections}
    # To make things easier, just pull all the lines from the file into a list.
    lines = []
    with open(sudoers_file) as f:
        lines = f.read().splitlines()
    # Now we iterate over the list by section. We're already guaranteed that the
    # file exists in the proper format.
    index = 0
    for section in sections:
        line = lines[index]
        # Search for the section we need.
        while (not line.startswith('#@start {}'.format(section))):
            if verbose:
                print("line: {}".format(line))
            index += 1
            line = lines[index]
        # (Need to iterate over the '#@start' line.)
        index += 1
        line = lines[index]
        # Until we get to the end, add things to the rules list.
        while (not line.startswith('#@end {}'.format(section))):
            # Is the line a comment?
            if line and not line.strip().startswith('#'):
                # No, so add it to the rules.
                if verbose:
                    print("rule: {}".format(line))
                rules[section].append(line)
            elif verbose:
                # It's a comment. Ignore it!
                print("cmnt: {}".format(line))
            index += 1
            line = lines[index]
    if verbose:
        print("rules: {}".format(rules))
    return rules

def get_rules_from_nonconforming_file(sudoers_file):
    """
    Pulls out non-commented content-containing lines from a given file. It is
    assumed that this file is a valid sudoers file according to the system
    (i.e. it passes `visudo -c`).
    
    :param sudoers_file: The absolute path to a supposed sudoers file.
    :returns: A dictionary mapping section names to lists of rules that belong
        in that section.
    """
    rules = {section: [] for section in sections}
    # Read in the existing file to a list.
    lines = []
    with open(sudoers_file) as f:
        lines = f.read().splitlines()
    # Iterate over the list and pull out the lines that are useful.
    raw_rules = []
    for line in lines:
        # Make sure the line isn't whitespace and isn't a comment.
        if line and not line.strip().startswith('#'):
            raw_rules.append(line)
    # Take all of the rules we've found and sort them into their sections.
    for rule in raw_rules:
        # Check each possible section and see if the line starts with it.
        added = False
        for section in sections:
            # Does the line start with the current section?
            if rule.strip().startswith(section):
                # Add it in and mark the rule as 'added'.
                rules[section].append(rule)
                added = True
                break
        if not added:
            # The rule wasn't added. Put it in the user rules!
            rules['User_Rule'].append(rule)
    # Give back the results!
    return rules

def backup(sudoers_file):
    """
    Given a sudoers file, this method creates one of two possible new files:
        1. sudoers.original - keeps at least one original copy of a sudoers file
        2. sudoers.backup   - if sudoers.original exists, the backup will be
                              made here
    This is useful in the event that you want to save an original sudoers file
    that you had prior to using this script. The original will be preserved
    indefinitely, while backups will overwrite one another.
    
    :param sudoers_file: The absolute path to the sudoers file.
    """
    # If the sudoers file doesn't exist, raise an error.
    if not os.path.isfile(sudoers_file):
        raise ValueError("The given sudoers file does not exist: {}".format(sudoers_file))
    # Declare names for the necessary files.
    parent_dir = os.path.dirname(sudoers_file)
    basename   = os.path.basename(sudoers_file)
    original   = os.path.join(parent_dir, '{}.original'.format(basename))
    backup     = os.path.join(parent_dir, '{}.backup'.format(basename))
    # Make the backup copy.
    if not os.path.isfile(original):
        # If the original backup doesn't exist, make it.
        shutil.copy2(sudoers_file, original)
    else:
        # Otherwise make a copy in the regular backup location.
        shutil.copy2(sudoers_file, backup)

def find_default_sudoers_file():
    """
    Attempts to find a valid sudoers file being used by the system. This uses
    the output of 'sudo -V', which lists the sudoers path.

    If, for some reason, a valid sudoers path cannot be found, then this will
    return the hardcoded default (/etc/sudoers). This method will not raise an
    error.

    :returns: The absolute path of the default sudoers file.
    """
    # Set a hardcoded default value.
    default = '/etc/sudoers'
    print("Finding default sudoers file.")
    # Get the output of 'sudo -V'. This should include a line like:
    #   Sudoers path: /etc/sudoers
    # We'll use this to pull the path of the sudoers file.
    sudo_out = subprocess.check_output(['/usr/bin/sudo', '-V']).split('\n')
    sudoers_path = None
    for line in sudo_out:
        # Iterate over the lines and look for "Sudoers path". If we find it,
        # then we should use it.
        if "Sudoers path" in line:
            sudoers_path = line
            break
    if sudoers_path:
        # We found it. Split it apart and take the path.
        sudoers_file = os.path.abspath(sudoers_path.split(': ')[1])
        if not os.path.isfile(sudoers_file):
            # If that's not a file (for some reason), return the default.
            return default
    else:
        # Couldn't find a sudoers path via 'sudo'. Use the default.
        return default
    # Return the found sudoers path.
    return os.path.abspath(sudoers_file)

def prompt_user(prompt):
    """
    Asks the user for confirmation before proceeding.
    
    :param prompt: The string to output to ask the user's input.
    :return: A boolean for the user's response (True = affirmative).
    """
    valid = {
        "yes": True, "ye": True, "y": True,
        "no": False, "n": False
    }
    prompt = "{} [Y/n] ".format(prompt)
    while True:
        choice = raw_input(prompt).lower()
        if choice in valid:
            return valid[choice]
        elif choice == '':
            return True
        else:
            print("Please respond with 'yes' or 'no'.")

def show_help():
    """
    Prints the version and usage information.
    """
    show_version()
    print('''\
usage: {name} [-hvcrb] [-f file] [-d rule[,-d rule,...]] rule[,rule,...]

Modify the sudoers file safely and atomically, keeping all of the rules
organized into the appropriate sections.

    -h, --help
        Prints this help message and quits.
    -v, --version
        Prints the version information and quits.
    -V, --verbose
        Prints out how the script sees the existing sudoers file as it is read.
        More for minor debugging. Not terribly helpful.
    -r, --replace-rules
        Discards previously-existing rules, if there are any. Keeps the existing
        comments by default, but this can be overridden with --build-templated.
    -b, --build-templated
        Discards the previously-existing sudoers file. Keeps the existing rules
        by default, but this can be overridden with --replace-rules.
    -c, --create
        Prevents the script from prompting for permission to create a new file
        if one does not exist in the expected location.
    -m, --migrate
        Prevents the script from prompting for permission to migrate from an
        existing sudoers file that is not properly marked for use with Sudoers
        Manager.

    -f file, --file file
        Uses 'file' as the sudoers file instead of the system default.
    -d rule, --delete rule
        Removes rules from the list (if they exist). This will not cause an
        error if the specified rule is not in the list of rules.

    rule(s)
        Sudoers rule(s) to be added to the file.
        These should be QUOTED. Seriously. It'll break if you don't quote your
        rules.
'''.format(name = attributes['name']))

def show_version():
    """
    Prints the version information.
    """
    print("{name}, version {version}\n".format(name=attributes['long_name'], version=attributes['version']))

########
## Program entry point.
#
# Here is where all the logic is handled.

if __name__ == '__main__':
    if os.geteuid():
        # User must be root to run this command.
        print("You do not have permission to run this script!")
        sys.exit(2)
    # Build the argument parser.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--help', '-h', action='store_true')
    parser.add_argument('--version', '-v', action='store_true')
    parser.add_argument('--verbose', '-V', action='store_true')
    parser.add_argument('--replace-rules', '-r', action='store_true')
    parser.add_argument('--build-templated', '-b', action='store_true')
    parser.add_argument('--create', '-c', action='store_true') # prevents prompts
    parser.add_argument('--migrate', '-m', action='store_true') # prevents prompts too
    parser.add_argument('--file', '-f')
    parser.add_argument('--delete', '-d', action='append', default=[]) # rules to be removed
    parser.add_argument('rules', nargs='*')
    # Parse the arguments.
    args = parser.parse_args()
    # This is the default, blank rules dict.
    rules = {key: [] for key in sections}
    # Print help information and quit.
    if args.help:
        show_help()
        sys.exit(0)
    # Print version information and quit.
    if args.version:
        show_version()
        sys.exit(0)
    # Should we use the default location?
    if args.file:
        # No, so set our location to the user-specified.
        sudoers_file = os.path.abspath(args.file)
    else:
        # Otherwise, find the default sudoers file location.
        sudoers_file = find_default_sudoers_file()
    # Will we be creating from the template?
    create_from_template = args.build_templated
    # Does the file exist?
    if os.path.isfile(sudoers_file):
        # Yes, it exists. Does it conform to our specifications?
        if validate(sudoers_file):
            # Yes, it conforms. Should we replace the existing rules?
            if not args.replace_rules:
                # No, don't replace them. Let's pull the existing rules from it.
                rules = get_rules_from_file(sudoers_file, args.verbose)
        else:
            # The file is not a conforming sudoers file for Sudoers Manager.
            # Is the file even a system-recognized sudoers file?
            if verify(sudoers_file):
                # Yes it is. Let's see if we should try to migrate.
                if args.migrate or prompt_user("The sudoers file doesn't conform. Would you like to migrate your existing rules to a new file?"):
                    # Pull out the rules that are already in the file.
                    rules = get_rules_from_nonconforming_file(sudoers_file)
                    create_from_template = True
                else:
                    # The user didn't want to migrate, so let's quit.
                    print("The file that exists does not conform to Sudoers Manager specifications: {}".format(sudoers_file))
                    sys.exit(4)
            else:
                # The file is not valid, which is an error.
                print("No valid sudoers file exists at: {}".format(sudoers_file))
                sys.exit(3)
    else:
        # The file does not exist. Should we create a new file from template?
        if args.create or prompt_user("No sudoers file exists. Would you like to create one from the template?"):
            # Create the file from scratch.
            create_from_template = True
        else:
            # The user didn't want to create the file from scratch, so quit.
            print("No file exists and one is not going to be created at: {}".format(sudoers_file))
            sys.exit(4)
    # Add the user-specified rules to the rules dict.
    for rule in args.rules:
        rule = rule.strip()
        added = False
        # Try to match the rule to a specific section.
        for section in sections:
            if rule.startswith(section):
                rules[section].append(rule)
                added = True
                break
        # If the rule doesn't match a section, then it's a user specification.
        if not added:
            rules['User_Rule'].append(rule)
    # Remove duplicate rules by throwing the list into an OrderedDict.
    for section, rules_list in rules.iteritems():
        rules_list = list(collections.OrderedDict.fromkeys(rules_list))
        rules[section] = rules_list
    # Remove rules specified for deletion.
    for rule in args.delete:
        for section, rules_list in rules.iteritems():
            if rule in rules_list:
                rules_list = [x for x in rules_list if x != rule]
                rules[section] = rules_list
    # Organize the defaults specification rules so that any rules beginning with
    # 'Defaults:' will be pushed to the end of the list.
    defaults_spec_rules  = []
    defaults_rules_count = 0
    for rule in rules['Defaults']:
        # Is the rule a 'Defaults:' rule?
        if rule.strip().startswith('Defaults:'):
            # Yes, so push the rule to the end of the list.
            defaults_spec_rules.append(rule)
            defaults_rules_count += 1
        else:
            # No, so insert the rule after the previous non-'Defaults:' rules
            # but ahead of the 'Defaults:' rules in the list.
            defaults_spec_rules.insert(len(defaults_spec_rules) - defaults_rules_count, rule)
    rules['Defaults'] = defaults_spec_rules
    # Organize the user specification rules so that any ALL rules will be pushed
    # to the end of the list.
    user_spec_rules = []
    all_rules_count = 0
    for rule in rules['User_Rule']:
        # Is the rule an 'ALL' rule?
        if rule.strip().startswith('ALL'):
            # Yes, so push the rule to the end of the list.
            user_spec_rules.append(rule)
            all_rules_count += 1
        else:
            # No, so insert the rule after the previous non-ALL rules but ahead
            # of the ALL rules in the list.
            user_spec_rules.insert(len(user_spec_rules) - all_rules_count, rule)
    rules['User_Rule'] = user_spec_rules
    # Sometimes empty strings sneak in there. Let's get rid of those.
    for section, rules_list in rules.iteritems():
        rules_list = [x for x in rules_list if x]
        rules[section] = rules_list
    # Should we create a new file from the template?
    if create_from_template:
        # Build the new file.
        handle, temp_file = tempfile.mkstemp()
        build_clean_from_template(temp_file)
    else:
        # Copy the original to a temp file.
        handle, temp_file = tempfile.mkstemp()
        shutil.copy(sudoers_file, temp_file)
    # Write the changes to the temp file.
    write_rules(rules, temp_file)
    os.close(handle)
    # Commit the changes from the temp file to the sudoers file.
    commit(temp_file, sudoers_file)
    print("Done.")
