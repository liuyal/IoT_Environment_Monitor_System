import os, sys, time, datetime, requests, subprocess, serial, ipaddress, yaml, random, threading, cProfile, math
from datetime import date, timedelta, timezone
import mysql.connector
from mysql.connector import Error
from mysql.connector import errorcode


def rand_mac():
    a = random.randint(0, 255)
    b = random.randint(0, 255)
    c = random.randint(0, 255)
    d = random.randint(0, 255)
    e = random.randint(0, 255)
    f = random.randint(0, 255)
    return "%02x:%02x:%02x:%02x:%02x:%02x" % (a, b, c, d, e, f)


def db_validate(ip):
    show_tables = "http://" + ip + "/Temperature_System/backend/php/show_tables.php"
    read_table = "http://" + ip + "/Temperature_System/backend/php/select_from_table.php?table="
    main_table = []
    tables = []
    wrong_data = {}
    new_data = {}
    data = {}
    response = requests.get(show_tables)
    table_resp = response.json()["data"]
    for item in table_resp:
        tables.append(item["table"])
        main_table.append(item["table"])
        wrong_data[item["table"]] = []
    tables.remove("nodes")
    tables.remove("daily_avg")
    tables.remove("system_config")
    main_table.remove("nodes")
    main_table.remove("daily_avg")
    main_table.remove("system_config")
    del wrong_data["nodes"], wrong_data["system_config"]

    if len(tables) == 1 and tables[0] == "data":
        try:
            response = requests.get(read_table + "data")
            content = response.json()["data"]
        except Exception as error:
            print("Empty: " + str(error))
            return

    for item in tables:
        data[item] = []
        response = requests.get(read_table + item)
        content = response.json()["data"]
        for each in content: data[item].append(each)
    for line in data:
        temp_list = data[line]
        for item in temp_list:
            date = line.split("_")[0]
            epoch_time = item["time"]
            date_str = datetime.datetime.utcfromtimestamp(int(epoch_time)).strftime("%Y%m%d")
            if date_str != date and line in tables:
                wrong_data[line].append(item)
            if date_str != date and date_str + "_data" not in new_data:
                new_data[date_str + "_data"] = []
                new_data[date_str + "_data"].append(item)
            elif date_str != date and date_str + "_data" in new_data:
                new_data[date_str + "_data"].append(item)
    pop_list = []
    for item in wrong_data:
        if len(wrong_data[item]) == 0: pop_list.append(item)
    for item in pop_list: wrong_data.pop(item, None)
    remove_cmd = []
    add_cmd = []
    for key in wrong_data:
        for i in range(0, len(wrong_data[key])):
            cmd = "DELETE FROM " + key + " WHERE time=" + str(wrong_data[key][i]["time"]) + " AND mac='" + str(wrong_data[key][i]["mac"]) + "';"
            remove_cmd.append(cmd)
    for key in new_data:
        for i in range(0, len(new_data[key])):
            if key not in main_table:
                cmd2 = "CREATE TABLE " + key + "(id INT NOT NULL AUTO_INCREMENT, mac VARCHAR(17), time BIGINT, temp DECIMAL (18, 2), hum DECIMAL (18, 2), PRIMARY KEY (id));"
                add_cmd.append(cmd2)
                main_table.append(key)
            cmd = "INSERT INTO " + key + "(mac,time,temp,hum) VALUES('" + str(new_data[key][i]["mac"]) + "'," + str(new_data[key][i]["time"]) + "," + str(new_data[key][i]["temp"]) + "," + str(new_data[key][i]["hum"]) + ");"
            add_cmd.append(cmd)
    try:
        with open("../server_info.yaml", 'r') as stream:
            try:
                mysql_cred = yaml.safe_load(stream)["mysql_cred"]
            except yaml.YAMLError as exc:
                print(exc)
        connection = mysql.connector.connect(host=mysql_cred["HOST"], database=mysql_cred["DATABASE"], user=mysql_cred["USER"], password=mysql_cred["PASSWORD"], auth_plugin='mysql_native_password')
        cursor = connection.cursor()
        cursor.execute("USE " + str(connection.database) + ";")
        for cmd_item in remove_cmd: cursor.execute(cmd_item)
        for cmd_item in add_cmd: cursor.execute(cmd_item)
        connection.commit()
    except mysql.connector.Error as error:
        print(str(cmd_item) + "\nFailed access table {}".format(error))


