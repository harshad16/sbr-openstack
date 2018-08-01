import os
import string
import json
import base64
import random
import requests
import xml.etree.ElementTree as ET
from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)
ocl_url = os.getenv('OCL_URL')
ocl_token = os.getenv('OCL_TOKEN')
ocl_namespace = os.getenv('OCL_NAMESPACE')


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/process_ticket', methods=['GET', 'POST'])
def process_ticket():
    success = False
    solution = "Not Available"
    next = request.values.get('next', '')
    if request.method == 'POST':
        namespace = ocl_namespace if ocl_namespace else '' #set default here
        url = ocl_url if ocl_url else '' #set default here
        access_token = ocl_token if ocl_token else '' #set default here
        print(url,access_token)
        headers = {'Content-Type':'application/json','Authorization': 'Bearer {}'.format(access_token),'Accept': 'application/json','Connection': 'close'}
        secret_name = 'sbr-{}'.format(''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))
        secret ={
                  "kind": "Secret",
                  "apiVersion": "v1",
                  "metadata": {
                    "name": secret_name,
                    "namespace": namespace
                  },
                  "type": "kubernetes.io/basic-auth",
                  "stringData": {
                    "username": request.form.get("username"),
                    "password": request.form.get("password"),
                    "ticket": request.form.get("ticket"),
                    "server": request.form.get("server")
                   }
                }
        secret_endpoint = '{}/api/v1/namespaces/{}/secrets'.format(url,namespace)
        secret_response = requests.post(secret_endpoint, json=secret, headers=headers, verify=False)
        print(secret_response.status_code)
        print(secret_response.text)

        job_name = 'sbr-job-{}'.format(''.join(random.choices(string.ascii_lowercase + string.digits, k=6)))
        job_endpoint = '{}/apis/batch/v1/namespaces/{}/jobs'.format(url,namespace)
        payload = {
                  "apiVersion": "batch/v1",
                  "kind": "Job",
                  "metadata": {
                    "name": job_name,
                    "labels": {
                      "app": "sbr"
                    },
                    "namespace":namespace
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
                                "name": "USERNAME",
                                "valueFrom": {
                                  "secretKeyRef": {
                                    "key": "username",
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
                                  "key": "password",
                                  "path": "passwordfile",
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
                
        job_response = requests.post(job_endpoint, json=payload,headers=headers, verify=False)
        print(job_response.status_code)
        print(job_response.text)
        if job_response.status_code == 201:
            success =True
            solution="on the way"
        # status_check = ['1', 'Running']
        # if not job_response:
        #     while status_check[1] == 'Running' and status_check[0] == '1':
        #         job_status = os.popen('oc describe job sbr').read()
        #         job = job_status.split('\n')
        #         status = list
        #         for param in job:
        #             if ':' in param:
        #                 key, val = param.split(':', 1)
        #                 if key == 'Pods Statuses':
        #                     status = [stat.strip().split(' ') for stat in val.split('/')]
        #                     break
        #         solution = ""
        #         url = 'https://access.redhat.com/support/cases/#/case/{}'.format(str(request.form.get("ticket")))
        #         if status:
        #             for stat in status:
        #                 status_check = stat
        #                 print('status_check', status_check)
        #                 if stat[1] == 'Running' and stat[0] == '1':
        #                     break
        #                 elif stat[1] == 'Succeeded' and stat[0] == '1':
        #                     success = True
        #                     comment_url = 'https://api.access.redhat.com/rs/cases/{}/comments'.format(str(request.form.get("ticket")))
        #                     response = requests.get(comment_url, auth=(request.form.get("username"), request.form.get("password")))
        #                     if response.status_code == 200:
        #                         xml = response.text
        #                         tree = ET.fromstring(xml)
        #                         try:
        #                             solution = tree[1][4].text
        #                             print(solution.split('\n'))
        #                         except:
        #                             pass
        #                     break
        #                 else:
        #                     success = False
        #         else:
        #             success = False

    return render_template('end.html', success=success, ticket=str(request.form.get("ticket")), url=url, solution=solution)


if __name__ == '__main__':
    app.run(host="0.0.0.0",port=8080, debug=True)
