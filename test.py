"""
Pass a list of Ticket to check the sbr-openstack-bot. 
List of ticket are to be in: filename.txt
"""
import os
import string
import time
import random
import requests
import urllib3


class SBRTest(object):
    def __init__(self):
        self.url = ''
        self.token = ''
        self.namespace = ''
        self.username = ''
        self.server = 'collabrador'
        self.password = ''
        self.headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(self.token),
                        'Accept': 'application/json', 'Connection': 'close'}

    def create_secret_name(self):
        return 'test-{}'.format(''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))

    def secret_template(self, secret_name, ticket):
        secret = {
            "kind": "Secret",
            "apiVersion": "v1",
            "metadata": {
                "name": secret_name
            },
            "type": "opaque",
            "stringData": {
                "ticket": ticket,
                "server": self.server,
                "rhnusername": self.username,
                "rhnpassword": self.password,
                "rhusername": self.username,
                "rhpassword": self.password
            }
        }
        return secret

    def get_secret(self, secret_name):
        secret_get_endpoint = '{}/api/v1/namespaces/{}/secrets/{}'.format(self.url, self.namespace, secret_name)
        secret_get_response = requests.get(secret_get_endpoint, headers=self.headers, verify=False)
        print("Status code of secret GET request: ", secret_get_response.status_code)
        if secret_get_response.status_code == 200:
            return True
        else:
            print("Error in secret GET request: ", secret_get_response.text)
            return False

    def create_secret(self, secret):
        secret_endpoint = '{}/api/v1/namespaces/{}/secrets'.format(self.url, self.namespace)
        secret_response = requests.post(secret_endpoint, json=secret, headers=self.headers, verify=False)
        print("Status code of secret POST request: ", secret_response.status_code)
        if secret_response.status_code == 201:
            return True
        else:
            print("Error in secret POST request: ", secret_response.text)
            return False

    def create_job_name(self):
        return 'test-job-{}'.format(''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))

    def job_template(self, job_name, secret_name):
        payload = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "labels": {
                    "app": "sbr"
                },
                "namespace": self.namespace
            },
            "spec": {
                "completions": 1,
                "activeDeadlineSeconds": 1800,
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "image": "sbr-job",
                                "name": job_name,
                                "volumeMounts": [
                                    {
                                        "name": "password",
                                        "mountPath": "/secret"
                                    }
                                ],
                                "env": [
                                    {
                                        "name": "JOBNAME",
                                        "value": job_name
                                    },
                                    {
                                        "name": "PROMETHEUS_PUSHGATEWAY_HOST",
                                        "value": "pushgateway-aicoe.cloud.paas.upshift.redhat.com"
                                    },
                                    {
                                        "name": "PROMETHEUS_PUSHGATEWAY_PORT",
                                        "value": "80"
                                    },
                                    {
                                        "name": "RHUSERNAME",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "key": "rhusername",
                                                "name": secret_name
                                            }
                                        }
                                    },
                                    {
                                        "name": "RHNUSERNAME",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "key": "rhnusername",
                                                "name": secret_name
                                            }
                                        }
                                    },
                                    {
                                        "name": "TICKET",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "key": "ticket",
                                                "name": secret_name
                                            }
                                        }
                                    },
                                    {
                                        "name": "SERVER",
                                        "valueFrom": {
                                            "secretKeyRef": {
                                                "key": "server",
                                                "name": secret_name
                                            }
                                        }
                                    }
                                ],
                                "resources": {
                                    "requests": {
                                        "memory": "2Gi",
                                        "cpu": "1"
                                    },
                                    "limits": {
                                        "memory": "2Gi",
                                        "cpu": "1"
                                    }
                                }
                            }
                        ],
                        "volumes": [
                            {
                                "name": "password",
                                "secret": {
                                    "secretName": secret_name,
                                    "items": [
                                        {
                                            "key": "rhnpassword",
                                            "path": "rhnpasswordfile",
                                            "mode": 384
                                        },
                                        {
                                            "key": "rhpassword",
                                            "path": "rhpasswordfile",
                                            "mode": 384
                                        }
                                    ]
                                }
                            }
                        ],
                        "restartPolicy": "Never"
                    }
                }
            }
        }
        return payload

    def get_job(self, job_name):
        job_get_endpoint = '{}/apis/batch/v1/namespaces/{}/jobs/{}'.format(self.url, self.namespace, job_name)
        job_get_response = requests.get(job_get_endpoint, headers=self.headers, verify=False)
        print("Status code of job GET requests: ", job_get_response.status_code)
        if job_get_response.status_code == 201:
            return True
        else:
            print("Error in job GET requets: ", job_get_response.text)
            return False

    def create_job(self, job):
        job_endpoint = '{}/apis/batch/v1/namespaces/{}/jobs'.format(self.url, self.namespace)
        job_response = requests.post(job_endpoint, json=job, headers=self.headers, verify=False)
        print("Status code of job POST requests: ", job_response.status_code)
        if job_response.status_code == 201:
            return True
        else:
            print("Error in job POST requets: ", job_response.text)
            return False

    def get_usable_gi_quota(self, quota_val):
        max_usable_quota = int(quota_val.strip("Gi")) - 2
        return max_usable_quota

    def get_usable_mi_quota(self, quota_val):
        max_usable_quota = (int(quota_val.strip("Gi")) - 2) * 1000
        return max_usable_quota

    def get_resource_quota(self, quota_name):
        resource_quota_endpoint = '{}/api/v1/namespaces/{}/resourcequotas/{}'.format(self.url, self.namespace,
                                                                                     quota_name)
        resource_quota_response = requests.get(resource_quota_endpoint, headers=self.headers, verify=False)
        print("Status code for resource quota GET request: ", resource_quota_response.status_code)
        if resource_quota_response.status_code == 200:
            print("Resource Quota: ", resource_quota_response.json())
            if 'status' in resource_quota_response.json() and resource_quota_response.json().get('status'):
                quota = resource_quota_response.json().get('status')
                if 'Gi' in quota['used'].get("limits.memory", "") and int(quota['used'].get(
                        "limits.memory").strip("Gi")) > self.get_usable_gi_quota(quota['hard'].get("limits.memory")):
                    print('gi')
                    return True
                if 'Mi' in quota['used'].get("limits.memory", "") and int(quota['used'].get(
                        "limits.memory").strip("Mi")) > self.get_usable_mi_quota(quota['hard'].get("limits.memory")):
                    print('mi')
                    return True
                if 'm' in quota['used'].get("limits.cpu", "") and int(quota['used'].get("limits.cpu").strip("m")) > (int(quota['hard'].get("limits.cpu")) - 1) * 1000:
                    print('m')
                    return True
                if 'm' not in quota['used'].get("limits.cpu", "") and int(quota['used'].get("limits.cpu")) > (int(quota['hard'].get("limits.cpu")) - 1):
                    print('n')
                    return True
                return False
            else:
                print("Error for resource quota status request: ", resource_quota_response.text)
                return False
        else:
            print("Error for resource quota GET request: ", resource_quota_response.text)
            return False

    def main(self):
        if not self.url or not self.namespace or not self.token:
            raise Exception("SBR Test can't start! OCP credentials are not provided!")
        tickets = open('filename.txt').read()
        tickets = tickets.split(',')
        obj_list = []
        for i, ticket in enumerate(tickets):
            if i == 10:
                break
            print("Processing the ticket: ", ticket)
            secret_name = self.create_secret_name()
            obj_list.append(secret_name)
            print("Secret name: ", secret_name)
            if not self.get_secret(secret_name=secret_name):
                secret = self.secret_template(secret_name=secret_name, ticket=ticket)
                self.create_secret(secret=secret)
            
                job_name = self.create_job_name()
                obj_list.append(job_name)
                print("Job name: ", job_name)
                if not self.get_job(job_name=job_name):
                    job = self.job_template(job_name=job_name, secret_name=secret_name)
                    self.create_job(job=job)
                else:
                    print('Job exists!')
                
                time.sleep(60)
                wait_quota = self.get_resource_quota(quota_name='bronze-quota')
                print(wait_quota)
                while wait_quota:
                    print("Waiting for available quota")
                    time.sleep(120)
                    wait_quota = self.get_resource_quota(quota_name='bronze-quota')
                    print(wait_quota)
            else:
                print('Secret exists!')
        print("completed!")
        print("obj: ",obj_list)


if __name__ == '__main__':
    urllib3.disable_warnings()
    sbr = SBRTest()
    sbr.main()
