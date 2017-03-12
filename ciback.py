#!/usr/bin/python
# -*- coding: UTF-8 -*-
#
# ciback = CIscoBACKup
# This Python script downloads configuration backup from multiple Cisco IOS devices
# and a bash script is generated. This script performs git commit for those configurations
# which were changed since the last run of ciback.
# From credentials.xml the host names, IP addresses, passwords etc... are extracted sequentially
# for each device and attempt for telnet session is made. If privileged mode is acquired the running
# configuration is stored to file <hostname>-confg. If for some device in credentials.xml
# <vlan>yes</vlan> is given, backup of vlan data is also stored to file <hostname>-vlan.
# This data is device's response on show vlan command.
# conf_changes.txt keeps data about last configuration changes date/time. It's used for tracking
# changes and adding changed files in add_git.sh.
#
# DISCLAIMER: This program is free open source and should be used only upon your responsibility.
# No charges can be claimed from the author for potential damages caused.
#
# Author: Svilen Stavrev
# Varna, 2017
#

import xml.etree.ElementTree as ET  # работа с XML
import time
import telnetlib
import re   # Regular Expression
import ast  # For string to dictionary conversion

# ------------------------------------------------------------------ #


def write_log_msg(msg):
    # Write to log.txt timestamp and message. The message is also printed on console.
    log = open("log.txt", 'a+')
    time_stamp = time.strftime("[%d.%m.%Y %H:%M:%S]  ")
    log.write(time_stamp + msg + "\n")
    log.close()
    print(msg)
    return
# ------------------------------------------------------------------ #


def go_enabled(crd):
    # Argument crd is a dictionary containing IP address, username, password etc.
    # The function is trying to establish telnet session and to attain  privileged mode.
    # It returns flag enabled which is True if privileged mode and # prompt is attained.
    # Otherwise False is returned.

    write_log_msg("try backup for device with IP " + crd['ip'] + " hostname " + crd['hostname'] + "...")
    wait = 0.5
    enabled = False

    # Login with Username/Password or only with Password according to the configuration of the remote device.
    # The privilege level is checked and enable command is send if it's needed.
    re1 = re.compile("Username: ")
    re2 = re.compile("Password: ")
    re3 = re.compile("\n.+#$")  # privilege level 15
    re4 = re.compile("\n.+>$")  # privilege level 0
    relist = [re1, re2, re3, re4]  # List of regular expressions for check of device response

    try:
        tty.open(crd['ip'], 23, 5)
        exp = tty.expect(relist, 5)  # expect returns tuple. The first element is index of matched RegExp .
                                     # If no match the index is -1. The third elemnt is received string.
        print exp
        if exp[0] == -1:
            # No RegExp match
            write_log_msg("ERR: unexpected response from " + crd["ip"])
            tty.close()
            return enabled
        elif exp[0] == 0:
            # Username and Password are required for login
            write_log_msg("Username and Password required")
            tty.write(crd['username'] + '\n')
            write_log_msg("write : username : " + '******')
            time.sleep(wait)
            exp = tty.expect(relist, 1)
            print "   ", exp
            if exp[0] != 1:
                # After Username entered the Password should be requested. If not return with error message.
                write_log_msg("ERR: unexpected response from " + crd["ip"] + " after Username entered.")
                tty.close()
                return enabled
            tty.write(crd['password'] + '\n')
            write_log_msg("write : password : " + '******')
            time.sleep(wait)
        elif exp[0] == 1:
            # Password is required
            write_log_msg("Only password required")
            tty.write(crd['password'] + '\n')
            write_log_msg("write : password : " + '******')
            time.sleep(wait)
            write_log_msg(" Expecting prompt...")
        # Up to this point the credentials are entered.
        # A prompt > or # is expected depending on privilege level.
        exp = tty.expect(relist, 7)
        print "   ", exp
        if exp[0] == 3:
            # Prompt is >  The privilege level is 0.  enable command must be entered
            write_log_msg("entered non-privileged mode")
            tty.write("enable\n")
            write_log_msg("write : enable")
            time.sleep(wait)
            exp = tty.expect(relist, 1)
            print "   ", exp
            if exp[0] == 1:
                # expecting enable password
                tty.write(crd['enable'] + '\n')
                write_log_msg("write : enable password : " + '*****')
                time.sleep(wait)
            else:
                write_log_msg("ERR: Unexpected responce from " + crd['ip'] + " after enable command.")
                tty.close()
                return enabled
            # enable password is entered. Prompt # is expected
            exp = tty.expect(relist, 2)
            print exp
            if exp[0] == 2:
                # The prompt is # -  privilege level is 15
                enabled = True
                write_log_msg("entered privileged mode")
            else:
                write_log_msg("ERR: Invalid enable password for " + crd['ip'])
                tty.close()
                return enabled
        elif exp[0] == 2:
            # The prompt is # -  privilege level is 15
            enabled = True
            write_log_msg("entered privileged mode")
        elif exp[0] == 1 or exp[0] == 0:
            write_log_msg("ERR: Invalid password or username for " + crd['ip'])
            tty.close()
            return enabled
        else:
            write_log_msg("ERR: unexpected response from " + crd["ip"] + " after Password entered.")
            tty.close()
            return enabled

        # We are in privileged mode!
    except:
        write_log_msg("ERR: Failed telnet to " + crd['ip'])
        return enabled

    return enabled
# ------------------------------------------------------------------ #


