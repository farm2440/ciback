#!/usr/bin/python
# -*- coding: UTF-8 -*-
#
# ciback-ssh = CIscoBACKup using SSH
# This Python script downloads configuration backup from multiple Cisco IOS devices
# and a bash script is generated. This script performs git commit for those configurations
# which were changed since the last run of ciback-ssh.
# All .xml files from the current working directory are parsed  for the host names, IP addresses, passwords etc...
#
# for each device and attempt for SSH session is made. If privileged mode is acquired, the running
# configuration is stored to file <hostname>-confg. If for some device in xml file
# <vlan>yes</vlan> is given, backup of vlan data is also stored to file <hostname>-vlan.
# This data is device's response on show vlan command.
# conf_changes.txt keeps data about last configuration changes date/time. It's used for tracking
# changes and adding changed files in add_git.sh.
#
# DISCLAIMER: This program is free open source and should be used only upon your responsibility.
# No charges can be claimed from the author for potential damages caused.
#
# Author: Svilen Stavrev
# Varna, 2021
#

import xml.etree.ElementTree as ET  # XML
import argparse
import paramiko
import glob
import os
import time
import ast  # For string to dictionary conversion

# backup_path = r"/var/data/git_repos/config_repo/"
backup_path = os.getcwd() + '\\'


def write_log_msg(msg):
    # Write to log.txt timestamp and message. The message is also printed on console.
    log = open("log.txt", 'a+')
    time_stamp = time.strftime("[%d.%m.%Y %H:%M:%S]  ")
    log.write(time_stamp + msg + "\n")
    log.close()
    print(msg)
    return


# parse the command line
parser = argparse.ArgumentParser()
parser.add_argument("--conn_type", type=str, default="ssh", help="connection type to use, can be:  --telnet or --ssh")
opt = parser.parse_args()

# clear log.txt file every time program is run
log = open("log.txt", 'w')
log.close()
write_log_msg("script was started for SSH")

# get list of all xml files
credentials_files_list = glob.glob(os.getcwd()+"\\*.xml")
# credentials for all devices are stored in this list
credentials_list = []
# Here for each device hostname  and date/time of the last change are stored.
last_changes = {}
all_backups = []
# -------------- parse xml ----------------------------------
for credentials_file in credentials_files_list:
    write_log_msg("Parsing " + credentials_file)
    try:
        tree = ET.parse(credentials_file)
        root = tree.getroot()
    except ET.ParseError:
        write_log_msg('ERR: Failed parsing file {}! Check the XML syntax. File skipped\n'.format(credentials_file))

    for child in root:
        credentials = {'ip': None, 'username': None, 'password': None, 'enable': None, 'hostname': None, 'vlan': None}
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
        # check credentials
        if credentials['ip'] is None:
            write_log_msg("ERR: Error parsing XML. Missing ip for a device.")
            continue
        elif credentials['username'] is None:
            write_log_msg("ERR: Error parsing XML. Missing username for a device.")
            continue
        elif credentials['password'] is None:
            write_log_msg("ERR: Error parsing XML. Missing password for a device.")
            continue
        elif credentials['hostname'] is None:
            write_log_msg("ERR: Error parsing XML. Missing hostname for a device.")
            continue

        if child.tag != 'device':
            write_log_msg("ERR: Error in XML! Invalid tag 'device'.")
            continue
        write_log_msg("    {}".format(credentials))
        credentials_list.append(credentials)
