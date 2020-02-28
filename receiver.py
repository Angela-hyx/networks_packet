from packet import packet
from socket import *
import sys

def main():
    #get arguments
    emulator_hostname = sys.argv[1]
    emulator_port = sys.argv[2]
    receiver_port = sys.argv[3]
    output_file = sys.argv[4]

    #create udp connection to emulator
    udpSocket = socket(AF_INET, SOCK_DGRAM)
    udpSocket.bind(('', int(receiver_port)))

    #set up needed variables
    expected_sequence_number = 0
    current_sequence_number = -1
    first_packet = False

    #clean output file
    open("arrival.log", "w").close()
    open("output.txt", "w").close()

    #receive packet from emulator
    while True:
        udp_data, address = udpSocket.recvfrom(2048)

        packet_received = packet.parse_udp_data(udp_data)
        sequence_number = packet_received.seq_num

        #write into arrival.log
        # print("receiver receives: " + str(sequence_number))
        if packet_received.type == 1:
            file_arrival = open("arrival.log", "a")
            file_arrival.write(str(sequence_number) + "\n")
            file_arrival.close()

        if sequence_number == expected_sequence_number:
            first_packet = True
            if packet_received.type == 1:
                packet_to_send = packet.create_ack(sequence_number)
                packet_to_send_encode = packet_to_send.get_udp_data()
                udpSocket.sendto(packet_to_send_encode, (emulator_hostname, int(emulator_port)))
                # print("receiver ack: " + str(packet_to_send.seq_num))

                current_sequence_number = sequence_number
                expected_sequence_number = (1+sequence_number)%32

                data = packet_received.data
                file_output = open(output_file, "a")
                file_output.write(data)
                file_output.close()
            elif packet_received.type == 2:
                # print("receive eot")
                packet_to_send = packet.create_eot(sequence_number)
                packet_to_send_encode = packet_to_send.get_udp_data()
                udpSocket.sendto(packet_to_send_encode, (emulator_hostname, int(emulator_port)))
                file_arrival = open("arrival.log", "a")
                file_arrival.write(str(packet_to_send.seq_num) + "\n")
                file_arrival.close()
                # print("receiver ack: " + str(packet_to_send.seq_num))

                udpSocket.close()
                sys.exit()
        elif first_packet == False:
            continue
        else:
            packet_to_send = packet.create_ack(current_sequence_number)
            packet_to_send_encode = packet_to_send.get_udp_data()
            udpSocket.sendto(packet_to_send_encode, (emulator_hostname, int(emulator_port)))
            # print("receiver ack: " + str(packet_to_send.seq_num))

if __name__ == "__main__":
    main()
