#!/bin/bash

mkdir certs
openssl ecparam -genkey -name secp384r1 -out certs/server.key
openssl req -new -x509 -sha256 -key certs/server.key -out certs/server.crt -days 3650 -subj "/C=AU/ST=Queensland/L=Brisbane/O=Sandbox/OU=Sandbox/CN=sandbox.local/emailAddress=rcernin@redhat.com"