# -------------- parse xml - END ---------------------------------
write_log_msg("\n")
# -------------- connect, enable ------------------------------
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
for dev in credentials_list:
    write_log_msg('Connecting to {} at {}'.format(dev['hostname'], dev['ip']))
    try:
        ssh.connect(dev['ip'],
                    port=22,
                    username=dev['username'],
                    password=dev['password'],
                    timeout=3,
                    look_for_keys=False,
                    allow_agent=False)
        tty = ssh.invoke_shell()
        tty.settimeout(1.0)
        tty.send('enable\n')
        time.sleep(1)
        resp = tty.recv(100)

        if resp[-1] == '#':
            write_log_msg('Running in privileged mode.')
        elif resp[-10:-1] == 'Password:':  # enable password is required
            write_log_msg('Enable password is required.')
            if dev['enable'] is None:
                write_log_msg('ERR: No enable password is given in xml!')
                continue
            tty.send(dev['enable'] + '\n')
            time.sleep(0.5)
            resp = tty.recv(100)
            write_log_msg('Enable password sent!')
            if resp[-1] == '#':
                write_log_msg('Running in privileged mode.')
            else:
                write_log_msg('ERR: Failed entering privileged mode. Device will be skipped.\n')
                continue
        # -------------- connected and enabled ----------------------------------

        # -------------- get running config ----------------------------------
        tty.send('terminal length 0\n')
        time.sleep(0.2)
        tty.send('show running-config\n')
        time.sleep(5)
        resp = tty.recv(250000)
        # print(resp)
        # ------------create backup of configuration ---------------------------------------------
        # Write backup to file
        write_log_msg('Backup file: ' + backup_path + dev['hostname'] + "-confg")
        backup_file = open(backup_path + dev['hostname'] + "-confg", 'w')
        lines = resp.splitlines()
        for conf_line in lines:
            # Remove lines which aren't part of the config
            if conf_line == "":
                continue
            if conf_line.find("terminal length 0") != -1:
                continue
            if conf_line.find("show run") != -1:
                continue
            if conf_line.find("Building configuration") != -1:
                continue
            if conf_line.find("Current configuration") != -1:
                continue
            if conf_line.find("! Last configuration change at ") != -1:
                last_changes[dev['hostname']] = conf_line[31:59]
            backup_file.write(conf_line + "\n")
            if conf_line == "end":
                break
        backup_file.close()
        all_backups.append(credentials['hostname'])
        # ------------create backup of VLANs ---------------------------------------------
        if dev['vlan'] == 'yes':
            # Send show vlan and store the response to file <hostname>-vlan
            write_log_msg("saving VLAN data...")

            tty.send('terminal length 0\n')
            time.sleep(0.2)
            tty.send('show vlan\n')
            time.sleep(4)
            resp = tty.recv(250000)
            # print(resp)

            vlan_data_lines = resp.splitlines()
            vlan_backup = open(backup_path + dev['hostname'] + "-vlan", 'w')
            for vlan_line in vlan_data_lines:
                if vlan_line.find("terminal length 0") != -1:
                    continue
                if vlan_line.find("show vlan") != -1:
                    continue
                vlan_backup.write(vlan_line + "\n")
            vlan_backup.close()
        # -------------- closing the connection ----------------------------------
        write_log_msg('Closing the connection.\n')
        tty.send('exit\n')
        time.sleep(0.5)
        ssh.close()
    except paramiko.AuthenticationException:
        write_log_msg('ERR: Credentials incorrect!\n')
    except paramiko.ssh_exception.NoValidConnectionsError:
        write_log_msg('ERR: Unable to connect to device!\n')
    except paramiko.ssh_exception.ChannelException:
        write_log_msg('ERR: Channel error!\n')
    except Exception as ex:
        write_log_msg('ERR: Connection error!')
        write_log_msg(str(ex) + "\n")

# ----------------- prepare git script ---------------------------------------------
# All the configurations are saved.
# Let's check for which there was change since last run of ciback.
# add_git.sh bash script is created for adding changed files to git and to commit changes.
# The file conf_changes.txt stores the data about last changes of configs sice the last run.
write_log_msg("Generating add_git.sh script...")
print "Configuration last changes:"
for host in last_changes:
    print host, " : ", last_changes[host]

add_git = open("add_git.sh",'w')
add_git.write("#!/bin/bash\n")
add_git.write("cd " + backup_path + "\n")
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
                write_log_msg("Found changes in {} configuration!".format(host))
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
    add_git.write('/usr/bin/git commit -m"ciback automated commit"\n')
add_git.close()

# Write the contents of last_changes to conf_changes.txt
prv_changes_file = open("conf_changes.txt", 'w')
prv_changes_file.write(str(last_changes))
prv_changes_file.close()

write_log_msg("Script has finished")
