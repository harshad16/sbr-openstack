FROM fedora:28

ENV USER sbr

RUN \
	dnf install -y --setopt=tsflags=nodocs git openssh-clients python36 python27 python3-pip sshpass findutils && \
	pip3 install requests prometheus_client && \
	git clone https://github.com/citellusorg/citellus.git && \
	git -c http.sslVerify=false clone https://gitlab.cee.redhat.com/gss-tools/rh-internal-citellus.git && \
	cp /rh-internal-citellus/overrides.json /citellus/citellusclient/plugins/ && \
	cp /rh-internal-citellus/citellus.mo /citellus/citellusclient/locale/en/LC_MESSAGES/ && \
	cp /rh-internal-citellus/citellus.po /citellus/citellusclient/locale/en/LC_MESSAGES/ && \
	cp -r /rh-internal-citellus/plugins/  /citellus/citellusclient/ && \
	mkdir /cases && \
   	chmod a+wr /cases /etc/passwd

COPY sbr-openstack-bot.py /
COPY docker_entry.sh /

ENTRYPOINT ["/docker_entry.sh"]
CMD ["sbr-openstack-bot.py"]
