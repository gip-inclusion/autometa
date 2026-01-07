#!/bin/bash
# View Matometa container logs
# Usage: ./deploy/logs.sh [-f]

ssh matometa@ljt.cc "docker logs ${1:--n 50} matometa-matometa-1"
