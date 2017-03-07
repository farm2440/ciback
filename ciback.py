#!/usr/bin/python
# -*- coding: UTF-8 -*-

# скрипт за извличане архив на конфигурациите на Cisco устройства
# Author: Swilen Stavrev
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

# ------------------------------------------------------------------ #
def writeLogMsg(msg):
    # Записва във log.txt диагностично съобщение а също дата/час на записа.
    log = open("log.txt", 'a+')
    timeStamp = time.strftime("[%d.%m.%Y %H:%M:%S]  ")
    log.write(timeStamp + msg + "\n")
    log.close()
    return
# ------------------------------------------------------------------ #
def backup_device(crd):
    # Прави архив на конфигурацията
    writeLogMsg("try backup for device with IP " + credentials['ip'] + "...")
    wait = 0.5

    # Прави се login като се предвиждат вариантите за влизане с username+password или само с password
    # проверява се нивото на достъп privilege level и ако трябва се праща enable
    re1 = re.compile("Username: ")
    re2 = re.compile("Password: ")
    re3 = re.compile("\n.+#$")  # privilege level 15
    re4 = re.compile("\n.+>$")  # privilege level 0
    relist = [re1, re2, re3, re4]

    try:
        tty = telnetlib.Telnet(credentials['ip'],23,5)
        exp = tty.expect(relist, 5)  # expect връща кортеж
        print exp
        print "exp[0]=", exp[0]
        print "exp[1]=", exp[1]
        print "exp[2]=", exp[2]
        if exp[0] == -1:
            # няма открит reg exp
            print "ERR: unexpected initial responce from ", credentials["ip"]
            writeLogMsg("ERR: unexpected responce from " + credentials["ip"])
            tty.close()
            return
        elif exp[0] == 0:
            # идентификация по Username & Password
            print("Username and Password required")
            tty.write(credentials['username'] + '\n')
            time.sleep(wait)
            exp = tty.expect(relist, 1)
            print "   ", exp
            print "   exp[0]=", exp[0]
            print "   exp[1]=", exp[1]
            print "   exp[2]=", exp[2]
            exp = tty.expect(relist, 1)
            if exp[0] != 1:
                # След въведено Username трябва да поиска парола. Ако не е така излизаа с грешка
                print "ERR: unexpected responce from ", credentials["ip"], " after Usrename entered."
                writeLogMsg("ERR: unexpected responce from " + credentials["ip"] + " after Usrename entered.")
                tty.close()
                return
            tty.write(credentials['password'] + '\n')
            time.sleep(wait)
        elif exp[0] == 1:
            # идентификация по Password
            print("Only password required")
            tty.write(credentials['password'] + '\n')
            time.sleep(wait)
        # До тук е въведена password или username/password в зависимост от нуждата
        # устройството трябва да върне промпт завършващ с > или # в зависимот от privilege level

        print " Expecting prompt..."
        exp = tty.expect(relist, 1)
        print "   ", exp
        print "   exp[0]=", exp[0]
        print "   exp[1]=", exp[1]
        print "   exp[2]=", exp[2]
        tty.write("exit\n")
        time.sleep(wait)
        tty.close()
    except:
        writeLogMsg("ERR: Failed telnet to " + credentials['ip'])
        return

    writeLogMsg("backup done")
    return
#------------------------------------------------------------------#

writeLogMsg("script was started")
tftpSrvIP = "10.0.52.1"  # IP адрес на TFTP сървъра

# parse XML
tree = ET.parse("credentials.xml")
root = tree.getroot()

i = 0
credentials = {'ip':"None", 'username':'None', 'password':'None', 'enable':'None' }

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

    print child.tag, i
    print credentials
    print "\n"
    backup_device(credentials)
writeLogMsg("script has finished")



