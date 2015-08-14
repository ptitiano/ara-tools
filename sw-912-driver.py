#!/usr/bin/env python2

from __future__ import print_function
from collections import OrderedDict
from subprocess import call, check_call
from time import sleep, strftime
from pprint import pprint
import pexpect, fdpexpect
import pxssh
import sys
import argparse
import serial
import glob
import re

ITERATION = 10
AP_CMD = 'loopback_test {} {} {} {}/ {}'
APB_CMD = 'gbl -t {} -s {} -w 10 -n ' + str(ITERATION) + ' start'

ROOT_GBL = '/sys/class/gb_loopback'

INSMOD_CMD = "export GB=/lib/modules/`uname -r`/kernel/drivers/greybus && \
echo $GB && \
insmod $GB/greybus.ko; \
insmod $GB/gb-es2.ko; \
insmod $GB/gb-raw.ko; \
insmod $GB/gb-loopback.ko; \
lsmod | grep gb_ | cut -f 1 -d ' '"


# Toshiba APbridge USB ids
USB_VID = 'ffff'
USB_DID = '0002'


DRIVERS = set(('gb_loopback', 'gb_raw', 'gb_es2', 'greybus'))
ENDO_TARGETS = set(('APB1', 'APB2', 'APB3', 'GPB1', 'GPB2', 'SVC'))

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

def gbl_status(f):

    f.sendline('gbl status')
    f.expect('REQ_PER_SEQ')
    f.expect('nsh>')
    return f.before.split()


def gbl_stats(f, cmd):

    f.sendline('gbl stop')
    f.expect('nsh>')
    info(f.before.strip())

    # split the cmd otherwise, nuttx is missing some
    # characters
    for c in cmd.split():
        f.send(c + ' ')
    f.sendline()
    f.expect('nsh>')
    info(f.before.strip())

    # Wait until completion 'ACTIVE = no'
    while True:
        st = gbl_status(f)
        if st[1] == 'no':
            break
        else:
            sleep(1)

    f.sendline('gbl -f csv status')
    info(f.readline().strip())
    f.readline()
    f.readline()
    f.expect('nsh>')
    info(f.before.strip())

    return f.before.strip()


def exec_svc_cmd(svc, cmd):

    svc.sendline(cmd)
    svc.expect('nsh>')
    info(svc.before.strip())


def exec_loopback(ssh, cmd):

    ssh.sendline(cmd)
    ssh.prompt()
    info(ssh.before.strip())


def run_from_ap(svc, host, test, size, verbose, target):

    ssh_host = '{}@{}'.format(USER, host)
    csv_path = '~{}/{}_{}_{}.csv'.format(USER, test, size, ITERATION)
    csv_url = '{}:{}'.format(ssh_host, csv_path)

    ap_test_cmd = AP_CMD.format(test, size, ITERATION, target.sysfs, target.dev)

    info(ssh_host, csv_path, csv_url, test, size)
    info(ap_test_cmd)

    svcfd = fdpexpect.fdspawn(svc.fd, timeout=5)

    info('Erase previous CSV file ({})'.format(csv_path))

    s = pxssh.pxssh()
    s.login(host, USER)
    s.sendline('rm {f}; touch {f}'.format(f=csv_path))  # run a command
    s.prompt()  # match the prompt
    info(s.before)  # print everything before the prompt.

    count = 1

    try:
        for pwrm, cmds in PWRM_TO_CMDS:

            info('\nTest ({}) - {}\n'.format(count, pwrm))

            for cmd in cmds:
                exec_svc_cmd(svcfd, cmd)

            if verbose:
                # insert the test name into the CSV file
                # TODO: add a new column into the CSV instead of new row
                call(['ssh', ssh_host,
                      'echo "{}" >> {}'.format(pwrm, csv_path)])

            exec_loopback(s, ap_test_cmd)
            exec_loopback(s, ap_test_cmd)
            exec_loopback(s, ap_test_cmd)

            count += 1

    except KeyboardInterrupt:
        info('\nKeyboardInterrupt')

    # transfer the results CSV file to from AP to Host
    call(['scp', csv_url, '.'])
    s.logout()


