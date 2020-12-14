# Meraki templates-migration

## PREREQUISITES
Run in Python 3

Install requests module, \
pip install -r requirements.txt

## DESCRIPTION
This script finds all networks matching a network tag (configured on the Organization > Overview page's table), and binds those networks to the target template (by name). The network's current VLANs for unique subnets will be reconfigured after binding to the target template, since binding to a template regenerates these unique subnets. Also, if the network is currently bound to a different template, it will be unbound from that current template first.
 \
Optionally, auto-bind the network's switches to profiles, as specified in the API call: \
[dashboard.meraki.com/api_docs#bind-a-network-to-a-template](https://dashboard.meraki.com/api_docs#bind-a-network-to-a-template)
 \
Here's a link on how to get Organization ID: \
https://developer.cisco.com/meraki/meraki-platform/#step-2-get-the-organization-id 


## New device type fix 
New section added to fix new device type issues. Additional question will prompt user to add new device type into network.\
Answer "y" to the question 
```
'Do you wish to add a new network type to ' + net_name + '? (Y/N)'
```
## Flow diagram

![Alt text](Flow_diagram.jpg?raw=true "Flow diagram")

## USAGE 
python migrate.py -k <api_key> -o <org_id> -t <target_template_name> -n <network_tag> [-s <auto_bind>]
If the target template's name has spaces, include quotes around it.

### New device type fix
1. Answer "y" to the question 
```
'Do you wish to add a new network type to all networks? (Y/N)'
```
2. Provide a valid name for the temporary network -- there can't be existing network with same name. Same name will be reused for subsequent operations on all tagged networks (if user chose to do so)
```
'Please enter a name for the new temporary network, same name will be reused for subsequent operations: '
```
3. Choose a network type for the new network
```
Please choose type of the a new network
1) wireless
2) appliance
3) switch
4) systemsManager
5) camera
6) cellularGateway
```

## Debug
if need to debug please comment the following lines
```
print_console=False,
suppress_logging=True
```

