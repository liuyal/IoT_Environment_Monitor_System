import os, sys, threading, time, requests, random, argparse, re, datetime
from scapy.layers.inet import IP, UDP
from scapy.sendrecv import send
import socket as socket


def rand_mac():
    a = random.randint(0, 255)
    b = random.randint(0, 255)
    c = random.randint(0, 255)
    d = random.randint(0, 255)
    e = random.randint(0, 255)
    f = random.randint(0, 255)
    return "%02x:%02x:%02x:%02x:%02x:%02x" % (a, b, c, d, e, f)


def udp_listener(thread_id, cv, UDP_IP="0.0.0.0", UDP_PORT=9996, time_out=5):
    global data
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(time_out)
    sock.bind((UDP_IP, UDP_PORT))
    try:
        while True:
            data, address = sock.recvfrom(1024)
            cv.acquire()
            cv.notifyAll()
            cv.release()
            time_stamp = str(datetime.datetime.now().strftime("%H:%M:%S"))
            sys.stdout.write("[" + str(thread_id) + "] " + time_stamp + " Address: " + str(address) + "\tPacket: " + str(data) + "\n")
    except socket.timeout:
        sock.close()


def response_handler(thread_id, time_stamp, src_ip, dst_ip, src_port, dst_port, udp_msg, http_request):
    response = ""
    
    if input_arg.http and http_request != "": 
        response = requests.get(http_request).json()
        sys.stdout.write("[" + str(thread_id) + "] " + time_stamp + " Request: " +http_request + "\n")
        sys.stdout.write("[" + str(thread_id) + "] " + time_stamp + " Response: " + str(response) + "\n")
    
    if input_arg.sql: 
        send(IP(src=src_ip, dst=dst_ip) / UDP(sport=src_port, dport=dst_port) / udp_msg, verbose=False)
        sys.stdout.write("[" + str(thread_id) + "] " + time_stamp + " " + udp_msg.replace("\n", " ") + "\n")


def dummy_node(thread_id, cv, mac, ip="0.0.0.0", host_ip="localhost", port=9996):
    global data
    dst_ip = host_ip
    
    try:
        udp_msg = ("[" + mac + "|on|" + ip + "]\n")
        http_request = "http://" + host_ip + "/IoT_Environment_Monitor_System/backend/php/node_status_check.php?mac=" + mac + "&state=on"
        response_handler(thread_id, str(datetime.datetime.now().strftime("%H:%M:%S")), ip, host_ip, port, port, udp_msg, http_request)
    except Exception as error:
        print(str(error))

    while True:
        try:
            cv.acquire()
            cv.wait()
            cv.release()
            time_stamp = str(datetime.datetime.now().strftime("%H:%M:%S"))
            if "fetch_data" in str(data):
                epoch = int(time.time())
                temp = round(random.uniform(-10, 40), 2)
                hum = round(random.uniform(0, 100), 2)
                udp_msg = "[" + mac + "|data_sent|" + str(epoch) + "|" + str(temp) + "|" + str(hum) + "]\n"
                http_request = "http://" + host_ip + "/IoT_Environment_Monitor_System/backend/php/node_insert_data.php?mac=" + mac + "&time=" + str(epoch) + "&temp=" + str(temp) + "&hum=" + str(hum)
                response_handler(thread_id, time_stamp, ip, dst_ip, port, port, udp_msg, http_request)

            elif "ping" in str(data):
                udp_msg = "[" + mac + "|pong|" + dst_ip + "|" + ip + "]\n"
                http_request = "http://" + host_ip + "/IoT_Environment_Monitor_System/backend/php/node_status_check.php?mac=" + mac + "&state=pong"
                response_handler(thread_id, time_stamp, ip, dst_ip, port, port, udp_msg, http_request)

            elif "reboot" in str(data):
                udp_msg = "[" + mac + "|rebooting]\n"
                response_handler(thread_id, time_stamp, ip, dst_ip, port, port, udp_msg, "")
                time.sleep(2)
                udp_msg = "[" + mac + "|on|" + ip + "]\n"
                http_request = "http://" + host_ip + "/IoT_Environment_Monitor_System/backend/php/node_status_check.php?mac=" + mac + "&state=on"
                response_handler(thread_id, time_stamp, ip, dst_ip, port, port, udp_msg, http_request)

            elif "set_ip" in str(data):
                dst_ip = str(data)[str(data).index("|") + 1:str(data).index("]")]
                udp_msg = "[" + mac + "|ip_set|" + dst_ip + "]\n"
                response_handler(thread_id, time_stamp, ip, dst_ip, port, port, udp_msg, "")

        except Exception as error:
            print(str(error))


def mac_to_int(mac):
    res = re.match('^((?:(?:[0-9a-f]{2}):){5}[0-9a-f]{2})$', mac.lower())
    if res is None: raise ValueError('invalid mac address')
    return int(res.group(0).replace(':', ''), 16)


def int_to_mac(macint):
    if type(macint) != int:
        raise ValueError('invalid integer')
    return ':'.join(['{}{}'.format(a, b) for a, b in zip(*[iter('{:012x}'.format(macint))] * 2)])


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-http', action='store_true', dest="http", default=False, help='HTTP mode')
    parser.add_argument('-sql', action='store_true', dest="sql", default=False, help='SQL mode')
    parser.add_argument('-n', action='store', dest="nodes", default=5, help='Verbose mode')
    input_arg = parser.parse_args()

    try:
        sys.argv[1]
    except:
        parser.print_help()

    HOST_IP = "192.168.1.80"
    HOST_PORT = 9996
    LOCAL_PORT = 9996
    mode = ""
    data = ""

    mac_list = []
    thread_list = []

    n_nodes = int(input_arg.nodes)
    condition = threading.Condition()

    listener = threading.Thread(target=udp_listener, args=(0, condition, "0.0.0.0", LOCAL_PORT, 6000))
    thread_list.append(listener)

    if input_arg.http == False and input_arg.sql == False:
        input_arg.http = True
        input_arg.sql = True
        mode = "HTTP+SQL"
    elif input_arg.http == True and input_arg.sql == False:
        mode = "HTTP"
    elif input_arg.http == False and input_arg.sql == True:
        mode = "SQL"

    for i in range(1, n_nodes + 1): mac_list.append(int_to_mac(i))

    print("\nStarting " + str(n_nodes) + " Dummy Nodes in " + mode + " mode...")

    for i in range(1, n_nodes + 1):
        # random.seed(i)
        # node_mac = rand_mac()
        node_mac = mac_list[i - 1]
        node_ip = "192.168.1." + str(i)
        dummy_node_thread = threading.Thread(target=dummy_node, args=(i, condition, node_mac, node_ip, HOST_IP, HOST_PORT))
        thread_list.append(dummy_node_thread)
        print("Node [" + str(i) + "]: " + node_mac + "|" + node_ip)
    print("")
    try:
        for item in thread_list: item.start()
    except KeyboardInterrupt:
        for item in thread_list: item.join()
        print("KeyboardInterrupt. Stopping script.")
