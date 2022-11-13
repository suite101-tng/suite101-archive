#!/bin/bash
ELB_NAME='suite-front-elb' 
APP_INSTANCES='i-6f9e8196'
BUILD_SERVER='i-ccd34f4b'
echo "********************************************************"
echo "********************************************************"
echo "           going into maintenance mode"
echo "********************************************************"
echo "********************************************************"

# remove app servers from rotation
aws elb deregister-instances-from-load-balancer --load-balancer-name $ELB_NAME --instances $APP_INSTANCES

# add build server to rotation
aws elb register-instances-with-load-balancer --load-balancer-name $ELB_NAME --instances $BUILD_SERVER
