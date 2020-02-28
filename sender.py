from packet import packet
from socket import *
import os
import threading
import time
import sys

#set up variables
packets = []

window_size = 10
window = []
window_location = 0
window_states = [] # 0: not sent, 1: sent not acked, 2: acked
window_lock = threading.Lock()

start_time = 0
end_time = 0

class Timer:
    def __init__(self, interval):
        self.interval = interval
        self.start = time.time()
        self.timer_lock = threading.Lock()
        self.started = False
    
    @staticmethod
    def create_timer():
        return Timer(100)
    
    def check_timer(self):
        current_time = time.time()
        if ((current_time -  self.start)*1000 >= self.interval):
            return True
        else:
            return False
    
    def start_timer(self):
        self.timer_lock.acquire()
        self.start = time.time()
        self.started = True
        self.timer_lock.release()

    def stop_timer(self):
        self.timer_lock.acquire()
        self.started = False
        self.timer_lock.release()

timer = Timer.create_timer()


class myThread(threading.Thread):
    def __init__(self, name, udpSocket, emulator_hostname, emulator_port, sender_port):
        threading.Thread.__init__(self)
        self.name = name
        self.udpSocket = udpSocket
        self.emulator_hostname = emulator_hostname
        self.emulator_port = emulator_port
        self.sender_port = sender_port
    def run(self):
        if self.name == "send":
            send(self.udpSocket, self.emulator_hostname, self.emulator_port)
        elif self.name == "receive":
            receive(self.udpSocket, self.emulator_hostname, self.emulator_port, self.sender_port)
        else:
            print("This should not happen. Something is wrong. -1")
            sys.exit()

# def print_window_seq_num():
#     window_seq_num = []
#     for x in window:
#         window_seq_num.append(x.seq_num)
#     print(window_seq_num)

def resend(udpSocket, emulator_hostname, emulator_port):
    window_lock.acquire()
    current_window_size = len(window)
    for x in range(current_window_size):
        state = window_states[x]
        if state == 1:
            packet_to_send = window[x]
            packet_to_send_encode = packet_to_send.get_udp_data()
            udpSocket.sendto(packet_to_send_encode, (emulator_hostname, int(emulator_port)))
            # print("sender resend: " + str(packet_to_send.seq_num))

            #write into seqnum.log
            file_seqnum = open("seqnum.log", "a")
            file_seqnum.write(str(packet_to_send.seq_num) + "\n")
            file_seqnum.close()
    window_lock.release()


def send(udpSocket, emulator_hostname, emulator_port):
    x_counter = 0
    num_packets = len(packets)
    firstFlag = True
    global window_location
    sequence_number = 0

    while True:
        if timer.started == True and timer.check_timer() == True:
            resend(udpSocket, emulator_hostname, emulator_port)
            # print("after resend: ", window_states)
            # print_window_seq_num()
            timer.start_timer()

        if window_location == num_packets:
            # print("before send eot")
            sequence_number += 1
            packet_eot = packet.create_eot(sequence_number)
            packet_eot_encode = packet_eot.get_udp_data()
            udpSocket.sendto(packet_eot_encode, (emulator_hostname, int(emulator_port)))
            file_seqnum = open("seqnum.log", "a")
            file_seqnum.write(str(packet_eot.seq_num) + "\n")
            file_seqnum.close()
            break

        window_lock.acquire()
        current_window_size = len(window)
        if current_window_size < 10 and x_counter < num_packets:
            if firstFlag == True:
                global start_time
                start_time = time.time()
                firstFlag = False
            packet_to_send = packets[x_counter]
            # print("sender send: " + str(packet_to_send.seq_num))

            sequence_number = packet_to_send.seq_num

            window.append(packet_to_send)
            window_states.append(0)

            packet_to_send_encode = packet_to_send.get_udp_data()
            udpSocket.sendto(packet_to_send_encode, (emulator_hostname, int(emulator_port)))
            window_states[len(window_states)-1] = 1
            # print("after send:", window_states)
            # print_window_seq_num()

            x_counter += 1

            if timer.started == False:
                timer.start_timer()

            #write into seqnum.log
            file_seqnum = open("seqnum.log", "a")
            file_seqnum.write(str(packet_to_send.seq_num) + "\n")
            file_seqnum.close()
        window_lock.release()