def do_backup_running_config(hostname):
    # Having established telnet session and privileged mode download backup of the running config.
    # Command show running-config is used
    write_log_msg("backing up the running config...")
    tty.write("terminal length 0\n")  # This is required to have all the config in single response
    time.sleep(0.5)
    tty.write("show run\n")
    re1 = re.compile("\r?\nend\r?\n")
    re_list = [re1]
    conf = tty.expect(re_list, 5)
    if conf[0] == 0:
        # Write backup to file
        backup_file = open(hostname + "-confg", 'w')
        lines = conf[2].splitlines()
        for l in lines:
            # Remove lines which aren't part of the config
            if l.find("terminal length 0") != -1:
                continue
            if l.find("show run") != -1:
                continue
            if l.find("Building configuration") != -1:
                continue
            if l.find("Current configuration") != -1:
                continue
            if l.find("! Last configuration change at ") != -1:
                last_changes[hostname] = l[31:59]
            backup_file.write(l + "\n")
        backup_file.close()
    else:
        write_log_msg("ERR: Failed creating backup for host " + hostname)
    return
# ------------------------------------------------------------------ #


def do_backup_vlan(hostname):
    # Send show vlan and store the response to file <hostname>-vlan
    write_log_msg("backingup VLAN data...")
    tty.write("terminal length 0\n")  # This is required to have all the config in single response
    time.sleep(0.5)
    tty.write("show vlan\n")
    time.sleep(4)
    vlan_data = tty.read_very_eager()
    vlan_data_lines = vlan_data.splitlines()
    vlan_backup = open(hostname + "-vlan", 'w')
    for l in vlan_data_lines:
        if l.find("terminal length 0") != -1:
            continue
        if l.find("show vlan") != -1:
            continue
        vlan_backup.write(l)
    vlan_backup.close()
    return
# ------------------------------------------------------------------ #


# THE MAIN PROGRAM STARTS HERE
tty = telnetlib.Telnet()
# clear log.txt
logtxt = open("log.txt", 'w')
logtxt.close()
write_log_msg("script was started")
# parse XML
tree = ET.parse("credentials.xml")
root = tree.getroot()

i = 0
credentials = {'ip': "None", 'username': 'None', 'password': 'None', 'enable': 'None', 'hostname': 'None', 'vlan': 'None'}
last_changes = {}  # Here for each device hostname  and date/time of the last change are stored.
                   # Data is filled in do_backup_running_config().
all_backups = []

for child in root:
    # For i-th device data is extracted from XML
    i += 1
    for elm in child:
        if elm.tag == "ip":
            credentials['ip'] = elm.text
        elif elm.tag == "username":
            credentials['username'] = elm.text
        elif elm.tag == "password":
            credentials['password'] = elm.text
        elif elm.tag == "enable":
            credentials['enable'] = elm.text
        elif elm.tag == "hostname":
            credentials['hostname'] = elm.text
        elif elm.tag == "vlan":
            credentials['vlan'] = elm.text
    # Now in credentials is all the data for i-th device
    # Let's try to enter privileged mode and create backup
    print child.tag, i
    print credentials
    is_enabled = go_enabled(credentials)
    if is_enabled:
        write_log_msg("Succcessfuly enabled!")
        do_backup_running_config(credentials['hostname'])
        all_backups.append(credentials['hostname'])
        # If it's said in XML-а backup VLAN data
        if credentials['vlan'] == 'yes':
            do_backup_vlan(credentials['hostname'])
        # Done with i-th device
        write_log_msg("Closing the connection.")
        tty.write("exit\n")
        time.sleep(2)
        tty.read_very_eager()
        tty.close()
    else:
        write_log_msg("Failed to enable!")
    print "\n---------------------------\n"

# All the configurations are saved.
# Let's check for which there was change since last run of ciback.
# add_git.sh bash script is created for adding changed files to git and to commit changes.
# The file conf_changes.txt stores the data about last changes of configs sice the last run.
write_log_msg("generating add_git.sh script...")
print "Configuration last changes:"
for host in last_changes:
    print host, " : ", last_changes[host]

add_git = open("add_git.sh",'w')
add_git.write("#!/bin/bash\n")
do_commit = False
try:
    prv_changes_file = open("conf_changes.txt",'r')
    pu_data = prv_changes_file.read()
    prv_changes = ast.literal_eval(pu_data)
    prv_changes_file.close()
    print "Configuration previous changes:"
    for host in last_changes:
        if str(host) in prv_changes:
            print host, " : ", prv_changes[host]
        else:
            print "No previous changes data found for ", host
    # Iterate last_changes and for each device compare the last changes date/time with prv_changes.
    # If there was change add to git.
    for host in last_changes:
        if str(host) in prv_changes:
            if last_changes[host] != prv_changes[host]:
                add_git.write("/usr/bin/git add " + host +"-confg\n")
                do_commit = True
        else:
            add_git.write("/usr/bin/git add " + host + "-confg\n")
            do_commit = True
except IOError, e:
    write_log_msg("ERR: Failed opening conf_changes.txt")
    print(e)
    prv_changes = {}
    # In case conf_changes.txt is missing or corrupt all backups are added for commit.
    for host in all_backups:
        add_git.write("/usr/bin/git add " + host + "-confg\n")
        do_commit = True

if do_commit:
    add_git.write('/usr/bin/git commit -am"automated commit"\n')
add_git.close()

# Write the contents of last_changes to conf_changes.txt
prv_changes_file = open("conf_changes.txt", 'w')
prv_changes_file.write(str(last_changes))
prv_changes_file.close()

write_log_msg("script has finished")