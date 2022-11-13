#!/bin/bash

echo "stopping suite ..."
sudo initctl emit suite-stop
sleep 1s
echo "starting suite ..."
sudo initctl emit suite-start
touch /tmp/django-restart
echo "restart complete!"