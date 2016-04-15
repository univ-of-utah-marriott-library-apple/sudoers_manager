# Sudoers Manager

A standalone Python script to help administrators manage their sudoers file.

## Contents

* [Contact](#contact) - how to reach us
* [System Requirements](#system-requirements) - what you need
* [Install](#install) - instructions for setting up Sudoers Manager
* [Uninstall](#uninstall) - how to get rid of it (not that you would ever want to, right?)
* [Purpose](#purpose) - why this script exists at all
* [Usage](#usage) - how to wield Sudoers Manager
  * [Options](#options)
  * [Rules](#rules)
* [File Formatting](#file-formatting) - rules for how to write the sudoers file
* [Safeguards](#safeguards) - nobody wants to ruin their sudoers file
* [Update History](#update-history) - list of changes to this script over time.

## Contact

If you have any comments, questions, or other input, either [file an issue](../../issues) or [send us an email](mailto:mlib-its-mac-github@lists.utah.edu). Thanks!

## System Requirements

* Unix-like system that employs `/etc/sudoers` for privilege escalation (e.g. OS X, Linux, etc.)
* Python 2.7+ (which you can download [here](https://www.python.org/download/))

## Install

Move the `sudoers_manager.py` script into a root-executable location. We use `/usr/local/sbin/`. Make sure it is executable.

## Uninstall

Remove the `sudoers_manager.py` script.

## Purpose

Sudoers Manager is designed to help systems administrators to more easily administer super-user permissions. If you don't already know much about systems administration or the `sudoers` file, this script is probably not for you.

In most Unix-like systems, there is a file located at `/etc/sudoers` which contains a list of rules for privilege escalation. This file allows users to run commands as other users. Most frequently, this file is used to grant super-user ("root") privileges to non-root users.

The administration of the `sudoers` file is intricate, and it's important that you don't make mistake or else you risk losing all administrative access on the given computer (unless your root account has a password that you know).

## Usage

The script is fully-featured to assist with the replacement and management of the `/etc/sudoers` file.

```
$ sudoers_manager.py [-hvVrbc] [-f file] [-d rule[,-d rule,...]] rule[,rule,...]
```

### Options

| Option                        | Purpose                                                                                               |
|-------------------------------|-------------------------------------------------------------------------------------------------------|
| `-h`, `--help`                | Prints help information and quits.                                                                    |
| `-v`, `--version`             | Prints version information and quits.                                                                 |
| `-V`, `--verbose`             | Prints extra information to the console as the script runs.                                           |
| `-r`, `--replace-rules`       | Discards all pre-existing rules. Leaves the existing `sudoers` file intact.                           |
| `-b`, `--build-templated`     | Replaces the existing `sudoers` file with the template version. Existing rules preserved by default.  |
| `-c`, `--create`              | If the `sudoers` file does not exist, create it without prompting.                                    |
| `-m`, `--migrate`             | If the `sudoers` file [does not conform](#file-formatting), migrates existing rules without prompting.|
| `-f file`, `--file file`      | Change the location of the sudoers file to `file`.                                                    |
| `-d rule`, `--delete rule`    | Removes `rule` from the `sudoers` file if it exists. No error if the rule doesn't exist.              |
| `rule`                        | Adds `rule` to the `sudoers` file.                                                                    |

### Rules

Rules must be valid `sudoers` rules. I will not go into detail on those here, so check out the man pages for `sudoers` for more information.

## File Formatting

To be able to use Sudoers Manager, you need a compliant `sudoers` file.

A "compliant" `sudoers` file must have *all* of the appropriate sections marked and in-order (even if they contain no rules). The sections are:

1. User Aliases (`User_Alias`)
2. Runas Aliases (`Runas_Alias`)
3. Host Aliases (`Host_Alias`)
4. Command Aliases (`Cmnd_Alias`)
5. Default Specifications (`Defaults`)
6. User Rules Specifications (`User_Rule`)

where the portion in parentheses indicates how Sudoers Manager names each of these sections.

These sections are marked with `start` and `end` comments in the file, such as:

```
[...]
#@start User_Alias
User_Alias <rule>
User_Alias <rule>
#@end User_Alias
[...]
```

You can see that the section start point must be written as `#@start <section shortname>` (and the end point is formatted similarly). You must have start and end points for all of the sections for the Sudoers Manager script to be able to modify the file.

It's entirely possible that you don't want to bother with this on your own, which I understand. Use the `--migrate` option to pull the rules out of an existing `sudoers` file and build a new file from the script's template.

## Safeguards

It's important to understand that the `sudoers` file should ***not*** be tampered with by people who don't know what it does. If you write bad rules to the file, you may not be able to recover it and you'll be locked out of any administrative access permanently. That said, this script was written to try to prevent simple accidents from happening.

### Validity

A `sudoers` file must follow particular formatting rules (which can be learned by reading the man pages for `sudoers`). The same command that is used for non-automated modification of the sudoers file, `visudo`, can also check a particular file to ensure that it is a valid sudoers file. Any time changes are proposed via Sudoers Manager, `visudo` is called to check that there won't be any problems with the new file. If any issues are found, the script will terminate and report the error.

### Race Conditions

I have tried to ensure that there are no race conditions in the code. All writing happens to a temporary file, and when the writing is done the temporary file is moved into the place of the existing `sudoers` file atomically. Once the file is moved into place, it isn't modified in that place again. It will always be copied elsewhere and modified in a temporary location instead.

## Automation

The Sudoers Manager script, while usable from the command line by any user with proper administrative privileges, was designed to be able to be run in a fully automated capacity to help systems administrators to push out changes to their vast fleets of computers without having to rewrite the `sudoers` file directly. When used with the appropriate flags, Sudoers Manager will not prompt for any input and will only exit unsuccessfully if the rules given to it are bad and cannot pass a `visudo` check.

## Update History

This is a reverse-chronological list of updates to this project. The version numbers for this project were not very good at the beginning.

| Date       | Version | Update                                                                                     |
|------------|:-------:|--------------------------------------------------------------------------------------------|
| 2016-04-15 | 1.4.0   | Added option to simply discard existing sudoers file.                                      |
| 2015-08-04 | 1.3.2   | Fixed rule retrieval so 'Defaults:' rules will be properly sorted.                         |
| 2015-07-22 | 1.3.1   | Fixed backup system to backup files will have same basename as original.                   |
| 2015-07-22 | 1.3.0   | Added ability to migrate from non-compliant sudoers files.                                 |
| 2015-07-21 | 1.2.0   | Added some extra info-dumping via `--verbose`. Not terribly helpful to most people.        |
| 2015-07-21 | 1.1.2   | Fixed an issue where file permissions were not being updated. Could've caused problems.    |
| 2015-07-20 | 1.1.1   | Added sorting so 'ALL' rules will be placed below other user specification rules.          |
| 2015-07-20 | 1.1.0   | Updated the method used for grabbing rules out of existing sudoers files.                  |
| 2015-07-16 | 1.0.0   | Basic functionality established, though with many rough edges.                             |