def db_reset():
    try:
        with open("../server_info.yaml", 'r') as stream:
            try:
                mysql_cred = yaml.safe_load(stream)["mysql_cred"]
            except yaml.YAMLError as exc:
                print(exc)
        connection = mysql.connector.connect(host=mysql_cred["HOST"], database=mysql_cred["DATABASE"], user=mysql_cred["USER"], password=mysql_cred["PASSWORD"], auth_plugin='mysql_native_password')
        cursor = connection.cursor()
        print("Resetting Database: " +  str(mysql_cred["DATABASE"]))
        try:
            cursor.execute("USE " + str(mysql_cred["DATABASE"]) + ";")
            cursor.execute("DROP DATABASE " + str(mysql_cred["DATABASE"]) + ";")
        except:
            print("Database " + str(mysql_cred["DATABASE"]) + " cannot be accessed or does not exist.")

        cursor.execute("CREATE DATABASE " + str(mysql_cred["DATABASE"]) + ";")
        cursor.execute("USE " + str(mysql_cred["DATABASE"]) + ";")

        cursor.execute("CREATE TABLE data(id INT NOT NULL AUTO_INCREMENT, mac VARCHAR(17), time BIGINT, temp DECIMAL (18, 2), hum DECIMAL (18, 2), PRIMARY KEY (id));")
        cursor.execute("CREATE Table nodes(mac VARCHAR(17), ip CHAR(39), port INT, time_stamp BIGINT, status boolean, display boolean DEFAULT False, PRIMARY KEY (mac));")
        cursor.execute("CREATE Table system_config(host_ip CHAR(39), host_port INT);")
        cursor.execute("CREATE TABLE daily_avg(mac VARCHAR(17), date BIGINT, avg_temp DECIMAL (18, 2), avg_hum DECIMAL (18, 2), PRIMARY KEY (mac, date));")
        connection.commit()
        print("Reset Complete")
    except mysql.connector.Error as error:
        print("Failed access table {}".format(error))



def time_check(ip):
    show_tables = "http://" + ip + "/Temperature_System/backend/php/show_tables.php"
    read_table = "http://" + ip + "/Temperature_System/backend/php/select_from_table.php?table="
    response = requests.get(show_tables)
    table_resp = response.json()["data"]
    tables = []
    for item in table_resp: tables.append(item['table'])
    for date in tables:
        try:
            if date != "nodes" and date != "system_config" and date != "daily_avg":
                response = requests.get(read_table + date)
                try:
                    resp = response.json()["data"]
                    print(date)
                    for item in resp:
                        epoch_time = item["time"]
                        times = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(epoch_time)))
                        print("\t" + str(times))
                except:
                    resp = response.json()["message"]
                    print(resp[0] + "\n" + resp[1])
        except Exception as error:
            print(error)


def time_check_sql():
    try:
        with open("../server_info.yaml", 'r') as stream:
            try:
                mysql_cred = yaml.safe_load(stream)["mysql_cred"]
            except yaml.YAMLError as exc:
                print(exc)
        connection = mysql.connector.connect(host=mysql_cred["HOST"], database=mysql_cred["DATABASE"], user=mysql_cred["USER"], password=mysql_cred["PASSWORD"], auth_plugin='mysql_native_password')
        cursor = connection.cursor()
        cursor.execute("USE " + str(connection.database) + ";")

        cursor.execute("SHOW TABLES;")
        tables = []
        for item in cursor.fetchall():
            if item[0] != "nodes" and item[0] != "daily_avg" and item[0] != "system_config":
                tables.append(item[0])

        for date in tables:
            try:
                cursor.execute("SELECT time FROM " + date + " ORDER BY time ASC;")
                data = cursor.fetchall()
                print(date)
                counter = 1
                for item in data:
                    epoch_time = item[0]
                    times = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(int(epoch_time)))
                    print("\t[" + str(counter) + "] " + str(times))
                    counter += 1
            except Exception as error:
                print(error)

    except mysql.connector.Error as error:
        print("Failed access table {}".format(error))


def add_nodes(mac):
    try:
        with open("../server_info.yaml", 'r') as stream:
            try:
                mysql_cred = yaml.safe_load(stream)["mysql_cred"]
            except yaml.YAMLError as exc:
                print(exc)
        connection = mysql.connector.connect(host=mysql_cred["HOST"], database=mysql_cred["DATABASE"], user=mysql_cred["USER"], password=mysql_cred["PASSWORD"], auth_plugin='mysql_native_password')
        cursor = connection.cursor()
        cursor.execute("USE " + str(connection.database) + ";")
        for item in mac:
            print("Adding node: " + str(item))
            cursor.execute("INSERT INTO nodes values('" + item + "', '0.0.0.0', 0, 0, false, false)")
            connection.commit()
    except mysql.connector.Error as error:
        print("Failed access table {}".format(error))