def receive(udpSocket, emulator_hostname, emulator_port, sender_port):
    # print("sender_port: ", sender_port)
    # udpSocket.bind(('', int(sender_port)))
    current_seq_num = -1
    first_packet = False
    global window_location
    while True:
        #receive packet from receiver (ACK/EOT)
        data, address = udpSocket.recvfrom(2048)
        packet_received = packet.parse_udp_data(data)

        if current_seq_num != packet_received.seq_num:
            first_packet = True
            current_seq_num = packet_received.seq_num

            if packet_received.type == 0: #receive ACK
                sequence_number_acked = packet_received.seq_num
                # print("sender receive: " + str(sequence_number_acked))

                #write into ack.log
                file_ack = open("ack.log", "a")
                file_ack.write(str(sequence_number_acked) + "\n")
                file_ack.close()

                #update window_states
                window_lock.acquire()
                current_window_size = len(window)
                for x in range(current_window_size):
                    window_states[x] = 2
                    packet_cur = window[x]
                    packet_cur_seq_num = packet_cur.seq_num
                    if packet_cur_seq_num == sequence_number_acked:
                        break
                
                #update window & window_states
                counter = 0
                for x in range(current_window_size):
                    state_cur = window_states[x]
                    if state_cur == 2:
                        counter += 1
                    else:
                        break
                for x in range(counter):
                    window.pop(0)
                    window_states.pop(0)
                    window_location += 1

                # print("after receive: ", window_states)
                # print_window_seq_num()

                #check if need to restart/stop timer
                current_window_size = len(window)
                check_flag = True
                for x in range(current_window_size):
                    if window_states[x] != 2:
                        check_flag = False
                        break
                window_lock.release()
                if check_flag == True:
                    timer.stop_timer()
                else:
                    timer.start_timer()
            elif packet_received.type == 2: #receive EOT
                # print("receive eot")
                global end_time
                end_time = time.time()
                file_ack = open("ack.log", "a")
                file_ack.write(str(packet_received.seq_num) + "\n")
                file_ack.close()
                break
            else:
                print("This should not happen. Something is wrong. -2")
                sys.exit()
        elif first_packet == False:
            continue

def main():
    #get arguments
    emulator_hostname = sys.argv[1]
    emulator_port = sys.argv[2]
    sender_port = sys.argv[3]
    transfer_file = sys.argv[4]

    #create packets
    sequence_number = 0
    file_transfer = open(transfer_file, "r")
    pos = 0
    data_file = file_transfer.read()

    filesize = len(data_file)
    numloop = filesize//500 + 1
    for x in range(numloop):
        if x == numloop-1:
            data = data_file[pos:]
            packet_cur = packet.create_packet(sequence_number, data)
            packets.append(packet_cur)
        else:
            data = data_file[pos:pos+500]
            packet_cur = packet.create_packet(sequence_number, data)
            packets.append(packet_cur)
            sequence_number += 1
            pos = pos + 500

    #clean output file
    open("time.log", "w").close()
    open("ack.log", "w").close()
    open("seqnum.log", "w").close()
    
    #create udp connection to emulator
    udpSocket = socket(AF_INET, SOCK_DGRAM)
    udpSocket.bind(('', int(sender_port)))

    #set up multithread
    thread_send = myThread("send", udpSocket, emulator_hostname, emulator_port, sender_port)
    thread_receive = myThread("receive", udpSocket, emulator_hostname, emulator_port, sender_port)
    thread_send.start()
    thread_receive.start()

    threads = []
    threads.append(thread_send)
    threads.append(thread_receive)
    for t in threads:
        t.join()

    udpSocket.close()

    #write into time.log
    file_time = open("time.log", "a")
    file_time.write(str(end_time*1000 - start_time*1000))
    file_time.close()
    # print("end_time: ", end_time)
    # print("start_time: ", start_time)
    print("transmission time: ", end_time*1000-start_time*1000)

    sys.exit()

if __name__ == "__main__":
    main()