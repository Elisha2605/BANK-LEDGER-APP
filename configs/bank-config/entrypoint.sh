#!/bin/sh
python3 /service/manage.py makemigrations

python3 /service/manage.py migrate

python3 /service/manage.py createsuperuser --noinput

python3 /service/manage.py crontab add

python3 /service/manage.py rqworker &
/usr/sbin/crond -f -l 8 & 

python3 /service/manage.py $1 $2