def http_random_data_generator(mac_list, ip, start_date, end_date, n=50):
    epoch_start = int(datetime.datetime(int(str(start_date)[0:4]), int(str(start_date)[4:6]), int(str(start_date)[6:8]), 0, 0, tzinfo=timezone.utc).timestamp())
    epoch_end = int(datetime.datetime(int(str(end_date)[0:4]), int(str(end_date)[4:6]), int(str(end_date)[6:8]), 0, 0, tzinfo=timezone.utc).timestamp())
    for i in range(0, n):
        # random.seed(i)
        # mac = rand_mac()
        mac = mac_list[random.randint(0, len(mac_list) - 1)]
        epoch = random.randint(epoch_start, epoch_end)
        temp = round(random.uniform(-10, 50), 2)
        hum = round(random.uniform(0, 100), 2)
        insert_req = "http://" + ip + "/Temperature_System/backend/php/insert.php?mac=" + mac + "&time=" + str(epoch) + "&temp=" + str(temp) + "&hum=" + str(hum)
        response = requests.get(insert_req)
        sys.stdout.write("[" + str(i) + "]" + time.strftime('%Y%m%d %H:%M:%S', time.gmtime(epoch)) + " " + str(epoch) + " " + str(temp) + " " + str(hum) + "\n" + insert_req + "\n" + str(response.json()) + "\n")


def http_data_generator(ip, mac, start, end):
    epoch = int(start)
    while epoch < int(end):
        temp = round(random.uniform(-10, 50), 2)
        hum = round(random.uniform(0, 100), 2)
        insert_req = "http://" + ip + "/Temperature_System/backend/php/insert.php?mac=" + mac + "&time=" + str(epoch) + "&temp=" + str(temp) + "&hum=" + str(hum)
        response = requests.get(insert_req)
        sys.stdout.write(time.strftime('%Y%m%d %H:%M:%S', time.gmtime(epoch)) + " " + str(epoch) + " " + str(temp) + " " + str(hum) + "\n" + insert_req + "\n" + str(response.json()) + "\n")
        epoch = epoch + 60


def http_generator_wrapper(ip, mac, start_date, end_date, threads):
    epoch_start = int(datetime.datetime(int(str(start_date)[0:4]), int(str(start_date)[4:6]), int(str(start_date)[6:8]), 0, 0, tzinfo=timezone.utc).timestamp())
    epoch_end = int(datetime.datetime(int(str(end_date)[0:4]), int(str(end_date)[4:6]), int(str(end_date)[6:8]), 0, 0, tzinfo=timezone.utc).timestamp())
    Delta = int(epoch_end - epoch_start)
    n_requests = int(Delta / 60)
    req_per_threads = int(math.ceil(n_requests / threads))

    print("Start:\t" + str(epoch_start))
    print("End:\t" + str(epoch_end))
    print("Delta:\t" + str(Delta))
    print("n_req:\t" + str(n_requests))
    print("n_t:\t" + str(threads))
    print("req/t:\t" + str(req_per_threads))

    list = []
    thread_list = []
    for i in range(0, threads):
        list.append(epoch_start)
        epoch_start = epoch_start + req_per_threads * 60
    list.append(list[-1] + req_per_threads * 60)

    counter = len(list) - 1
    for index in reversed(list):
        if index > epoch_end:
            list.pop(counter)
            counter -= 1

    for i in range(0, threads):
        gen_thread = threading.Thread(target=http_data_generator, args=(ip, mac, list[i], list[i + 1]))
        thread_list.append(gen_thread)
    for item in thread_list: item.start()
    for item in thread_list: item.join()
    print("")


