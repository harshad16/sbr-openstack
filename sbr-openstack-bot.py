"""
SBR OpenStack Supporter/Datahub Bot.The SBR OpenStack Supppoter bot project is sponsered by Red Hat Inc.
It is an application for Red Hat SBR OpenStack Support Team.
The application serves as automation for the customer case ticket processing.

Author: Harshad Reddy Nalla
Team: Thoth
Department: AICoE
Company: Red Hat Inc.
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


from prometheus_client import CollectorRegistry, pushadd_to_gateway, Gauge

_LOGGER = logging.getLogger(__name__)
prometheus_registry = CollectorRegistry()


class SBR:
    """
    SBR OpenStack Supporter/Datahub Bot

    The SBR OpenStack Supppoter bot project is sponsered by Red Hat Inc.
    It is an application for Red Hat SBR OpenStack Support Team.
    The application serves as automation for the customer case ticket processing,
    it process the ticket by performing following actions:

    - Fetching relevant information (attachments,SOS Reports).
    - Extracting the SOS Report from the attachment based upon the SOS Report type of the compression.
    - Execute Citellus(SBR OpenStack Support Team Validation tool) on to the SOS Report.
    - Gather solutions for the failed plugins.
    - Publish the best of the solutions as a private comments on the case.
    """

    def __init__(self):
        self.ticket = os.getenv('TICKET')
        self.rh_username = os.getenv('RHUSERNAME')
        self.rhn_username = os.getenv('RHNUSERNAME')
        self.server = os.getenv('SERVER')
        self.job = os.getenv('JOBNAME')
        self.rh_pwd_dir = '/secret/rhpasswordfile'
        password_file = open(self.rh_pwd_dir, 'r')
        self.rh_password = password_file.read()
        self.rhn_pwd_dir = '/secret/rhnpasswordfile'
        password_file = open(self.rhn_pwd_dir, 'r')
        self.rhn_password = password_file.read()
        self.path = f'/cases/{self.ticket}/attachments'

        if 'redhat.com' in self.rh_username:
            self.user = re.search(r'[^@]+', self.rh_username).group(0)
        else:
            self.user = self.rh_username

        self.redhat_solutions = 'https://access.redhat.com/solutions'

    def get_ticket_config(self):
        """
        Gathers the hostname , port and ticket attachement directory details with respect to the server.
        """
        if not self.server:
            self.server = "collabrador"
            _LOGGER.info('Default server `collabrador` is selected for fetching ticket attachments')
        if self.server == "collabrador":
            remote_host = "s01.gss.hst.phx2.redhat.com"
            remote_port = "22"
            print("Provided Ticket number is: ", int(self.ticket))
            if int(self.ticket) > 1599999:
                ticket_split = '/'.join([self.ticket[i + 2: i + 3] for i in range(len(self.ticket) - 1)])
                print("ticket split is: ", ticket_split)
                remote_directory = f"/srv/cases/0{self.ticket[0:2]}/{ticket_split}attachments"
                print("remote_directory is: ", remote_directory)
            else:
                remote_directory = f"/srv/cases/0{self.ticket[0:2]}/{self.ticket[2:5]}/{self.ticket[5:8]}/attachments"
                print("remote_directory is: ", remote_directory)
            _LOGGER.info('Server `collabrador` is selected for fetching ticket attachments')
        elif self.server == "fubar":
            remote_host = "fubar.gsslab.rdu2.redhat.com"
            remote_port = "22"
            remote_directory = f'/fubar/{self.ticket}'
            _LOGGER.info('Server `fubar` is selected for fetching ticket attachments')
        else:
            raise Exception('Not know server is being accessed!')

        # create a storage for the ticket if not exists
        if not os.path.exists(f'/cases/{self.ticket}'):
            os.makedirs(f'/cases/{self.ticket}')

        return remote_host, remote_port, remote_directory

    def ssh_copy_attachments(self, remote_host, remote_port, remote_directory):
        """
        Copy the ticket attachments from the storage server to /cases/<ticket> directory.
        """
        try:
            print("Ticket attachment Directory: ", remote_directory)
            escape_known_host = f"-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
            scp_command = f"sshpass -f {self.rh_pwd_dir} scp {escape_known_host} -r -P {remote_port} {self.user}@{remote_host}:{remote_directory} /cases/{self.ticket}"
            scp_process = subprocess.run(scp_command.split(' '))
            if scp_process.returncode == 0:
                _LOGGER.info('Successfully fetched the attachments')
            elif scp_process.returncode == 1:
                metric_name = self.job + '-scp-error'
                metric_name = metric_name.replace('-', '_')
                job_comment_metric = Gauge(metric_name, 'unable to scp ticket attachments as the file is not found',
                                           registry=prometheus_registry)
                job_comment_metric.inc(1)
                _LOGGER.error('Unable to fetch attachments as file is not found')
            elif scp_process.returncode == 5:
                metric_name = self.job + '-scp-error'
                metric_name = metric_name.replace('-', '_')
                job_comment_metric = Gauge(metric_name,
                                           'unable to scp ticket attachments due to authentication failure',
                                           registry=prometheus_registry)
                job_comment_metric.inc(5)
                _LOGGER.error('Unable to fetch attachments due to authentication')
            else:
                _LOGGER.error(f'Unable to fetch attachments due to error code {scp_process.returncode}')
                raise Exception('scp failed!,Unable to fetch attachments.')
        except:
            metric_name = self.job + '-scp-error'
            metric_name = metric_name.replace('-', '_')
            job_comment_metric = Gauge(metric_name, 'unable to scp ticket attachments', registry=prometheus_registry)
            job_comment_metric.inc(2)
            _LOGGER.error('scp failed!, fetching attachments is not possible.')
            raise Exception('scp failed!, fetching attachments is not possible.')
        return True

    def get_all_sosreports(self):
        """
        Extract the SOS report based upon there compression type.
        """
        print('Extracting the compressed file!')
        sosreports = list()
        for sosreport in os.listdir(self.path):
            if sosreport.startswith("."):
                continue
            if tarfile.is_tarfile(f'{self.path}/{sosreport}'):
                print("sosreport is compressed as tar file")
                sosreport_tar_obj = tarfile.open(f'{self.path}/{sosreport}')
                sosreport_tar_obj.extractall(path=self.path)
                os.chmod(f'{self.path}/{sosreport_tar_obj.getnames()[0]}', 0o755)
                os.remove(f'{self.path}/{sosreport}')
                sosreports.append(sosreport_tar_obj.getnames()[0])
                _LOGGER.info('Extracted the tar compressed sosreport from attachments')
            elif zipfile.is_zipfile(f'{self.path}/{sosreport}'):
                print("sosreport is compressed as zip file")
                sosreport_zip_obj = zipfile.ZipFile(f'{self.path}/{sosreport}')
                sosreport_zip_obj.extractall(path=f'{self.path}')
                os.chmod(f'{self.path}/{sosreport_zip_obj.namelist()[0]}', 0o755)
                os.remove(f'{self.path}/{sosreport}')
                sosreports.append(sosreport_zip_obj.namelist()[0])
                _LOGGER.info('Extracted the zipped sosreport from attachments')
            else:
                print("failed sosreport extraction! compression type is not tar or zip!")
                _LOGGER.error('Failed sosreport extraction from attachments')
                metric_count = 0
                metric_name = self.job + '-sosreport-extract-' + str(metric_count)
                metric_count += 1
                metric_name = metric_name.replace('-', '_')
                job_comment_metric = Gauge(metric_name, 'unable to extract sosreport', registry=prometheus_registry)
                job_comment_metric.inc()
                raise Exception('Failed sosreport extraction from attachments')

        return sosreports

    def check_sosreports(self, directory):
        """
        Check if the directory contained in the attachment is sosreport.
        """
        if "soscleaner" in directory:
            return False

        if os.path.exists(f"{directory}/sos_commands") and os.path.exists(f"{directory}/hostname") and os.path.exists(
                f"{directory}/date"):
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
            metric_name = self.job + '-sosreport-error'
            metric_name = metric_name.replace('-', '_')
            job_comment_metric = Gauge(metric_name, 'unable to send sosreport to citellus',
                                       registry=prometheus_registry)
            job_comment_metric.inc()
            raise Exception('Unable to provide sosreport to Citellus for execution')

    def get_solutions(self, sosreport_dir):
        """
        Gather the solutions from the access.redhat/solutions.
        """
        f = open(f'{sosreport_dir}/citellus.json')
        report = json.load(f)

        hash_map = []
        solution_data = []
        solution = ''

        for hash_key, plugin in report['results'].items():
            if plugin.get('result').get('rc') == 20:
                if plugin.get('kb') and self.redhat_solutions in plugin.get('kb'):
                    kbase_id = re.search(r'\d+$', plugin.get('kb')).group(0)
                    if kbase_id not in hash_map:
                        hash_map.append(kbase_id)
                        url = 'https://api.access.redhat.com/rs/solutions/' + kbase_id
                        response = requests.get(url, auth=(self.rhn_username, self.rhn_password))
                        if response.status_code == 200:
                            xml = response.text
                            tree = ET.fromstring(xml)
                            try:
                                resolution = tree.find('{http://www.redhat.com/gss/strata}resolution')
                                solution = resolution.find('{http://www.redhat.com/gss/strata}text').text
                            except Exception as e:
                                _LOGGER.error('xml parsing of the solution failed!')
                                metric_name = self.job + '-solution-xml-parse-' + str(kbase_id)
                                metric_name = metric_name.replace('-', '_')
                                job_comment_metric = Gauge(metric_name, 'solution xml parsing failed',
                                                           registry=prometheus_registry)
                                job_comment_metric.inc()
                                pass
                            if solution:
                                plugin['result']['solution'] = solution
                        else:
                            _LOGGER.error('Request to solution api failed!')
                            metric_name = self.job + '-solution-request-' + str(kbase_id)
                            metric_name = metric_name.replace('-', '_')
                            job_comment_metric = Gauge(metric_name, 'solution request failed due to authentication',
                                                       registry=prometheus_registry)
                            job_comment_metric.inc()
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
        for ind, sol in enumerate(solution_data):
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
            if ind == 4:
                _LOGGER.info('Top 5 solutions are found for the failed plugins')
                break
        return comment, link

    def publish_comments(self, comment, link):
        """
        Publish the comment on the customer case.
        """
        comment_endpoint = f'https://api.access.redhat.com/rs/cases/{self.ticket}/comments'
        payload = {
            "label": "Solution by the bot",
            "text": comment,
            "uri": link,
            "draft": False,
            "caseNumber": str(self.ticket),
            "public": False
        }

        comment_response = requests.post(comment_endpoint, json=payload, auth=(self.rhn_username, self.rhn_password))
        if comment_response.status_code == 200 or comment_response.status_code == 201:
            _LOGGER.info('comment to customer cases was successfully published')
            return True
        else:
            _LOGGER.error('comment to customer cases was NOT successfully published')
            metric_name = self.job + '-publish-comment'
            metric_name = metric_name.replace('-', '_')
            job_comment_metric = Gauge(metric_name, 'Error of comment publish on customer case',
                                       registry=prometheus_registry)
            job_comment_metric.inc()
            return False

    def pushgateway(self, job_name):
        _PUSH_GATEWAY_HOST = os.getenv('PROMETHEUS_PUSHGATEWAY_HOST')
        _PUSH_GATEWAY_PORT = os.getenv('PROMETHEUS_PUSHGATEWAY_PORT')
        if _PUSH_GATEWAY_HOST and _PUSH_GATEWAY_PORT:
            try:
                push_gateway = f"{_PUSH_GATEWAY_HOST}:{_PUSH_GATEWAY_PORT}"
                _LOGGER.debug(f"Submitting metrics to Prometheus push gateway {push_gateway}")
                pushadd_to_gateway(push_gateway, job=job_name, registry=prometheus_registry)
            except Exception as e:
                _LOGGER.exception('An error occurred pushing the metrics: {}'.format(str(e)))

    def main(self):
        """ 
        Execute SBR OpenStack bot.
        """
        job_name = self.job + '-job-exec-time'
        job_name = job_name.replace('-', '_')
        job_metric_time = Gauge(job_name, 'Runtime of application job execution', registry=prometheus_registry)
        try:
            with job_metric_time.time():
                solutions = list()
                complete = False
                remote_host, remote_port, remote_dir = self.get_ticket_config()
                if remote_host and remote_port and remote_dir:
                    self.ssh_copy_attachments(remote_host, remote_port, remote_dir)
                    if os.path.isdir(self.path):
                        sosreports = self.get_all_sosreports()
                        for sosreport in sosreports:
                            execution_path = f"{self.path}/{sosreport}"
                            self.execute_citellus(execution_path)
                            solution_data = self.get_solutions(execution_path)
                            solutions.append(solution_data)
                            comment, link = self.generate_comments(solution_data)
                            print("Comment:", comment)
                            complete = True
                            # if comment:
                            #     complete = self.publish_comments(comment, link)

                if complete:
                    _LOGGER.info('Script successfully completed')
                else:
                    metric_name = self.job + '-application-failed'
                    metric_name = metric_name.replace('-', '_')
                    job_comment_metric = Gauge(metric_name, 'Script Unable to process the ticket',
                                               registry=prometheus_registry)
                    job_comment_metric.inc()
                    _LOGGER.info('Script Unable to process the ticket')
                    raise Exception('Script Unable to process the ticket')
        except Exception as e:
            print("Script Failed due to", e)
        self.pushgateway(self.job)


if __name__ == '__main__':
    sbr = SBR()
    sbr.main()
