#!/usr/bin/python3

'''
=== PREREQUISITES ===
Run in Python 3

Install requests module, via macOS terminal:
Python 3 > pip3 install requests

Install Meraki module:
Python 3 > pip3 install meraki

=== DESCRIPTION ===
This script finds all networks matching a network tag (configured on the Organization > Overview page's table), and binds those networks to the target template (by name). The network's current VLANs for unique subnets will be reconfigured after binding to the target template, since binding to a template regenerates these unique subnets. Also, if the network is currently bound to a different template, it will be unbound from that current template first.
Optionally, auto-bind the network's switches to profiles, as specified in the API call: https://dashboard.meraki.com/api_docs#bind-a-network-to-a-template

=== USAGE ===
python migrate.py -k <api_key> -o <org_id> -t <target_template_name> -n <network_tag> [-s <auto_bind>]
If the target template's name has spaces, include quotes around it.

'''


import getopt
import json
import requests
import sys
from datetime import datetime
import meraki


# Prints a line of text that is meant for the user to read
def printusertext(p_message):
    print('# %s' % p_message)

# Prints help text
def printhelp():
    printusertext('This script finds all networks matching a network tag (configured on the')
    printusertext('Organization > Overview page\'s table), and binds those networks to the')
    printusertext('target template (by name). The network\'s current VLANs for unique subnets')
    printusertext('will be reconfigured after binding to the target template, since binding to')
    printusertext('a template regenerates these unique subnets. Also, if the network is')
    printusertext('currently bound to a different template, it will be unbound from that')
    printusertext('current template first.')
    printusertext('Optionally, auto-bind the network\'s switches to profiles, as specified in the')
    printusertext('API call: https://dashboard.meraki.com/api_docs#bind-a-network-to-a-template')
    printusertext('')
    printusertext('Usage:')
    printusertext('python migrate.py -k <api_key> -o <org_id> -t <target_template_name>')
    printusertext('\t-n <network_tag> [-s <auto_bind>]')
    printusertext('If the target template\'s name has spaces, include quotes around it.')


