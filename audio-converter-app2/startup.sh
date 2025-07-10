#!/bin/bash
cd /home/site/wwwroot
pip install -r requirements.txt
exec gunicorn app:app --bind=0.0.0.0:8000 --capture-output --log-level debug --access-logfile - --error-logfile -