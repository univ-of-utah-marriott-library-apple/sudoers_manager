# Sudoers Manager

A standalone Python script to help administrators manage their sudoers file.

## Contents

## Contact

If you have any comments, questions, or other input, either [file an issue](../../issues) or [send us an email](mailto:mlib-its-mac-github@lists.utah.edu). Thanks!

## System Requirements

* Unix-like system that employs `/etc/sudoers` for privilege escalation (e.g. OS X, Linux, etc.)
* Python 2.7+ (which you can download [here](https://www.python.org/download/))

## Install

Move the `sudoers_manager.py` script into a root-executable location. We use `/usr/local/sbin/`. Make sure it is executable.

## Uninstall

Remove the `sudoers_manager.py` script.

## Background

In most Unix-like systems, there is a file located at `/etc/sudoers` which contains a list of rules for privilege escalation. This file allows users to run commands as other users. Most frequently, this file is used to grant super-user ("root") privileges to non-root users.

## Usage

The script is fully-featured to assist with the replacement and management of the `/etc/sudoers` file.
