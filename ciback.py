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


def writeLogMsg(msg):
    # Записва във log.txt диагностично съобщение а също дата/час на записа.
    log = open("log.txt", 'a+')
    timeStamp = time.strftime("[%d.%m.%Y %H:%M:%S]  ")
    log.write(timeStamp + msg + "\n")
    log.close()
    return
# ------------------------------------------------------------------ #


def go_enabled(crd):
    # получава речник crd в които са IP адрес, потребителско име и пароли за устройството
    # опитва се да установи telnet сесия и да стигне привилегирован режим.
    # връща флаг enabled който е True ако функцията е успяла да стигне до привилегирован
    # режим и да получи промпт #.  Ако не устее върнатия enabled=False

    writeLogMsg("try backup for device with IP " + crd['ip'] + "...")
    wait = 0.5
    enabled = False

    # Прави се login като се предвиждат вариантите за влизане с username+password или само с password
    # проверява се нивото на достъп privilege level и ако трябва се праща enable
    re1 = re.compile("Username: ")
    re2 = re.compile("Password: ")
    re3 = re.compile("\n.+#$")  # privilege level 15
    re4 = re.compile("\n.+>$")  # privilege level 0
    relist = [re1, re2, re3, re4] # списък с regular expression за проверка на връщаните от Cisco низове

    try:
        tty.open(crd['ip'],23,5)
        #tty = telnetlib.Telnet(crd['ip'],23,5)
        exp = tty.expect(relist, 5)  # expect връща кортеж. Първия елемент е индекс на RegExp за който има match.
                                     # Ако няма, стойността му е -1. Третия елемент е приетия низ.
        print exp
        if exp[0] == -1:
            # няма открит reg exp
            print "ERR: unexpected initial responce from ", crd["ip"]
            writeLogMsg("ERR: unexpected responce from " + crd["ip"])
            tty.close()
            return enabled
        elif exp[0] == 0:
            # идентификация по Username & Password
            print("Username and Password required")
            tty.write(crd['username'] + '\n')
            print "write : username : ", crd['username']
            time.sleep(wait)
            exp = tty.expect(relist, 1)
            print "   ", exp
            if exp[0] != 1:
                # След въведено Username трябва да поиска парола. Ако не е така излизаа с грешка
                print "ERR: unexpected responce from ", crd["ip"], " after Usrename entered."
                writeLogMsg("ERR: unexpected responce from " + crd["ip"] + " after Usrename entered.")
                tty.close()
                return enabled
            tty.write(crd['password'] + '\n')
            print "write : password :",crd['password']
            time.sleep(wait)
        elif exp[0] == 1:
            # идентификация по Password
            print("Only password required")
            tty.write(crd['password'] + '\n')
            print "write : password :", crd['password']
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
                tty.write(crd['enable'] + '\n')
                print "write : enable password :", crd['enable']
                time.sleep(wait)
            else:
                print "ERR: Unexpected responce from ", crd['ip'], " after enable command."
                writeLogMsg("ERR: Unexpected responce from " + crd['ip'] + " after enable command.")
                tty.close()
                return enabled
            # enable паролата е въведена. Очакваме промпт #
            exp = tty.expect(relist, 2)
            print exp
            if exp[0] == 2:
                # промпт е # - има privilege level 15
                enabled = True
                print "entered privileged mode"
            else:
                print "ERR: Invalid enable password for ", crd['ip']
                writeLogMsg("ERR: Invalid enable password for " + crd['ip'])
                tty.close()
                return enabled
        elif exp[0] == 2:
            # промпт е # - има privilege level 15
            enabled = True
            print "entered privileged mode"
        elif exp[0] == 1 or exp[0] == 0:
            print "ERR: Invalid password or username for ", crd['ip']
            writeLogMsg("ERR: Invalid password or username for " + crd['ip'])
            tty.close()
            return enabled
        else:
            print "ERR: unexpected responce from ", crd["ip"], " after Password entered."
            writeLogMsg("ERR: unexpected responce from " + crd["ip"] + " after Password entered.")
            tty.close()
            return enabled

        # Тук сме в privileged mode!
        # TODO backup code!

        # tty.write("exit\n")
        # print "write : exit"
        # time.sleep(wait)
        # tty.close()
    except:
        print "ERR: Failed telnet to ", crd['ip']
        writeLogMsg("ERR: Failed telnet to " + crd['ip'])
        return enabled

    writeLogMsg("backup done")
    return enabled
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
    enabled = go_enabled(credentials)
    if enabled :
        print "Succcessfuly enabled! Closing the connection..."

        # за проба
        tty.write("show version\n")
        time.sleep(5)
        ver = tty.read_very_eager()
        print "show version : ", ver

        tty.write("exit\n")
        time.sleep(0.5)
        tty.close()
    else :
        print "Failed to enable!"


    print "\n---------------------------\n"
writeLogMsg("script has finished")