def sql_random_data_generator(mac_list, start_date, end_date, n=50):
    epoch_start = int(datetime.datetime(int(str(start_date)[0:4]), int(str(start_date)[4:6]), int(str(start_date)[6:8]), 0, 0, tzinfo=timezone.utc).timestamp())
    epoch_end = int(datetime.datetime(int(str(end_date)[0:4]), int(str(end_date)[4:6]), int(str(end_date)[6:8]), 0, 0, tzinfo=timezone.utc).timestamp())
    with open("../server_info.yaml", 'r') as stream:
        try:
            mysql_cred = yaml.safe_load(stream)["mysql_cred"]
        except yaml.YAMLError as exc:
            print(exc)
    connection = mysql.connector.connect(host=mysql_cred["HOST"], database=mysql_cred["DATABASE"], user=mysql_cred["USER"], password=mysql_cred["PASSWORD"], auth_plugin='mysql_native_password')
    cursor = connection.cursor()
    for i in range(0, n):
        # random.seed(i)
        # mac = rand_mac()
        mac = mac_list[random.randint(0, len(mac_list) - 1)]
        epoch = random.randint(epoch_start, epoch_end)
        temp = round(random.uniform(-10, 50), 2)
        hum = round(random.uniform(0, 100), 2)
        sql_cmd = "INSERT INTO DATA(mac, time, temp, hum) VALUES('" + mac + "', " + str(epoch) + ", " + str(temp) + ", " + str(hum) + ");"
        cursor.execute(sql_cmd)
        sys.stdout.write("[" + str(i) + "]" + time.strftime('%Y%m%d %H:%M:%S', time.gmtime(epoch)) + " " + str(epoch) + " " + str(temp) + " " + str(hum) + " | " + sql_cmd + "\n")
    connection.commit()


def sql_data_generator(thread_id, connection, mac, start, end):
    epoch = int(start)
    cursor = connection.cursor()
    while epoch < int(end):
        temp = round(random.uniform(-10, 50), 2)
        hum = round(random.uniform(0, 100), 2)
        insert_sql_cmd = "INSERT INTO data(mac, time, temp, hum) VALUES('" + mac + "', " + str(epoch) + ", " + str(temp) + ", " + str(hum) + ")"
        cursor.execute(insert_sql_cmd)
        sys.stdout.write("[" + str(thread_id) + "] " + time.strftime('%Y%m%d %H:%M:%S', time.gmtime(epoch)) + " " + str(epoch) + " " + str(temp) + " " + str(hum) + " | " + insert_sql_cmd + "\n")
        epoch = epoch + 60
    connection.commit()


def sql_generator_wrapper(mac, start_date, end_date, threads):
    epoch_start = int(datetime.datetime(int(str(start_date)[0:4]), int(str(start_date)[4:6]), int(str(start_date)[6:8]), 0, 0, tzinfo=timezone.utc).timestamp())
    epoch_end = int(datetime.datetime(int(str(end_date)[0:4]), int(str(end_date)[4:6]), int(str(end_date)[6:8]), 0, 0, tzinfo=timezone.utc).timestamp())
    Delta = int(epoch_end - epoch_start)
    n_requests = int(Delta / 60)
    req_per_threads = int(math.ceil(n_requests / threads))

    print("Start:\t" + str(epoch_start))
    print("End:\t" + str(epoch_end))
    print("Delta:\t" + str(Delta))
    print("n_req:\t" + str(n_requests))
    print("n_t:\t" + str(threads))
    print("req/t:\t" + str(req_per_threads))

    list = []
    thread_list = []
    for i in range(0, threads):
        list.append(epoch_start)
        epoch_start = epoch_start + req_per_threads * 60
    list.append(list[-1] + req_per_threads * 60)

    counter = len(list) - 1
    for index in reversed(list):
        if index > epoch_end:
            list.pop(counter)
            counter -= 1

    for i in range(0, counter):
        with open("../server_info.yaml", 'r') as stream:
            try:
                mysql_cred = yaml.safe_load(stream)["mysql_cred"]
            except yaml.YAMLError as exc:
                print(exc)
        connection = mysql.connector.connect(host=mysql_cred["HOST"], database=mysql_cred["DATABASE"], user=mysql_cred["USER"], password=mysql_cred["PASSWORD"], auth_plugin='mysql_native_password')
        gen_thread = threading.Thread(target=sql_data_generator, args=(i, connection, mac, list[i], list[i + 1]))
        thread_list.append(gen_thread)

    for item in thread_list: item.start()
    for item in thread_list: item.join()
    print("")


if __name__ == "__main__":

    ip = "localhost"
    mac_list = ["00:00:00:00:00:01", "00:00:00:00:00:02", "00:00:00:00:00:03", "00:00:00:00:00:04", "00:00:00:00:00:05"]

    # db_reset()
    # sql_generator_wrapper(mac="00:00:00:00:00:01", start_date=20191220, end_date=20191230, threads=200)
    # sql_random_data_generator(mac_list, start_date=20191220, end_date=20191230, n=5)
    # http_generator_wrapper(ip="localhost", mac="00:00:00:00:00:01", start_date=20191227, end_date=20191228, threads=100)
    # http_random_data_generator(mac_list, ip, start_date=20191220, end_date=20191230, n=500)
    # add_nodes(mac_list)
    # sql_connector_test()
    # time_check(ip)
    # time_check_sql()
    # db_validate(ip)
