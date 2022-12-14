#!/usr/bin/python
'''
Tool for test sending from E34 on /dev/ttyUSB?, and receive on another E34 on /dev/ttyUSB?.

I have got this code from Berdy.
'''
__author__ = "Berdy"
# __copyright__ = "Copyright 2007, The Cogent Project"
# __credits__ = ["Rob Knight", "Peter Maxwell", "Gavin Huttley",
#                     "Matthew Wakefield"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Pasakorn Tiwatthanont"
# __email__ = "..."
# __status__ = "Production"


import sys
import serial
import time
from datetime import datetime
import string
import random

import difflib


TMO_PERIOD_SEC = 5.
DELAY_CHECK_SEC = .01
DELAY_INTER_FRAME_SEC = 0.
DEFAULT_PAYLOAD_LEN = 279  # MAVLink v2 max length -- https://mavlink.io/en/guide/serialization.html


# -----------------------------------------------------------------------------
def print_info(str):
    current_time = datetime.now().strftime("%H:%M:%S")
    print(current_time + '>' + str)


# -----------------------------------------------------------------------------
def random_string(N):
    str = ''.join(random.choices(string.ascii_letters + string.digits, k=N))
    #str = ''.join([ chr(i) for i in range(N)])
    str = str + '\n'
    return str


# -----------------------------------------------------------------------------
def generate_deterministic_string(start : int, size : int) -> bytes:
    s = b''
    for i in range(start, start + size):
        s += (i%256).to_bytes(1, byteorder='big')
    return s


# -----------------------------------------------------------------------------
def compare_send_recv_bytes(sent_bytes : bytes, recv_bytes : bytes):
    # https://www.educative.io/answers/what-is-sequencematcher-in-python
    # string1 = "I love to eat apple."
    # string2 = "But I do not like to eat pineapple."
    # temp = difflib.SequenceMatcher(None, string1, string2)
    # print(temp.get_matching_blocks())
    # print('Similarity Score: ', temp.ratio())
    temp = difflib.SequenceMatcher(None, sent_bytes, recv_bytes)
    print('   ', temp.get_matching_blocks())
    print('    Similarity Score:', temp.ratio())
    return 1 if (temp.ratio() < 1.) else 0


# -----------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('Ex.> {} <port> <baud> [payload_len | {}]'.format(sys.argv[0], DEFAULT_PAYLOAD_LEN))
    serial_port = sys.argv[1]
    serial_baud = sys.argv[2]
    payload_len = int(sys.argv[3]) if len(sys.argv) >= 4 else DEFAULT_PAYLOAD_LEN
    print_info(str(sys.argv))

    result_ok = 0
    result_failed = 0
    result_timeout = 0
    start_time = time.time()
    send_max = 1000

    with serial.Serial(serial_port, serial_baud) as ser:
        while ((time.time() - start_time) < 60):
            # send test string to slave device
            # send_str = b"start:%d:0123456789a0123456789b0123456789c0123456789d0123456789e0123456789f|mid|0123456789a0123456789b0123456789c0123456789d0123456789e0123456789f|end\n" % (1000-send_max)  #random_string(30)
            # send_str = random_string(payload_len)
            send_str = generate_deterministic_string(0, payload_len)

            # print(len(send_str))
            # print(send_str)
            # break

            if isinstance(send_str,  str):
                recv_str = ''
                ser.write(send_str.encode())  # Sending..
            else:
                recv_str = bytes()
                ser.write(send_str)
                # send_str += bytes(10)  # XXX: Fake sending over than receiving
                # send_str = send_str[10:]  # XXX: Fake sending less than receiving

            waiting = True
            send_time = time.time()
            # print_info(send_str)

            while (waiting):
                # Check timeout
                elapse_time = time.time() - send_time
                if (elapse_time > TMO_PERIOD_SEC):
                    waiting = False
                    result_timeout += 1
                    print_info('timeout! only {} bytes received'.format( len(recv_str) ))

                # Read until endline (non blocking)
                if ser.in_waiting > 0  or  waiting == False:
                    if isinstance(send_str,  str):
                        recv_str = recv_str + ser.read( ser.inWaiting() ).decode('ascii')  # Receiving..
                        if '\n' in recv_str:
                            if (recv_str == send_str):
                                result_ok += 1
                                print_info('ok '+ recv_str)
                            else:
                                result_failed += 1
                                print_info('failed : ' + recv_str)
                            waiting = False
                    else:
                        recv_str = recv_str + ser.read( ser.inWaiting() )  # Actually, 'bytes' object
                        if len(recv_str) >= len(send_str)  or  waiting == False:
                            if compare_send_recv_bytes(send_str, recv_str) == 0:
                                result_ok += 1
                                print_info('ok')
                            else:
                                result_failed += 1
                                print_info('failed')
                            waiting = False

                if waiting:
                    time.sleep(DELAY_CHECK_SEC)

            # Suspend sending thread
            time.sleep(DELAY_INTER_FRAME_SEC)  # sleep between frames
            if send_max > 0:
                send_max -= 1
            else:
                break

            # Clear buffer
            while ser.in_waiting > 0:
                    ser.read( ser.inWaiting() )

        ser.close()

    success = (result_ok * 100) / (result_ok + result_failed + result_timeout)
    print("ok:%d failed:%d timeout:%d success:%.2f%%" % (result_ok, result_failed, result_timeout, success))
