"""
SBR OpenStack Supporter/Datahub Bot
"""
import os
import re
import json

import subprocess

import tarfile
import zipfile

import requests
import logging
import xml.etree.ElementTree as ET
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


class SBR:
    """
    SBR OpenStack Supporter/Datahub Bot
    TODO: 
        1. Integrate Logging functionality
        2. Added Raise functionality where ever necessary 
    """
    def __init__(self):
        self.ticket = os.getenv('TICKET')
        self.username = os.getenv('USERNAME')
        self.server = os.getenv('SERVER')
        self.pwd_dir = '/secret/passwordfile'
        password_file = open(self.pwd_dir, 'r')
        self.password = password_file.read()
        self.path = f'/cases/{self.ticket}/attachments'
        
        if 'redhat.com' in self.username:
            self.user = re.search(r'[^@]+', self.username).group(0)
        else:
            self.user = self.username

        self.redhat_solutions = 'https://access.redhat.com/solutions'


    def get_ticket_config(self):
        """
        Gathers the hostname , port and ticket attachement directory details with respect to the server
        """
        if not self.server:
            self.server = "collabrador"
            _LOGGER.info('Default server collabrador is selected for fetching ticket attachments')
        if self.server == "collabrador":
            remote_host = "s01.gss.hst.phx2.redhat.com"
            remote_port = "22"
            remote_directory = f'/srv/cases/0{self.ticket[0:2]}/{self.ticket[2:5]}/{self.ticket[5:8]}/attachments'
            if int(self.ticket) > 1599999:
                ticket_split = '/'.join([self.ticket[i + 2: i + 3] for i in range(len(self.ticket) - 1)])
                remote_directory = f'/srv/cases/0{self.ticket[0:2]}/{ticket_split}attachments'
        elif self.server == "fubar":
            remote_host = "fubar.gsslab.rdu2.redhat.com"
            remote_port = "22"
            remote_directory = f'/fubar/{self.ticket}'

        # create a storage for the ticket if not exists
        if not os.path.exists(f'/cases/{self.ticket}'):
            os.makedirs(f'/cases/{self.ticket}')

        return remote_host, remote_port, remote_directory


    def ssh_copy_attachments(self, remote_host, remote_port, remote_directory):
        """
        Copy the ticket attachments from the storage server to /cases/<ticket> directory
        """
        try:
            escape_known_host = f'-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
            scp_command = f'sshpass -f {self.pwd_dir} scp {escape_known_host} -r -P {remote_port} {self.user}@{remote_host}:{remote_directory} /cases/{self.ticket}'
            scp_process = subprocess.check_call(scp_command.split(' '))
        except Exception as e:
            # Log and Raise
            _LOGGER.error('Bot was unable to fetch the ticket attachments from server')
            pass 
        return True


    def get_all_sosreports(self):
        """
        """
        sosreports = list()
        for sosreport in os.listdir(self.path):
            if sosreport.startswith("."):
                    continue
            if tarfile.is_tarfile(f'{self.path}/{sosreport}'):
                sosreport_tar_obj = tarfile.open(f'{self.path}/{sosreport}')
                sosreport_tar_obj.extractall(path=self.path)
                os.chmod(f'{self.path}/{sosreport_tar_obj.getnames()[0]}', 0o755)
                os.remove(f'{self.path}/{sosreport}')
                sosreports.append(sosreport_tar_obj.getnames()[0])
                _LOGGER.info('Extracted the tar compressed sosreport from attachments')
            elif zipfile.is_zipfile(f'{self.path}/{sosreport}'):
                sosreport_zip_obj = zipfile.ZipFile(f'{self.path}/{sosreport}')
                sosreport_zip_obj.extractall(path=f'{self.path}')
                os.chmod(f'{self.path}/{sosreport_tar_obj.getnames()[0]}', 0o755)
                os.remove(f'{self.path}/{sosreport}')
                sosreports.append(sosreport_tar_obj.getnames()[0])
                _LOGGER.info('Extracted the zipped sosreport from attachments')
            else:
                _LOGGER.error('Failed sosreport extraction from attachments')
                # Raise and Log
                return []

        return sosreports


    def check_sosreports(self, directory):
        """
        Check if the directory contained in the attachment is sosreport
        """
        if "soscleaner" in directory:
            return False

        if os.path.exists(f"{directory}/sos_commands") and os.path.exists(f"{directory}/hostname") and os.path.exists(f"{directory}/date"):
            return True
        
        return False


    def execute_citellus(self, sosreport_dir):
        """
        Run Citellus on the Customer Ticket sos-report
        """
        if self.check_sosreports(sosreport_dir):
            os.system(f'python3 citellus/citellus.py {sosreport_dir}')
            _LOGGER.info('Citellus execution on the sosreport is completed successfully')
            return True
        else: 
            _LOGGER.error('Unable to provide sosreport to Citellus for execution')
            # Raise and Log
            return False


    def get_solutions(self, sosreport_dir):
        """
        Gather the solutions from the access.redhat/solutions 
        """
        f = open(f'{sosreport_dir}/citellus.json')
        report = json.load(f)

        hash_map = []
        solution_data = []
        
        for hash_key, plugin in report['results'].items():
            if plugin.get('result').get('rc') == 20:
                if plugin.get('kb') and self.redhat_solutions in plugin.get('kb'):
                    kbase_id = re.search(r'\d+$', plugin.get('kb')).group(0)
                    if kbase_id not in hash_map:
                        hash_map.append(kbase_id)
                        url = 'https://api.access.redhat.com/rs/solutions/' + kbase_id
                        response = requests.get(url, auth=(self.username, self.password))
                        print(response.status_code)
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
                            # Raise and Log
                            pass
                solution_data.append(plugin)

        solution_data = sorted(solution_data, key=lambda val: val['priority'], reverse=True)
        return solution_data


    def generate_comments(self, solution_data):
        """
        Generate the top 5 critical comments for solving the failure.
        """
        comment = "HI,\n"
        link = ""
        for ind,sol in enumerate(solution_data):
            if 'solution' in sol.get('result'):
                comment += f"Error: {sol.get('description')} \n and {sol.get('result').get('err')}\n"
                comment += f"Solution: {sol.get('result').get('solution')}\n"
                comment += f"---------------------------------------------------------------------\n"
                link += sol.get('kb') + '\n'
            elif sol.get('kb'):
                comment += f"Error: {sol.get('description')}\n and {sol.get('result').get('err')}\n"
                comment += f"Solution: {sol.get('kb')}\n"
                comment += f"---------------------------------------------------------------------\n"
                link += sol.get('kb') + '\n'
            else:
                comment += f"\nError: {sol.get('description')}\n and {sol.get('result').get('err')}\n"
                comment += f"---------------------------------------------------------------------\n"   
            if ind == 3:
                break
        return comment, link


    def publish_comments(self, comment, link):
        """
        Publish the comment on the customer case.
        """
        time = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        comment_endpoint = f'https://api.access.redhat.com/rs/cases/{self.ticket}/comments'
        payload = {
            "label": "Solution by the bot",
            "text": comment,
            "uri": link,
            "draft": False,
            "caseNumber": str(self.ticket),
            "public": False
        }

        comment_response = requests.post(comment_endpoint, json=payload, auth=(self.username, self.password))
        print(comment_response.status_code)
        if comment_response.status_code == 200 or comment_response.status_code == 201:
            return True
        else:
            # Log and Raise
            return False

    
    def main(self):
        """ 
        Execute SBR OpenStack bot.
        """
        solutions=list()
        complete = False
        remote_host, remote_port, remote_dir = self.get_ticket_config()
        if remote_host and remote_port and remote_dir:
            self.ssh_copy_attachments(remote_host, remote_port, remote_dir)
            if os.path.isdir(self.path):
                sosreports = self.get_all_sosreports()
                for sosreport in sosreports:
                    execution_path=f'{self.path}/{sosreport}' 
                    self.execute_citellus(execution_path)
                    solution_data = self.get_solutions(execution_path)
                    solutions.append(solution_data)
                    comment,link = self.generate_comments(solution_data)
                    if comment:
                        complete=self.publish_comments(comment,link)

        if complete:
            print('Script successfully completed')
        else:
            print('Script Unable to process the ticket')

        _LOGGER.info('Bot has completed the process')

if __name__ == '__main__':
    sbr = SBR()
    sbr.main()
