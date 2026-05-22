#!/bin/bash
cd /home/maka/arduino
source venv/bin/activate
exec proxychains watchexec -e py -r python app.py
