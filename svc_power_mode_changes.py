#!/usr/bin/env python2

from __future__ import print_function
from collections import OrderedDict
from subprocess import call, check_call
import sys
import argparse
import serial

T1_CMD = '/root/loopback_test sink 512 1000 /sys/bus/greybus/devices/endo0:1:1:1:13/ /dev/gb/loopback0'
T2_CMD = '/root/loopback_test sink 512 1000 /sys/bus/greybus/devices/endo0:1:2:1:13/ /dev/gb/loopback1'
T5_CMD = '/root/loopback_test transfer 512 1000 /sys/bus/greybus/devices/endo0:1:1:1:13/ /dev/gb/loopback0'


# default IP of the AP
HOST = '192.168.3.2'
USER = 'root'


SVC_DEFAULT_BAUD = 115200

PWRM_TO_CMDS = (
    ('PWM-G1, 1 lane', ['svc linktest -p 0 -m pwm -g 1 -s a -l 1',
                        'svc linktest -p 1 -m pwm -g 1 -s a -l 1']),
    ('PWM-G2, 1 lane', ['svc linktest -p 0 -m pwm -g 2 -s a -l 1',
                        'svc linktest -p 1 -m pwm -g 2 -s a -l 1']),
    ('PWM-G3, 1 lane', ['svc linktest -p 0 -m pwm -g 3 -s a -l 1',
                        'svc linktest -p 1 -m pwm -g 3 -s a -l 1']),
    ('PWM-G4, 1 lane', ['svc linktest -p 0 -m pwm -g 4 -s a -l 1',
                        'svc linktest -p 1 -m pwm -g 4 -s a -l 1']),
    ('PWM-G1, 2 lanes', ['svc linktest -p 0 -m pwm -g 1 -s a -l 2',
                         'svc linktest -p 1 -m pwm -g 1 -s a -l 2']),
    ('PWM-G2, 2 lanes', ['svc linktest -p 0 -m pwm -g 2 -s a -l 2',
                         'svc linktest -p 1 -m pwm -g 2 -s a -l 2']),
    ('PWM-G3, 2 lanes', ['svc linktest -p 0 -m pwm -g 3 -s a -l 2',
                         'svc linktest -p 1 -m pwm -g 3 -s a -l 2']),
    ('PWM-G4, 2 lanes', ['svc linktest -p 0 -m pwm -g 4 -s a -l 2',
                         'svc linktest -p 1 -m pwm -g 4 -s a -l 2']),
    ('HS-G1A, 1 lane', ['svc linktest -p 0 -m hs -g 1 -s a -l 1',
                        'svc linktest -p 1 -m hs -g 1 -s a -l 1']),
    ('HS-G2A, 1 lane', ['svc linktest -p 0 -m hs -g 2 -s a -l 1',
                        'svc linktest -p 1 -m hs -g 2 -s a -l 1']),
    ('HS-G1A, 2 lanes', ['svc linktest -p 0 -m hs -g 1 -s a -l 2',
                         'svc linktest -p 1 -m hs -g 1 -s a -l 2']),
    ('HS-G2A, 2 lanes', ['svc linktest -p 0 -m hs -g 2 -s a -l 2',
                         'svc linktest -p 1 -m hs -g 2 -s a -l 2']),
    ('HS-G1B, 1 lane', ['svc linktest -p 0 -m pwm -g 1 -s a -l 1',
                        'svc linktest -p 1 -m pwm -g 1 -s a -l 1',
                        'svc linktest -p 0 -m pwm -g 1 -s b -l 1',
                        'svc linktest -p 1 -m pwm -g 1 -s b -l 1',
                        'svc linktest -p 0 -m hs -g 1 -s b -l 1',
                        'svc linktest -p 1 -m hs -g 1 -s b -l 1']),
    ('HS-G2B, 1 lane', ['svc linktest -p 0 -m pwm -g 1 -s a -l 1',
                        'svc linktest -p 1 -m pwm -g 1 -s a -l 1',
                        'svc linktest -p 0 -m pwm -g 1 -s b -l 1',
                        'svc linktest -p 1 -m pwm -g 1 -s b -l 1',
                        'svc linktest -p 0 -m hs -g 2 -s b -l 1',
                        'svc linktest -p 1 -m hs -g 2 -s b -l 1']),
    ('HS-G1B, 2 lanes', ['svc linktest -p 0 -m pwm -g 1 -s a -l 2',
                         'svc linktest -p 1 -m pwm -g 1 -s a -l 2',
                         'svc linktest -p 0 -m pwm -g 1 -s b -l 2',
                         'svc linktest -p 1 -m pwm -g 1 -s b -l 2',
                         'svc linktest -p 0 -m hs -g 1 -s b -l 2',
                         'svc linktest -p 1 -m hs -g 1 -s b -l 2']),
    ('HS-G2B, 2 lanes', ['svc linktest -p 0 -m pwm -g 1 -s a -l 2',
                         'svc linktest -p 1 -m pwm -g 1 -s a -l 2',
                         'svc linktest -p 0 -m pwm -g 1 -s b -l 2',
                         'svc linktest -p 1 -m pwm -g 1 -s b -l 2',
                         'svc linktest -p 0 -m hs -g 2 -s b -l 2',
                         'svc linktest -p 1 -m hs -g 2 -s b -l 2']))

