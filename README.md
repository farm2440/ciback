ciback = CIscoBACKup
This Python program downloads configuration backup from multiple Cisco IOS devices.

ciback.py - uses Telnet for transport. 
Credentials and IP addresses  are in single XML files

<<<<<<< HEAD
This Python script downloads configuration backup from multiple Cisco IOS devices
and a bash script is generated. This script performs git commit for those configurations
which were changed since the last run of ciback.
From credentials.xml the host names, IP addresses, passwords etc... are extracted sequentially
for each device and attempt for telnet session is made. If privileged mode is acquired the running
configuration is stored to file HOSTNAME-confg. If for some device in credentials.xml
yes is given, backup of vlan data is also stored to file HOSTNAME-vlan.
This data is device's response on show vlan command.
conf_changes.txt keeps data about last configuration changes date/time. It's used for tracking
changes and adding changed files in add_git.sh.

ciback-ssh.py - Does the same job as ciback.py using Paramiko for SSH transport
Tries to parse all XML files in currend folder for credentials and IP addresses.


Required input:
credentials.xml - this file must be in the same folder as ciback.py. ciback.py reads from it the IP addresses ,hostnames, credentials, etc. All IOS devices described in this xml file are polled secuentially. A telnet is established and the responce to "show running-config" command is saved to file HOSTNAME-config. If for some device in credentials.xml "yes" is given for vlan tag, backup of vlan data is also stored to file HOSTNAME-vlan. This data is device's response on show vlan command.
For ciback-ssh.py credentials for different devices can be stored in multiple XML files.

Generated output:
add_git.sh - This script when called commits to Git for those configurations which were changed since the last run of ciback.py.
conf_changes.txt - keeps information about date/time of the last configuration changes. It's used for tracking changes and adding files to add_git.sh.
log.txt - log of the events during ciback.py run. Information abot success of telnet session establishment or errors can be found here

=======
This Python program downloads configuration backup from multiple Cisco IOS devices.

Required input:
  - credentials.xml - this file must be in the same folder as ciback.py. ciback.py reads from it the IP addresses ,hostnames, credentials, etc. All IOS devices described in this xml file are polled secuentially. A telnet is established  and the responce to "show running-config" command is saved to file HOSTNAME-config. If for some device in credentials.xml  "yes" is given for vlan tag, backup of vlan data is also stored to file HOSTNAME-vlan. This data is device's response on show vlan command.
 
Generated output:
  - add_git.sh -  This script when called commits to  Git for those configurations which were changed since the last run of ciback.py.

  - conf_changes.txt - keeps information about date/time of the last configuration changes. It's used for tracking changes and adding files to add_git.sh.

  - log.txt - log of the events during ciback.py run. Information abot success of telnet session establishment or errors can be found here
>>>>>>> e9d0a2ff215f04c43de6acc7d1d621f91e755459
