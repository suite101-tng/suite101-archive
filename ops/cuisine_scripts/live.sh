#!/bin/bash
ELB_NAME='suite-front-elb' 
APP_INSTANCES='i-6f9e8196'
BUILD_SERVER='i-b5332f4c'
echo "********************************************************"
echo "********************************************************"
echo "           coming out of maintenance mode"
echo "********************************************************"
echo "********************************************************"

# add app servers to rotation
aws elb register-instances-with-load-balancer --load-balancer-name $ELB_NAME --instances $APP_INSTANCES

# remove build server to rotation
aws elb deregister-instances-from-load-balancer --load-balancer-name $ELB_NAME --instances $BUILD_SERVER
