#!/bin/bash
PATH=$PATH:/usr/local/bin
PYTHONPATH=/home/idve/kr_afterbuy_be
export PATH PYTHONPATH

python /home/idve/kr_afterbuy_be/controllers/cr_exchange_rate.py
