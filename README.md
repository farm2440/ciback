ciback = CIscoBACKup

This Python script downloads configuration backup from multiple Cisco IOS devices
and a bash script is generated. This script performs git commit for those configurations
which were changed since the last run of ciback.
From credentials.xml the host names, IP addresses, passwords etc... are extracted sequentially
for each device and attempt for telnet session is made. If privileged mode is acquired the running
configuration is stored to file -confg. If for some device in credentials.xml
yes is given, backup of vlan data is also stored to file -vlan.
This data is device's response on show vlan command.
conf_changes.txt keeps data about last configuration changes date/time. It's used for tracking
changes and adding changed files in add_git.sh.
