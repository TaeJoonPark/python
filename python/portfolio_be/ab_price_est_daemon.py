#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import time
from datetime import datetime, timedelta
from lib.daemon import Daemon
from multiprocessing import Pool
import ab_price_est_handler

class ABPriceEstDeamon(Daemon):
    def run(self):
        # sys.path.append('/home/vagrant/dev/kr_afterbuy_be/')
        # print sys.path

        pool = Pool(processes=10)
        while True:
            pool.apply_async(ab_price_est_handler.estimate_price)

            # execfile('/home/vagrant/dev/kr_afterbuy_be/ab_price_est_handler.py')

            # print datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # f = open("/tmp/daemon_test.txt", 'a')
            # f.write(os.path.dirname(os.path.abspath( __file__ ))+"\n")
            # f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            # f.write("\n")
            # f.close()
            time.sleep(1)

if __name__ == "__main__":
    daemon = ABPriceEstDeamon('/tmp/ab-price_estimate.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)

"""
def get_process_count():
    import subprocess
    import shlex
    proc1 = subprocess.Popen(shlex.split('ps aux'), stdout=subprocess.PIPE)
    proc2 = subprocess.Popen(shlex.split('grep ab_price_est_handler'), stdin=proc1.stdout, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)

    proc1.stdout.close()  # Allow proc1 to receive a SIGPIPE if proc2 exits.
    # out, err = proc2.communicate()
    # print('out: {0}'.format(out))
    # print('err: {0}'.format(err))

    process_list = proc2.communicate()[0].split('\n')
    process_count = len(process_list) - 1

    return process_count

if __name__ == '__main__':
    process_count = get_process_count()

    if process_count <= 10:
        execfile('./ab_price_est_handler.py')
"""