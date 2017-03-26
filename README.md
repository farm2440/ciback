ciback = CIscoBACKup

This Python program downloads configuration backup from multiple Cisco IOS devices.

Required input:
  - credentials.xml - this file must be in the same folder as ciback.py. ciback.py reads from it the IP addresses ,hostnames, credentials, etc. All IOS devices described in this xml file are polled secuentially. A telnet is established  and the responce to "show running-config" command is saved to file HOSTNAME-config. If for some device in credentials.xml  "yes" is given for vlan tag, backup of vlan data is also stored to file HOSTNAME-vlan. This data is device's response on show vlan command.
 
Generated output:
  - add_git.sh -  This script when called commits to  Git for those configurations which were changed since the last run of ciback.py.

  - conf_changes.txt - keeps information about date/time of the last configuration changes. It's used for tracking changes and adding files to add_git.sh.

  - log.txt - log of the events during ciback.py run. Information abot success of telnet session establishment or errors can be found here
