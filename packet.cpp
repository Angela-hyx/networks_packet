#include <iostream>
#include <string.h>
#include <string>
#include <arpa/inet.h>
using namespace std;

class packet{
    const int maxDataLength = 500;
    const int SeqNumModulo = 32;

public:
    int type;
    int seqnum;
    string data;

    packet(int Type, int SeqNum, string strData) {
        if (strData.size() > maxDataLength) {
            cerr<<"data too large (max 500 chars)"<<endl;
        }

        type = Type;
        seqnum = SeqNum % SeqNumModulo;
        data = strData;
    }

    static packet createACK(int SeqNum) {
            return packet(0, SeqNum, "");
    }

    static packet createPacket(int SeqNum, string data) {
            return packet(1, SeqNum, data);
    }

    static packet createEOT(int SeqNum) {
            return packet(2, SeqNum, "");
    }

    void getUDPdata(char* array) {
        int network_type = htonl(type); int network_seqnum = htonl(seqnum); int network_length = htonl(data.size());

        memcpy(array, &network_type, 4);
        memcpy(array + 4, &network_seqnum, 4);
        memcpy(array + 8, &network_length, 4);
        memcpy(array + 12, data.c_str(), data.size());
    }

    static packet parseUDPdata(char* UDPdata) {
        int type, seqnum, length;
        char data_c_str[500];

        memcpy(&type, UDPdata, 4);
        memcpy(&seqnum, UDPdata + 4, 4);
        memcpy(&length, UDPdata + 8, 4);
        type = ntohl(type);
        seqnum = ntohl(seqnum);
        length = ntohl(length);
        strncpy(data_c_str, UDPdata + 12, length);
        string data(data_c_str);

        return packet(type, seqnum, data);
    }
};

int main() {
    packet x = packet::createPacket(12, "DATA DATAAAAAAAAA!!!!!");

    char y[512];
    x.getUDPdata(y);

    packet z = packet::parseUDPdata(y);
    cout<<z.type<<" "<<z.seqnum<<" "<<z.data<<endl;
    return 0;
}
