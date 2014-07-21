#!/bin/bash

ADDRESS="http://localhost:8888/api/v1/"

function status() {
    curl $ADDRESS
    echo
    curl ${ADDRESS}strategy
    echo
}

function HUPHUP() {
    kill -HUP `cat ~/.config/juju-deployer/server.pid`
    curl ${ADDRESS}strategy
    echo
}

status
curl -d @state.json $ADDRESS
curl $ADDRESS
echo

HUPHUP

#curl $ADDRESS/reset


