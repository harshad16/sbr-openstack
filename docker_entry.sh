#!/bin/bash

# Check whether there is a passwd entry for the container UID
myuid=$(id -u)
mygid=$(id -g)
uidentry=$(getent passwd $myuid)

# If there is no passwd entry for the container UID, attempt to create one
if [ -z "$uidentry" ] ; then
    if [ -w /etc/passwd ] ; then
        echo "$myuid:x:$myuid:$mygid:anonymous uid:/home/user:/bin/false" >> /etc/passwd
    else
        echo "Container ENTRYPOINT failed to add passwd entry for anonymous UID"
    fi
fi
exec python3 app.py "$@"
