import os
import string
import time
import urllib3
import random
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)
ocl_url = os.getenv('OCP_URL')
ocl_token = os.getenv('OCP_TOKEN')
ocl_namespace = os.getenv('OCP_NAMESPACE')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/process_ticket', methods=['GET', 'POST'])
def process_ticket():
    success = False
    solution = "Not Available"
    case_url = 'https://access.redhat.com/support/cases/#/case/{}'.format(str(request.form.get("ticket")))
    ERROR = []
    status_check = True
    rhnusername = request.form.get("rhn_username") if request.form.get("rhn_username") else request.form.get(
        "rh_username")
    rhnpassword = request.form.get("rhn_password") if request.form.get("rhn_password") else request.form.get(
        "rh_password")
    if request.method == 'POST':
        namespace = ocl_namespace if ocl_namespace else ''  # set default here
        url = ocl_url if ocl_url else ''  # set default here
        access_token = ocl_token if ocl_token else ''  # set default here
        headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(access_token),
                   'Accept': 'application/json', 'Connection': 'close'}
        secret_name = 'sbr-{}'.format(''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))
        secret = {
            "kind": "Secret",
            "apiVersion": "v1",
            "metadata": {
                "name": secret_name,
                "namespace": namespace
            },
            "type": "kubernetes.io/basic-auth",
            "stringData": {
                "rhnusername": rhnusername,
                "rhnpassword": rhnpassword,
                "username": request.form.get("rh_username"),
                "password": request.form.get("rh_password"),
                "ticket": request.form.get("ticket"),
                "server": request.form.get("server")
            }
        }
        secret_endpoint = '{}/api/v1/namespaces/{}/secrets'.format(url, namespace)
        secret_response = requests.post(secret_endpoint, json=secret, headers=headers, verify=False)
        print(secret_response.status_code)

        job_name = 'sbr-job-{}'.format(''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))
        job_endpoint = '{}/apis/batch/v1/namespaces/{}/jobs'.format(url, namespace)
        payload = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": job_name,
                "labels": {
                    "app": "sbr"
                },
                "namespace": namespace
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
                                                "key": "username",
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
                                        "cpu": "2"
                                    },
                                    "limits": {
                                        "memory": "2Gi",
                                        "cpu": "2"
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
                                            "key": "password",
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

        job_response = requests.post(job_endpoint, json=payload, headers=headers, verify=False)
        print(job_response.status_code)
        if job_response.status_code == 201:
            success = True
            solution = "The job is Running. Please Visit the below Url for the solution in 3-4 mins"
        else:
            success = False

        if request.form.get("no_debug") is not None:
            return render_template('end.html', success=success, ticket=str(request.form.get("ticket")), url=case_url,
                                   solution=solution, ERROR=ERROR)

        while status_check:
            # 5 sec delay for stopping unneccessary requests
            time.sleep(5)
            job_check_endpoint = '{}/apis/batch/v1/namespaces/{}/jobs/{}'.format(url, namespace, job_name)
            job_check_response = requests.get(job_check_endpoint, headers=headers, verify=False)
            print(job_check_response.status_code)
            job_details = job_check_response.json().get('status')
            if job_details:
                if 'active' in job_details and job_details['active'] == 1:
                    status_check = True
                    continue
                elif 'succeeded' in job_details and job_details['succeeded'] == 1:
                    success = True
                    status_check = False
                    comment_url = 'https://api.access.redhat.com/rs/cases/{}/comments'.format(
                        str(request.form.get("ticket")))
                    response = requests.get(comment_url,
                                            auth=(request.form.get("rhn_username"), request.form.get("rhn_password")))
                    if response.status_code == 200:
                        xml = response.text
                        tree = ET.fromstring(xml)
                        try:
                            solution = tree[1][4].text
                            # print(solution.split('\n'))
                        except:
                            print('Can not fetch the solutions!')
                            pass
                    try:
                        res = requests.get('http://pushgateway-aicoe.cloud.paas.upshift.redhat.com')
                        content = res.content
                        soup = BeautifulSoup(content)
                        sample = soup.find_all("div", "panel-heading cursor-pointer")
                        error_dict = {}
                        error_key = []
                        error_value = []
                        for index in range(len(sample)):
                            error_name = ""
                            for tag in sample[index].find('span').next_siblings:
                                if tag.name == 'span':
                                    break
                                else:
                                    error_name += str(tag)
                            if error_name.strip(' \t\n\r'):
                                error_key.append(error_name.strip(' \t\n\r'))

                        sample2 = soup.find_all("table", "table table-striped table-bordered table-hover")
                        for index in range(len(sample2)):
                            for tag2 in sample2[index].find_all("td"):
                                td = tag2.get_text().strip(' \t\n\r').split()
                                if len(td) < 2 and td:
                                    error_value.append(td[0])
                        for x in range(len(error_value)):
                            error_dict[error_key[x]] = error_value[x]
                        error_check = job_name + '-scp-error'
                        error_check = error_check.replace('-', '_')
                        if error_check in error_dict and error_dict[error_check] == '1':
                            ERROR.append(
                                'File Not Found for ticket {} in the {} Server'.format(request.form.get('ticket'),
                                                                                       request.form.get('server')))
                        elif error_check in error_dict and error_dict[error_check] == '5':
                            ERROR.append('Authentication failed for Red Hat Kerberos')
                        elif error_check in error_dict and error_dict[error_check] == '2':
                            ERROR.append('SCP of attachment for ticket {} from the {} server failed'.format(
                                request.form.get('ticket'), request.form.get('server')))

                        if str(job_name + '-solution-request').replace('-', '_') in error_dict:
                            ERROR.append('API Request failed due to Authentication of RHN account')
                        # print(ERROR)
                    except Exception as e:
                        print('Problem occured in scrapping prometheus metrics!')
                        pass
                    break

                elif 'failed' in job_details and job_details['failed']:
                    success = False
                    status_check = False

            else:
                success = False

    return render_template('end.html', success=success, ticket=str(request.form.get("ticket")), url=case_url,
                           solution=solution, ERROR=ERROR)


if __name__ == '__main__':
    urllib3.disable_warnings()
    app.run(host="0.0.0.0", port=8080, debug=True)