def run_from_apbridge(svc, host, test, size, verbose, apb):

    csv_path = 'apb_{}_{}_{}.csv'.format(test, size, ITERATION)

    # gbl is using a slightly different name
    apb_test_cmd = APB_CMD.format(test.replace('transfer', 'xfer'), size)

    info(csv_path, test, size, apb_test_cmd)

    svcfd = fdpexpect.fdspawn(svc.fd, timeout=5)

    f = fdpexpect.fdspawn(apb.fd, timeout=5)

    info('Create CSV file ({})'.format(csv_path))

    with open(csv_path, "w") as fd:

        count = 1

        try:
            for pwrm, cmds in PWRM_TO_CMDS:

                info('\nTest ({}) - {}\n'.format(count, pwrm))

                for cmd in cmds:
                    exec_svc_cmd(svcfd, cmd)

                if verbose:
                    # insert the test name into the CSV file
                    # TODO: add a new column into the CSV instead of new row
                    call(['ssh', ssh_host,
                          'echo "{}" >> {}'.format(pwrm, csv_path)])

                fd.write('{},{},{},{}\n'.format(
                          strftime("%c"),
                          test,
                          size,
                          gbl_stats(f, apb_test_cmd)))
                fd.write('{},{},{},{}\n'.format(
                          strftime("%c"),
                          test,
                          size,
                          gbl_stats(f, apb_test_cmd)))
                fd.write('{},{},{},{}\n'.format(
                          strftime("%c"),
                          test,
                          size,
                          gbl_stats(f, apb_test_cmd)))

                count += 1

        except KeyboardInterrupt:
            info('\nKeyboardInterrupt')


def check_usb_connection(ssh):

    ssh.sendline('lsusb -d {}:{}'.format(USB_VID, USB_DID))
    ssh.readline()
    ssh.prompt()
    if ssh.before.strip() == '':
        raise ValueError('Endo is not connected to USB')


def load_driver(ssh):

    ssh.sendline(INSMOD_CMD)
    ssh.prompt()
    # retrieve the last 4 items that should be the loaded drivers
    drv = set(ssh.before.split()[-4:])
    if drv != DRIVERS:
        raise ValueError('Cannot load all the drivers {}'.format(
                            list(DRIVERS - drv)))


def get_devices(ssh):

    ssh.sendline('ls --color=never {}'.format(ROOT_GBL))
    ssh.readline()
    ssh.prompt()

    return ssh.before.split()


def get_device_sysfslink(ssh, dev):

    ssh.sendline('readlink -f {}/{}'.format(ROOT_GBL, dev.replace('!','\!')))
    ssh.readline()
    ssh.prompt()

    return '/'.join(ssh.before.strip().split('/')[:-2])


def get_device_id(ssh, path):

    ssh.sendline('cat {}/../../device_id'.format(path))
    ssh.readline()
    ssh.prompt()

    return ssh.before.strip()


def get_device_path(dev):

     return '/dev/{}'.format(dev.replace('!','/'))


def id_to_name(did):
    if did < 4:
        return 'APB{}'.format(did)
    else:
        return 'GPB{}'.format(did - 3)

#
# Use to store information relative to the target.
# target can be BBB, SVC or any bridges (AP, GP)
#
class Target():

    def __init__(self, name, tty='', did=0):
        if did > 0:
            self.name = id_to_name(did)
        else:
            self.name = name
        self.tty = tty
        self.did = did
        self.sysfs = ''
        self.dev = ''

    def __repr__(self):
        return '{}, {}, {}, {}, {}'.format(
                self.name, self.did, self.tty, self.dev, self.sysfs)


def get_usb_tty():

    return glob.glob('/dev/ttyUSB*')


