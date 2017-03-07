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
            print "write : username : ", credentials['username']
            time.sleep(wait)
            exp = tty.expect(relist, 1)
            print "   ", exp
            if exp[0] != 1:
                # След въведено Username трябва да поиска парола. Ако не е така излизаа с грешка
                print "ERR: unexpected responce from ", credentials["ip"], " after Usrename entered."
                writeLogMsg("ERR: unexpected responce from " + credentials["ip"] + " after Usrename entered.")
                tty.close()
                return
            tty.write(credentials['password'] + '\n')
            print "write : password :",credentials['password']
            time.sleep(wait)
        elif exp[0] == 1:
            # идентификация по Password
            print("Only password required")
            tty.write(credentials['password'] + '\n')
            print "write : password :", credentials['password']
            time.sleep(wait)
        # До тук е въведена password или username/password в зависимост от нуждата
        # устройството трябва да върне промпт завършващ с > или # в зависимот от privilege level
        print " Expecting prompt..."
        exp = tty.expect(relist, 7)
        print "   ", exp
        if exp[0] == 3:
            # промпт е > т.е. privilege level 0. трябва да се въведе enable
            print "entered non-privileged mode"
            tty.write("enable\n")
            print "write : enable"
            time.sleep(wait)
            exp = tty.expect(relist, 1)
            print "   ", exp
            if exp[0] == 1:
                # очаква се enable password
                tty.write(credentials['enable'] + '\n')
                print "write : enable password :", credentials['enable']
                time.sleep(wait)
            else:
                print "ERR: Unexpected responce from ", credentials['ip'], " after enable command."
                writeLogMsg("ERR: Unexpected responce from " + credentials['ip'] + " after enable command.")
                tty.close()
                return
            # enable паролата е въведена. Очакваме промпт #
            exp = tty.expect(relist, 2)
            print exp
            if exp[0] == 2:
                # промпт е # няма privilege level 15
                print "entered privileged mode"
            else:
                print "ERR: Invalid enable password for ", credentials['ip']
                writeLogMsg("ERR: Invalid enable password for " + credentials['ip'])
                tty.close()
                return
        elif exp[0] == 2:
            # промпт е # няма privilege level 15
            print "entered privileged mode"
        elif exp[0] == 1 or exp[0] == 0:
            print "ERR: Invalid password or username for ", credentials['ip']
            writeLogMsg("ERR: Invalid password or username for " + credentials['ip'])
            tty.close()
            return
        else:
            print "ERR: unexpected responce from ", credentials["ip"], " after Password entered."
            writeLogMsg("ERR: unexpected responce from " + credentials["ip"] + " after Password entered.")
            tty.close()
            return

        # Тук сме в privileged mode!
        # TODO backup code!
        
        tty.write("exit\n")
        print "write : exit"
        time.sleep(wait)
        tty.close()
    except:
        print "ERR: Failed telnet to ", credentials['ip']
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
    backup_device(credentials)
    print "\n---------------------------\n"
writeLogMsg("script has finished")



