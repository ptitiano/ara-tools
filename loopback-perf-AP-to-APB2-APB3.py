#!/usr/bin/env python2

from os import system
import argparse

LOOPBACK_PERF_DRIVER = './loopback-perf-driver.py'

def main():
    # Parse arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--baudrate',
                        help='baud rate of SVC/APB tty')
    parser.add_argument('host', help='IP/hostname of target AP')
    parser.add_argument('-s', '--size', default=500, help='Packet Size')
    parser.add_argument('-i', '--iteration',
                        help='The number of iterations to run the test over',
                        default=100)
    parser.add_argument('-v', '--verbose', dest="verbose", default=False,
                        action='store_true',
                        help='Make script execution more verbose')
    args = parser.parse_args()

    # Call 'sw-912-driver.py' with T2-specific options
    cmd = '{} '.format(LOOPBACK_PERF_DRIVER)
    # User command-line options
    cmd += '{} '.format(args.host)
    if args.baudrate:
        cmd += '-r {} '.format(args.baudrate)
    if args.size:
        cmd += '-s {} '.format(args.size)
    if args.iteration:
        cmd += '-i {} '.format(args.iteration)
    if args.verbose:
        cmd += '-v'.format(args.baudrate)
    # 'AP to APB2+APB3' test case specific options ('T2')
    cmd += ' --ap'
    cmd += ' -t sink'
    cmd += ' -b APB2 APB3'
    cmd += ' -c T2'

    if args.verbose:
        print(cmd)
    system(cmd)

if __name__ == '__main__':
    main()