def get_target_type(tty, baudrate):

    ser = serial.Serial(port=tty, baudrate=baudrate)
    ser.flushInput()
    fdp = fdpexpect.fdspawn(ser.fd, timeout=10)

    try:
        fdp.sendline('help')
        fdp.expect(['nsh>', 'bash', 'Password', 'Login'])
    except pexpect.TIMEOUT:
        info('timeout {}'.format(fdp.before.strip()))
        return Target('UNK', tty)
    except pexpect.EOF:
        info('Cannot reach the console {}'.format(tty))
        return Target('UNK', tty)

    if 'nsh>' in fdp.after:
        if 'svc' in fdp.before:
            return Target('SVC', tty)

        try:
            fdp.sendline('unipro r 0x3000 0')
            fdp.expect('nsh>')
            m = re.search('\[3000\]: (\d)', fdp.before)
            d = int(m.group(1))
            return Target('UNK', tty, d)
        except pexpect.TIMEOUT:
            info('{} timeout {}'.format(tty, fdp.before.strip()))
            return Target('UNK', tty)
    else:
        return Target('BBB', tty)


#
# main
#


def main():
    # Parse arguments.
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--baudrate',
                        default=SVC_DEFAULT_BAUD,
                        help='baud rate of SVC/APB tty, default {}'.format(
                            SVC_DEFAULT_BAUD))
    parser.add_argument('host', help='IP/hostname of target AP', default=HOST)
    parser.add_argument('-b', '--bridge', help='apbridge2 tty', default='APB2')
    parser.add_argument('-s', '--size', default=512, help='Packet Size')
    parser.add_argument('-t', '--test',
                        default='sink',
                        choices=['sink', 'transfer', 'ping'],
                        help='Test type')
    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Add extra info in CSV')
    parser.add_argument('--ap',
                        action='store_true',
                        help='Run test from AP instead of APBridge')
    parser.add_argument('-l', '--list',
                        action='store_true',
                        help='List loopback devices')
    parser.add_argument('-u', '--usb',
                        action='store_true',
                        help='List USB tty')
    args = parser.parse_args()


    info('Enumerating and probing tty USB consoles')

    targets = {}

    for tty in get_usb_tty():
        t = get_target_type(tty, args.baudrate)
        info('  {} -> {}'.format(t.name, t.tty))
        targets[t.name] = t

    if not (ENDO_TARGETS & set(targets)):
        fatal_err('Cannot find any valid Endo modules.\
                    The board might not be powered')

    if args.usb:
        return


    try:
        ssh = pxssh.pxssh()
        ssh.login(args.host, USER)

        info('Checking USB connection...')
        check_usb_connection(ssh)

        info('Loading Greybus drivers...')
        load_driver(ssh)

        info('Enumerating loopback devices in the endo...')
        devs = get_devices(ssh)

        for dev in devs:
            p = get_device_sysfslink(ssh, dev)
            d = int(get_device_id(ssh, p))
            n = id_to_name(d)
            if not n in targets.keys():
                info('{} UART is not connected'.format(n))
                break
            targets[n].sysfs = p
            targets[n].dev = get_device_path(dev)
            info('  {}[{}]={}, dev={}'.format(
                    n, d, p.split('/')[-1], get_device_path(dev)))

    except ValueError as e:
        fatal_err(str(e))
        return

    ssh.logout()

    if args.list:
        return

    info('AP host: {}'.format(args.host))

    # Open the SVC and AP console ttys and flush any input characters.
    try:
        info('opening SVC console {} at: {} baud'.format(
                targets['SVC'].tty, args.baudrate))
        svc = serial.Serial(port=targets['SVC'].tty, baudrate=args.baudrate)
        info('flushing SVC input buffer')
        svc.flushInput()
    except:
        fatal_err('failed initializing SVC')


    bridge = targets[args.bridge]

    try:
        info('opening {} console {} at: {} baud'.format(
                bridge.name, bridge.tty, args.baudrate))
        apb = serial.Serial(port=bridge.tty, baudrate=args.baudrate)
        info('flushing {} input buffer'.format(bridge.name))
        apb.flushInput()
    except:
        fatal_err('failed initializing ' + bridge.name)

    # Execute the above-defined power mode changes at the SVC
    # console.
    if args.ap:
        run_from_ap(svc, args.host, args.test, args.size, args.verbose, bridge)
    else:
        run_from_apbridge(svc, args.host, args.test, args.size, args.verbose,
                          apb)

if __name__ == '__main__':
    main()