#
# UI
#


def info(*args, **kwargs):
    kwargs['file'] = sys.stdout
    print(*args, **kwargs)


def err(*args, **kwargs):
    kwargs['file'] = sys.stderr
    args = ('error:',) + args
    print(*args, **kwargs)


def fatal_err(*args, **kwargs):
    err(*args, **kwargs)
    sys.exit(1)


def svc_io(*args, **kwargs):
    args = ('<SVC>:',) + args
    info(*args, **kwargs)


#
# Command handling
#


def wait_for_ret_or_abort():
    try:
        while True:
            c = sys.stdin.read(1)
            info('mbolivar:', ord(c))
            if c == '\r' or c == '\n':
                return
    except KeyboardInterrupt:
        sys.exit(0)


def exec_cmd(svc, cmd):
    nsh_prompt = 'nsh> '
    buf = []

    try:
        svc.write(''.join(buf) + cmd + '\n')
        while True:
            if svc.inWaiting():
                c = svc.read()
                buf.append(c)
                if c == '\n':
                    svc_io(''.join(buf), end='')
                    buf = []
                if len(buf) >= len(nsh_prompt) and ''.join(buf) == nsh_prompt:
                    return  # got nsh> prompt
    except IOError as e:
        fatal_err("couldn't set power mode:", str(e))


def exec_loopback(rhost, cmd):

    check_call(['ssh', rhost, cmd])


def exec_power_mode_changes(svc, host):

    ssh_host = '%s@%s' % (USER, host)
    csv_path = '/%s/transfer_512_1000.csv' % USER
#    csv_path = '/%s/sink_512_1000.csv' % USER
    csv_url = '%s:%s' % (ssh_host, csv_path)

    test_cmd = T5_CMD

#    info(ssh_host, csv_path, csv_url)

    print('Erase previous CSV file (%s)' % csv_path)
    call(['ssh', ssh_host, 'rm %s' % csv_path])

    count = 1

    try:
        for pwrm, cmds in PWRM_TO_CMDS:

            print('\nTest (%d) - ' % count + pwrm + '\n')

            for cmd in cmds:
                exec_cmd(svc, cmd)

            # insert the test name into the CSV file
            # TODO: add a new column into the CSV instead of new row
            call(['ssh', ssh_host, 'echo "%s" >> %s' % (pwrm, csv_path)])

            exec_loopback(ssh_host, test_cmd)
            exec_loopback(ssh_host, test_cmd)
            exec_loopback(ssh_host, test_cmd)

            count += 1

    except KeyboardInterrupt:
        info('\nKeyboardInterrupt')

    # transfer the results CSV file to from AP to Host
    call(['scp', csv_url, '.'])


#
# main
#


def main():
    # Parse arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument('-b', '--baudrate',
                        default=SVC_DEFAULT_BAUD,
                        help='baud rate of SVC tty, default {}'.format(
                            SVC_DEFAULT_BAUD))
    parser.add_argument('svc', help='Path to SVC console tty')
    parser.add_argument('host', help='IP/hostname of target AP', default=HOST)
    args = parser.parse_args()

    # Open the SVC console tty and flush any input characters.
    info('opening SVC at: {}, {} baud'.format(args.svc, args.baudrate))
    info('AP host: %s' % args.host)
    try:
        svc = serial.Serial(port=args.svc, baudrate=args.baudrate)
    except:
        fatal_err('failed to open SVC')
    try:
        svc.flushInput()
        info('flushed SVC input buffer')
    except:
        fatal_err("couldn't flush SVC input buffer")

    # Execute the above-defined power mode changes at the SVC
    # console.
    exec_power_mode_changes(svc, args.host)

if __name__ == '__main__':
    main()
