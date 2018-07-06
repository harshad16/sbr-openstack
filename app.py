import os
import re
import json
import requests
import subprocess
import delegator
import xml.etree.ElementTree as ET
from datetime import datetime


ticket = os.getenv('TICKET')
username = os.getenv('USERNAME')
if 'redhat.com' in username:
    user = re.search(r'[^@]+', username).group(0)
else:
    user = username

# open the password file
password_file = open('/secret/passwordfile', 'r')
password = password_file.read()

remote_directory = '/srv/cases/0' + ticket[0:2] + '/' + ticket[2:5] + '/' + ticket[5:8] + '/attachments'
if int(ticket) > 1599999:
    remote_directory = '/srv/cases/0' + ticket[0:2] + '/' + '/'.join(
        [ticket[i + 2:i + 3] for i in range(len(ticket) - 1)]) + 'attachments'

try:
    os.makedirs('/cases/' + ticket)
except IOError as e:
    print(e)

scp_command = 'sshpass -p ' + password + ' scp -o StrictHostKeyChecking=no -r ' + user + '@s01.gss.hst.phx2.redhat.com:' + remote_directory + ' cases/' + ticket
# c = delegator.run(scp_command)
# print(c.out)
scp_process = subprocess.check_call(scp_command.split(' '))
print('process completed')


print('check if folder is created')
for fold in os.listdir('/cases/'):
    print(fold)

print('files in ticket folder')
for fold in os.listdir('/cases/' + ticket):
    print('inside dir')
    if os.path.isdir('/cases/' + ticket +'/'+ fold):
        for fil in os.listdir('/cases/' + ticket+'/'+ fold):
            print(fil)
    print(fold)
# Run Citellus on the Customer Ticket sos-report
# if os.path.isdir('/cases/' + ticket + '/attachments'):
os.system('python3 citellus/citellus.py /cases/' + ticket + '/attachments')

# Read the json result file to parse.
f = open('/cases/' + ticket + '/attachments/citellus.json')
report = json.load(f)

hash_map = []
solution_data = []
api_endpoint = "https://api.access.redhat.com/rs/solutions/"

for hash_key, plugin in report['results'].items():
    if plugin.get('result').get('rc') == 20:
        if plugin.get('kb') and 'https://access.redhat.com/solutions' in plugin.get('kb'):
            kbase_id = re.search(r'\d+$', plugin.get('kb')).group(0)
            if kbase_id not in hash_map:
                hash_map.append(kbase_id)
                url = api_endpoint + kbase_id
                print(url, username, password)
                response = requests.get(url, auth=(username, password))
                if response.status_code == 200:
                    xml = response.text
                    tree = ET.fromstring(xml)
                    try:
                        resolution = tree.find('{http://www.redhat.com/gss/strata}resolution')
                        solution = resolution.find('{http://www.redhat.com/gss/strata}text').text
                    except:
                        pass
                    if solution:
                        plugin['result']['solution'] = solution
                else:
                    print(response.status_code,'\n',response.text)
        solution_data.append(plugin)

# if solution_data:
solution_data = sorted(solution_data, key=lambda val: val['priority'], reverse=True)

comment = "HI,\n"
link = ""
for sol in solution_data:
    if 'solution' in sol.get('result'):
        comment += "Problem looks to be: " + sol.get('description') + "\n" + "and " + sol.get('result').get('err')
        comment += "\nMay be this can help: " + sol.get('result').get('solution') + "\n"
        link = sol.get('kb')
    elif sol.get('kb'):
        comment += "Problem looks to be: " + sol.get('description') + "\n" + "and " + sol.get('result').get('err')
        comment += "\nMay be this can help: " + sol.get('kb') + "\n"
        link = sol.get('kb')
    else:
        comment += "\nProblem looks to be: " + sol.get('description') + "\n" + "and " + sol.get('result').get(
            'err') + "\n"
    break

time = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
comment_endpoint = 'https://api.access.redhat.com/rs/cases/' + str(ticket) + '/comments'
payload = {
    "label": "Solution by the bot",
    "text": comment,
    "uri": link,
    "draft": False,
    "caseNumber": str(ticket),
    "public": False
}
    # comment_response = requests.post(comment_endpoint, json=payload, auth=(username, password))
print('done')