def main(argv):
    # Set default values for command line arguments
    api_key = org_id = arg_template = arg_tag = arg_switch = 'null'

    # Get command line arguments
    try:
        opts, args = getopt.getopt(argv, 'hk:o:t:n:s:')
    except getopt.GetoptError:
        printhelp()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            printhelp()
            sys.exit()
        elif opt == '-k':
            api_key = arg
        elif opt == '-o':
            org_id = arg
        elif opt == '-t':
            arg_template = arg
        elif opt == '-n':
            arg_tag = arg
        elif opt == '-s':
            arg_switch = arg

    # Check if all parameters are required parameters have been given
    if api_key == 'null' or org_id == 'null' or arg_template == 'null' or arg_tag == 'null':
        printhelp()
        sys.exit(2)
    '''if arg_switch not in ('null', 'True', 'true', 'False', 'false'):
        printhelp()
        sys.exit(2)'''

    # Instantiate a Meraki dashboard API session
    dashboard = meraki.DashboardAPI(
        api_key,
        output_log=False,
        print_console=False,
        suppress_logging=True
        # log_file_prefix=os.path.basename(__file__)[:-3],
        # log_path='',
        # print_console=False
    )

    # Find all networks matching input tag
    networks = dashboard.organizations.getOrganizationNetworks(org_id)
    tagged_networks = [network for network in networks if network['tags'] is not None and arg_tag in network['tags']]

    # Find all templates
    templates = dashboard.organizations.getOrganizationConfigTemplates(org_id)
    template_ids = [template['id'] for template in templates]
    template_names = [template['name'] for template in templates]
    target_template_id = template_ids[template_names.index(arg_template)]

    # Tally up number of networks that are either unbound or currently bound to other templates
    unbound_count = 0
    for network in tagged_networks:
        if 'configTemplateId' in network:
            index = template_ids.index(network['configTemplateId'])
            if 'count' in templates[index]:
                templates[index]['count'] += 1
            else:
                templates[index]['count'] = 1
        else:
            unbound_count += 1

    # Confirm with user number of networks to be updated
    print('Found a grand total of {0} networks with the tag {1}:'.format(len(tagged_networks), arg_tag))
    if unbound_count > 0:
        print('{0} networks are currently unbound, not bound to any template'.format(unbound_count))
    for template in templates:
        if 'count' in template and template['count'] > 0:
            print('{0} networks are currently bound to template {1}'.format(template['count'], template['name']))

    ###########################################################
    #     New device type issue fix part 1
    ###########################################################
    
    ### New device type issue - Ask user input for batch process
    temp_network_name = ''
    add_network_type = False
    inputValid = False
    bind_template = False
    print("### New Device Type Issue Fix ###")
    reply = input('Do you wish to add a new network type to all ' + str(len(tagged_networks)) + ' networks? (Y/N)' ).lower()
    while reply[0] not in {"y", "n"}:
        reply = input('Please answer Y/N only: ').lower()
    if reply[0] == 'y':
        add_network_type = True
        while not inputValid:
            temp_network_name = input('Please enter a name for the new temporary network, same name will be reused for subsequent operations: ')
            inputValid = True
            for network in networks:
                if network['name'].lower() == temp_network_name.lower():
                    print ("Network already exists...Please try again")
                    inputValid = False
        validtypes = ['wireless', 'appliance', 'switch', 'systemsManager', 'camera', 'cellularGateway']
        index = 0
        print ('Please choose type of the a new network, this will be added to all ' + str(len(tagged_networks)) + ' networks: ')
        for ntype in validtypes:
            index = index + 1
            print(str(index) + ') ' + ntype)
        inputValid = False
        while not inputValid:
            inputRaw = input('option' + ': ')
            inputNo = int(inputRaw) - 1
            if inputNo > -1 and inputNo < len(validtypes):
                net_type = validtypes[inputNo]
                print('Selected option: ' + net_type)
                inputValid = True
                net_type_array = [net_type]
                break
            else:
                print('Please select a valid option number')

    ###########################################################
    #     End of New device type issue fix part 1
    ###########################################################

    # Update and bind networks to template
    for network in tagged_networks:
        net_id = network['id']
        net_name = network['name']
        original_net_name = net_name
        old_vlans = dashboard.appliance.getNetworkApplianceVlans(net_id)
        old_vlan_ids = [vlan['id'] for vlan in old_vlans]
        if 'configTemplateId' in network:
            template_name = template_names[template_ids.index(network['configTemplateId'])]
            print('Unbinding network {0} from current template {1}'.format(net_name, template_name))
            dashboard.networks.unbindNetwork(net_id)
            
            ###########################################################
            #     New device type issue fix part 2
            ###########################################################
            if add_network_type:
                print("Creating network " + temp_network_name + ' and network type is ' + net_type + ' ...')
                
                ## Adding new network
                try:
                    response = dashboard.organizations.createOrganizationNetwork(org_id, temp_network_name, net_type_array)
                except meraki.APIError as e:
                    print(f'Meraki API error: {e}')
                    print(f'status code = {e.status}')
                    print(f'reason = {e.reason}')
                    print(f'error = {e.message}')
                    continue
                except Exception as e:
                    print(f'some other error: {e}')
                    continue
                else:   
                    net_ids = []
                    net_ids.append(response['id'])
                
                    ## Split and bind network with additional component
                    
                    split_networks = dashboard.networks.splitNetwork(net_id)
                    for split_network in split_networks["resultingNetworks"]:
                        net_ids.append(split_network['id'])
                    response = dashboard.organizations.combineOrganizationNetworks(org_id, original_net_name, net_ids)
                    net_id = response["resultingNetwork"]['id']

        if not bind_template:
            continue_run = input('Continue to update by binding all {0} networks to the {1} template? (Y/N) '.format(len(tagged_networks), arg_template))
            if continue_run[0] == 'n':
                quit()
            else:
                bind_template = True
                print('Binding network {0} to target template {1}'.format(net_name, arg_template))
                if arg_switch in ('True', 'true'):
                    dashboard.networks.bindNetwork(net_id, target_template_id, autoBind=True)
                else:
                    dashboard.networks.bindNetwork(net_id, target_template_id, autoBind=False)
                new_vlans = dashboard.appliance.getNetworkApplianceVlans(net_id)
                for new_vlan in new_vlans:
                    vlan_id = new_vlan['id']
                    old_vlan = old_vlans[old_vlan_ids.index(vlan_id)]
                    if new_vlan['subnet'] != old_vlan['subnet'] or new_vlan['applianceIp'] != old_vlan['applianceIp']:
                        dashboard.appliance.updateNetworkApplianceVlan(net_id, vlan_id, subnet=old_vlan['subnet'], applianceIp=old_vlan['applianceIp'])
        ###########################################################
        #     End of New device type issue fix part 2
        ###########################################################

if __name__ == '__main__':
    startTime = datetime.now()
    print('Starting script at: %s' % startTime)
    print('Arguments entered: %s' % sys.argv[1:])
    main(sys.argv[1:])
    print('Ending script at: %s' % datetime.now())
    print('Total run time: %s' % (datetime.now() - startTime))
