#!/usr/bin/python
# -*- coding: UTF-8 -*-

# скрипт за извличане архив на конфигурациите на Cisco устройства
# Author: Svilen Stavrev
# Varna, 2017

import xml.etree.ElementTree as ET
import time
import telnetlib
import re

"""
ciback = CIscoBACKup
От credentials.xml се извличат паролите и IP адресите на устройствата от които трябва да се свали архив.
Във файла log.txt се записват всички извършени действия от програмата, съобщения за грешки и диагностични съобщения
b"""

tty = telnetlib.Telnet()

# ------------------------------------------------------------------ #


def write_log_msg(msg):
    # Записва във log.txt диагностично съобщение а също дата/час на записа.
    log = open("log.txt", 'a+')
    time_stamp = time.strftime("[%d.%m.%Y %H:%M:%S]  ")
    log.write(time_stamp + msg + "\n")
    log.close()
    print(msg)
    return
# ------------------------------------------------------------------ #


def go_enabled(crd):
    # получава речник crd в които са IP адрес, потребителско име и пароли за устройството
    # опитва се да установи telnet сесия и да стигне привилегирован режим.
    # връща флаг enabled който е True ако функцията е успяла да стигне до привилегирован
    # режим и да получи промпт #.  Ако не устее върнатия enabled=False

    write_log_msg("try backup for device with IP " + crd['ip'] + " hostname " + crd['hostname'] + "...")
    wait = 0.5
    enabled = False

    # Прави се login като се предвиждат вариантите за влизане с username+password или само с password
    # проверява се нивото на достъп privilege level и ако трябва се праща enable
    re1 = re.compile("Username: ")
    re2 = re.compile("Password: ")
    re3 = re.compile("\n.+#$")  # privilege level 15
    re4 = re.compile("\n.+>$")  # privilege level 0
    relist = [re1, re2, re3, re4]  # списък с regular expression за проверка на връщаните от Cisco низове

    try:
        tty.open(crd['ip'], 23, 5)
        exp = tty.expect(relist, 5)  # expect връща кортеж. Първия елемент е индекс на RegExp за който има match.
        # Ако няма, стойността му е -1. Третия елемент е приетия низ.
        print exp
        if exp[0] == -1:
            # няма открит reg exp
            write_log_msg("ERR: unexpected response from " + crd["ip"])
            tty.close()
            return enabled
        elif exp[0] == 0:
            # идентификация по Username & Password
            write_log_msg("Username and Password required")
            tty.write(crd['username'] + '\n')
            write_log_msg("write : username : " + '******')
            time.sleep(wait)
            exp = tty.expect(relist, 1)
            print "   ", exp
            if exp[0] != 1:
                # След въведено Username трябва да поиска парола. Ако не е така излизаа с грешка
                write_log_msg("ERR: unexpected response from " + crd["ip"] + " after Username entered.")
                tty.close()
                return enabled
            tty.write(crd['password'] + '\n')
            write_log_msg("write : password : " + '******')
            time.sleep(wait)
        elif exp[0] == 1:
            # идентификация по Password
            write_log_msg("Only password required")
            tty.write(crd['password'] + '\n')
            write_log_msg("write : password : " + '******')
            time.sleep(wait)
        # До тук е въведена password или username/password в зависимост от нуждата
        # устройството трябва да върне промпт завършващ с > или # в зависимот от privilege level
            write_log_msg(" Expecting prompt...")
        exp = tty.expect(relist, 7)
        print "   ", exp
        if exp[0] == 3:
            # промпт е > т.е. privilege level 0. трябва да се въведе enable
            write_log_msg("entered non-privileged mode")
            tty.write("enable\n")
            write_log_msg("write : enable")
            time.sleep(wait)
            exp = tty.expect(relist, 1)
            print "   ", exp
            if exp[0] == 1:
                # очаква се enable password
                tty.write(crd['enable'] + '\n')
                write_log_msg("write : enable password : " + '*****')
                time.sleep(wait)
            else:
                write_log_msg("ERR: Unexpected responce from " + crd['ip'] + " after enable command.")
                tty.close()
                return enabled
            # enable паролата е въведена. Очакваме промпт #
            exp = tty.expect(relist, 2)
            print exp
            if exp[0] == 2:
                # промпт е # - има privilege level 15
                enabled = True
                write_log_msg("entered privileged mode")
            else:
                write_log_msg("ERR: Invalid enable password for " + crd['ip'])
                tty.close()
                return enabled
        elif exp[0] == 2:
            # промпт е # - има privilege level 15
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

        # Тук сме в privileged mode!
    except:
        write_log_msg("ERR: Failed telnet to " + crd['ip'])
        return enabled

    return enabled
# ------------------------------------------------------------------ #


def do_backup_running_config(hostname):
    # Изтегля конфигурацията при вече изградена telnet връзка и privileged mode
    # Използва командата show running-config
    write_log_msg("backing up the running config...")
    tty.write("terminal length 0\n")  # без тази команда няма да се изведе цялата конфигурация наведнъж
    time.sleep(0.5)
    tty.write("show run\n")
    re1 = re.compile("\r?\nend\r?\n")
    re_list = [re1]
    conf = tty.expect(re_list, 5)
    if conf[0] == 0:
        # Записваме конфигурацията във файл
        backup_file = open(hostname + "-confg", 'w')
        lines = conf[2].splitlines()
        for l in lines:
            if l.find("terminal length 0") != -1:
                continue
            if l.find("show run") != -1:
                continue
            if l.find("Building configuration") != -1:
                continue
            if l.find("Current configuration") != -1:
                continue
            backup_file.write(l + "\n")
        backup_file.close()
    else:
        write_log_msg("ERR: Failed creating backup for host " + hostname)
    return
# ------------------------------------------------------------------ #


def do_backup_vlan(hostname):
    # Изпраща команда show vlan и върнатия резултат го записва във файл hostname-vlan
    write_log_msg("backingup VLAN data...")
    tty.write("terminal length 0\n")  # без тази команда няма да се изведе цялата конфигурация наведнъж
    time.sleep(0.5)
    tty.write("show vlan\n")
    time.sleep(4)
    vlan_data = tty.read_very_eager()
    vlan_data_lines = vlan_data.splitlines()
    vlan_backup = open(hostname + "-vlan",'w')
    for l in vlan_data_lines:
        if l.find("terminal length 0") != -1:
            continue
        if l.find("show vlan") != -1:
            continue
        vlan_backup.write(l)
    vlan_backup.close()
    return
# ------------------------------------------------------------------ #

# изчистване на log.txt от старо съдържание
logtxt = open("log.txt", 'w')
logtxt.close()
write_log_msg("script was started")

# parse XML
tree = ET.parse("credentials.xml")
root = tree.getroot()

i = 0
credentials = {'ip': "None", 'username': 'None', 'password': 'None', 'enable': 'None', 'hostname': 'None', 'vlan': 'None'}

for child in root:
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

    print child.tag, i
    print credentials
    is_enabled = go_enabled(credentials)
    if is_enabled:
        write_log_msg("Succcessfuly enabled!")
        do_backup_running_config(credentials['hostname'])

        if credentials['vlan'] == 'yes':
            do_backup_vlan(credentials['hostname'])
            
        write_log_msg("Closing the connection.")
        tty.write("exit\n")
        time.sleep(2)
        tty.read_very_eager()
        tty.close()
    else:
        write_log_msg("Failed to enable!")

    print "\n---------------------------\n"
write_log_msg("script has finished")



