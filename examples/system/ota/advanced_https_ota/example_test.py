import re
import os
import sys
import socket
from threading import Thread
import ssl

try:
    import BaseHTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler
except ImportError:
    import http.server as BaseHTTPServer
    from http.server import SimpleHTTPRequestHandler

try:
    import IDF
except ImportError:
    # this is a test case write with tiny-test-fw.
    # to run test cases outside tiny-test-fw,
    # we need to set environment variable `TEST_FW_PATH`,
    # then get and insert `TEST_FW_PATH` to sys path before import FW module
    test_fw_path = os.getenv("TEST_FW_PATH")
    if test_fw_path and test_fw_path not in sys.path:
        sys.path.insert(0, test_fw_path)
    import IDF

import DUT
import random
import subprocess

server_cert = "-----BEGIN CERTIFICATE-----\n" \
              "MIIDXTCCAkWgAwIBAgIJAP4LF7E72HakMA0GCSqGSIb3DQEBCwUAMEUxCzAJBgNV\n"\
              "BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX\n"\
              "aWRnaXRzIFB0eSBMdGQwHhcNMTkwNjA3MDk1OTE2WhcNMjAwNjA2MDk1OTE2WjBF\n"\
              "MQswCQYDVQQGEwJBVTETMBEGA1UECAwKU29tZS1TdGF0ZTEhMB8GA1UECgwYSW50\n"\
              "ZXJuZXQgV2lkZ2l0cyBQdHkgTHRkMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIB\n"\
              "CgKCAQEAlzfCyv3mIv7TlLkObxunKfCdrJ/zgdANrsx0RBtpEPhV560hWJ0fEin0\n"\
              "nIOMpJSiF9E6QsPdr6Q+eogH4XnOMU9JE+iG743N1dPfGEzJvRlyct/Ck8SswKPC\n"\
              "9+VXsnOdZmUw9y/xtANbURA/TspvPzz3Avv382ffffrJGh7ooOmaZSCZFlSYHLZA\n"\
              "w/XlRr0sSRbLpFGY0gXjaAV8iHHiPDYLy4kZOepjV9U51xi+IGsL4w75zuMgsHyF\n"\
              "3nJeGYHgtGVBrkL0ZKG5udY0wcBjysjubDJC4iSlNiq2HD3fhs7j6CZddV2v845M\n"\
              "lVKNxP0kO4Uj4D8r+5USWC8JKfAwxQIDAQABo1AwTjAdBgNVHQ4EFgQU6OE7ssfY\n"\
              "IIPTDThiUoofUpsD5NwwHwYDVR0jBBgwFoAU6OE7ssfYIIPTDThiUoofUpsD5Nww\n"\
              "DAYDVR0TBAUwAwEB/zANBgkqhkiG9w0BAQsFAAOCAQEAXIlHS/FJWfmcinUAxyBd\n"\
              "/xd5Lu8ykeru6oaUCci+Vk9lyoMMES7lQ+b/00d5x7AcTawkTil9EWpBTPTOTraA\n"\
              "lzJMQhNKmSLk0iIoTtAJtSZgUSpIIozqK6lenxQQDsHbXKU6h+u9H6KZE8YcjsFl\n"\
              "6vL7sw9BVotw/VxfgjQ5OSGLgoLrdVT0z5C2qOuwOgz1c7jNiJhtMdwN+cOtnJp2\n"\
              "fuBgEYyE3eeuWogvkWoDcIA8r17Ixzkpq2oJsdvZcHZPIZShPKW2SHUsl98KDemu\n"\
              "y0pQyExmQUbwKE4vbFb9XuWCcL9XaOHQytyszt2DeD67AipvoBwVU7/LBOvqnsmy\n"\
              "hA==\n"\
              "-----END CERTIFICATE-----\n"

server_key = "-----BEGIN PRIVATE KEY-----\n"\
             "MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCXN8LK/eYi/tOU\n"\
             "uQ5vG6cp8J2sn/OB0A2uzHREG2kQ+FXnrSFYnR8SKfScg4yklKIX0TpCw92vpD56\n"\
             "iAfhec4xT0kT6Ibvjc3V098YTMm9GXJy38KTxKzAo8L35Veyc51mZTD3L/G0A1tR\n"\
             "ED9Oym8/PPcC+/fzZ999+skaHuig6ZplIJkWVJgctkDD9eVGvSxJFsukUZjSBeNo\n"\
             "BXyIceI8NgvLiRk56mNX1TnXGL4gawvjDvnO4yCwfIXecl4ZgeC0ZUGuQvRkobm5\n"\
             "1jTBwGPKyO5sMkLiJKU2KrYcPd+GzuPoJl11Xa/zjkyVUo3E/SQ7hSPgPyv7lRJY\n"\
             "Lwkp8DDFAgMBAAECggEAfBhAfQE7mUByNbxgAgI5fot9eaqR1Nf+QpJ6X2H3KPwC\n"\
             "02sa0HOwieFwYfj6tB1doBoNq7i89mTc+QUlIn4pHgIowHO0OGawomeKz5BEhjCZ\n"\
             "4XeLYGSoODary2+kNkf2xY8JTfFEcyvGBpJEwc4S2VyYgRRx+IgnumTSH+N5mIKZ\n"\
             "SXWNdZIuHEmkwod+rPRXs6/r+PH0eVW6WfpINEbr4zVAGXJx2zXQwd2cuV1GTJWh\n"\
             "cPVOXLu+XJ9im9B370cYN6GqUnR3fui13urYbnWnEf3syvoH/zuZkyrVChauoFf8\n"\
             "8EGb74/HhXK7Q2s8NRakx2c7OxQifCbcy03liUMmyQKBgQDFAob5B/66N4Q2cq/N\n"\
             "MWPf98kYBYoLaeEOhEJhLQlKk0pIFCTmtpmUbpoEes2kCUbH7RwczpYko8tlKyoB\n"\
             "6Fn6RY4zQQ64KZJI6kQVsjkYpcP/ihnOY6rbds+3yyv+4uPX7Eh9sYZwZMggE19M\n"\
             "CkFHkwAjiwqhiiSlUxe20sWmowKBgQDEfx4lxuFzA1PBPeZKGVBTxYPQf+DSLCre\n"\
             "ZFg3ZmrxbCjRq1O7Lra4FXWD3dmRq7NDk79JofoW50yD8wD7I0B7opdDfXD2idO8\n"\
             "0dBnWUKDr2CAXyoLEINce9kJPbx4kFBQRN9PiGF7VkDQxeQ3kfS8CvcErpTKCOdy\n"\
             "5wOwBTwJdwKBgDiTFTeGeDv5nVoVbS67tDao7XKchJvqd9q3WGiXikeELJyuTDqE\n"\
             "zW22pTwMF+m3UEAxcxVCrhMvhkUzNAkANHaOatuFHzj7lyqhO5QPbh4J3FMR0X9X\n"\
             "V8VWRSg+jA/SECP9koOl6zlzd5Tee0tW1pA7QpryXscs6IEhb3ns5R2JAoGAIkzO\n"\
             "RmnhEOKTzDex611f2D+yMsMfy5BKK2f4vjLymBH5TiBKDXKqEpgsW0huoi8Gq9Uu\n"\
             "nvvXXAgkIyRYF36f0vUe0nkjLuYAQAWgC2pZYgNLJR13iVbol0xHJoXQUHtgiaJ8\n"\
             "GLYFzjHQPqFMpSalQe3oELko39uOC1CoJCHFySECgYBeycUnRBikCO2n8DNhY4Eg\n"\
             "9Y3oxcssRt6ea5BZwgW2eAYi7/XqKkmxoSoOykUt3MJx9+EkkrL17bxFSpkj1tvL\n"\
             "qvxn7egtsKjjgGNAxwXC4MwCvhveyUQQxtQb8AqGrGqo4jEEN0L15cnP38i2x1Uo\n"\
             "muhfskWf4MABV0yTUaKcGg==\n"\
             "-----END PRIVATE KEY-----\n"


def get_my_ip():
    s1 = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s1.connect(("8.8.8.8", 80))
    my_ip = s1.getsockname()[0]
    s1.close()
    return my_ip


def get_server_status(host_ip, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_status = sock.connect_ex((host_ip, port))
    sock.close()
    if server_status == 0:
        return True
    return False


def create_file(server_file, file_data):
    with open(server_file, "w+") as file:
        file.write(file_data)


def get_ca_cert(ota_image_dir):
    os.chdir(ota_image_dir)
    server_file = os.path.join(ota_image_dir, "server_cert.pem")
    create_file(server_file, server_cert)

    key_file = os.path.join(ota_image_dir, "server_key.pem")
    create_file(key_file, server_key)
    return server_file, key_file


def start_https_server(ota_image_dir, server_ip, server_port):
    server_file, key_file = get_ca_cert(ota_image_dir)
    httpd = BaseHTTPServer.HTTPServer((server_ip, server_port),
                                      SimpleHTTPRequestHandler)

    httpd.socket = ssl.wrap_socket(httpd.socket,
                                   keyfile=key_file,
                                   certfile=server_file, server_side=True)
    httpd.serve_forever()


def start_chunked_server(ota_image_dir, server_port):
    server_file, key_file = get_ca_cert(ota_image_dir)
    chunked_server = subprocess.Popen(["openssl", "s_server", "-WWW", "-key", key_file, "-cert", server_file, "-port", str(server_port)])
    return chunked_server


def redirect_handler_factory(url):
    """
    Returns a request handler class that redirects to supplied `url`
    """
    class RedirectHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            print("Sending resp, URL: " + url)
            self.send_response(301)
            self.send_header('Location', url)
            self.end_headers()

    return RedirectHandler


def start_redirect_server(ota_image_dir, server_ip, server_port, redirection_port):
    os.chdir(ota_image_dir)
    server_file, key_file = get_ca_cert(ota_image_dir)
    redirectHandler = redirect_handler_factory("https://" + server_ip + ":" + str(redirection_port) + "/advanced_https_ota.bin")

    httpd = BaseHTTPServer.HTTPServer((server_ip, server_port),
                                      redirectHandler)

    httpd.socket = ssl.wrap_socket(httpd.socket,
                                   keyfile=key_file,
                                   certfile=server_file, server_side=True)
    httpd.serve_forever()


@IDF.idf_example_test(env_tag="Example_WIFI")
def test_examples_protocol_advanced_https_ota_example(env, extra_data):
    """
    This is a positive test case, which downloads complete binary file multiple number of times.
    Number of iterations can be specified in variable iterations.
    steps: |
      1. join AP
      2. Fetch OTA image over HTTPS
      3. Reboot with the new OTA image
    """
    dut1 = env.get_dut("advanced_https_ota_example", "examples/system/ota/advanced_https_ota")
    # Number of iterations to validate OTA
    iterations = 3
    server_port = 8001
    # File to be downloaded. This file is generated after compilation
    bin_name = "advanced_https_ota.bin"
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, bin_name)
    bin_size = os.path.getsize(binary_file)
    IDF.log_performance("advanced_https_ota_bin_size", "{}KB".format(bin_size // 1024))
    IDF.check_performance("advanced_https_ota_bin_size", bin_size // 1024)
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, server_port) is False):
        thread1 = Thread(target=start_https_server, args=(dut1.app.binary_path, host_ip, server_port))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    for i in range(iterations):
        dut1.expect("Loaded app from partition at offset", timeout=30)
        try:
            ip_address = dut1.expect(re.compile(r" sta ip: ([^,]+),"), timeout=30)
            print("Connected to AP with IP: {}".format(ip_address))
        except DUT.ExpectTimeout:
            raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
            thread1.close()
        dut1.expect("Connected to WiFi network! Attempting to connect to server...", timeout=30)

        print("writing to device: {}".format("https://" + host_ip + ":" + str(server_port) + "/" + bin_name))
        dut1.write("https://" + host_ip + ":" + str(server_port) + "/" + bin_name)
        dut1.expect("Loaded app from partition at offset", timeout=60)
        dut1.expect("Connected to WiFi network! Attempting to connect to server...", timeout=30)
        dut1.reset()


@IDF.idf_example_test(env_tag="Example_WIFI")
def test_examples_protocol_advanced_https_ota_example_truncated_bin(env, extra_data):
    """
    Working of OTA if binary file is truncated is validated in this test case.
    Application should return with error message in this case.
    steps: |
      1. join AP
      2. Generate truncated binary file
      3. Fetch OTA image over HTTPS
      4. Check working of code if bin is truncated
    """
    dut1 = env.get_dut("advanced_https_ota_example", "examples/system/ota/advanced_https_ota")
    server_port = 8001
    # Original binary file generated after compilation
    bin_name = "advanced_https_ota.bin"
    # Truncated binary file to be generated from original binary file
    truncated_bin_name = "truncated.bin"
    # Size of truncated file to be grnerated. This value can range from 288 bytes (Image header size) to size of original binary file
    # truncated_bin_size is set to 64000 to reduce consumed by the test case
    truncated_bin_size = 64000
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, bin_name)
    f = open(binary_file, "r+")
    fo = open(os.path.join(dut1.app.binary_path, truncated_bin_name), "w+")
    fo.write(f.read(truncated_bin_size))
    fo.close()
    f.close()
    binary_file = os.path.join(dut1.app.binary_path, truncated_bin_name)
    bin_size = os.path.getsize(binary_file)
    IDF.log_performance("advanced_https_ota_bin_size", "{}KB".format(bin_size // 1024))
    IDF.check_performance("advanced_https_ota_bin_size", bin_size // 1024)
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, server_port) is False):
        thread1 = Thread(target=start_https_server, args=(dut1.app.binary_path, host_ip, server_port))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    dut1.expect("Loaded app from partition at offset", timeout=30)
    try:
        ip_address = dut1.expect(re.compile(r" sta ip: ([^,]+),"), timeout=30)
        print("Connected to AP with IP: {}".format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
    dut1.expect("Connected to WiFi network! Attempting to connect to server...", timeout=30)

    print("writing to device: {}".format("https://" + host_ip + ":" + str(server_port) + "/" + truncated_bin_name))
    dut1.write("https://" + host_ip + ":" + str(server_port) + "/" + truncated_bin_name)
    dut1.expect("Image validation failed, image is corrupted", timeout=30)
    os.remove(binary_file)


@IDF.idf_example_test(env_tag="Example_WIFI")
def test_examples_protocol_advanced_https_ota_example_truncated_header(env, extra_data):
    """
    Working of OTA if headers of binary file are truncated is vaildated in this test case.
    Application should return with error message in this case.
    steps: |
      1. join AP
      2. Generate binary file with truncated headers
      3. Fetch OTA image over HTTPS
      4. Check working of code if headers are not sent completely
    """
    dut1 = env.get_dut("advanced_https_ota_example", "examples/system/ota/advanced_https_ota")
    server_port = 8001
    # Original binary file generated after compilation
    bin_name = "advanced_https_ota.bin"
    # Truncated binary file to be generated from original binary file
    truncated_bin_name = "truncated_header.bin"
    # Size of truncated file to be grnerated. This value should be less than 288 bytes (Image header size)
    truncated_bin_size = 180
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, bin_name)
    f = open(binary_file, "r+")
    fo = open(os.path.join(dut1.app.binary_path, truncated_bin_name), "w+")
    fo.write(f.read(truncated_bin_size))
    fo.close()
    f.close()
    binary_file = os.path.join(dut1.app.binary_path, truncated_bin_name)
    bin_size = os.path.getsize(binary_file)
    IDF.log_performance("advanced_https_ota_bin_size", "{}KB".format(bin_size // 1024))
    IDF.check_performance("advanced_https_ota_bin_size", bin_size // 1024)
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, server_port) is False):
        thread1 = Thread(target=start_https_server, args=(dut1.app.binary_path, host_ip, server_port))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    dut1.expect("Loaded app from partition at offset", timeout=30)
    try:
        ip_address = dut1.expect(re.compile(r" sta ip: ([^,]+),"), timeout=30)
        print("Connected to AP with IP: {}".format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
    dut1.expect("Connected to WiFi network! Attempting to connect to server...", timeout=30)

    print("writing to device: {}".format("https://" + host_ip + ":" + str(server_port) + "/" + truncated_bin_name))
    dut1.write("https://" + host_ip + ":" + str(server_port) + "/" + truncated_bin_name)
    dut1.expect("advanced_https_ota_example: esp_https_ota_read_img_desc failed", timeout=30)
    os.remove(binary_file)


@IDF.idf_example_test(env_tag="Example_WIFI")
def test_examples_protocol_advanced_https_ota_example_random(env, extra_data):
    """
    Working of OTA if random data is added in binary file are validated in this test case.
    Magic byte verification should fail in this case.
    steps: |
      1. join AP
      2. Generate random binary image
      3. Fetch OTA image over HTTPS
      4. Check working of code for random binary file
    """
    dut1 = env.get_dut("advanced_https_ota_example", "examples/system/ota/advanced_https_ota")
    server_port = 8001
    # Random binary file to be generated
    random_bin_name = "random.bin"
    # Size of random binary file. 32000 is choosen, to reduce the time required to run the test-case
    random_bin_size = 32000
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, random_bin_name)
    fo = open(binary_file, "w+")
    # First byte of binary file is always set to zero. If first byte is generated randomly,
    # in some cases it may generate 0xE9 which will result in failure of testcase.
    fo.write(str(0))
    for i in range(random_bin_size - 1):
        fo.write(str(random.randrange(0,255,1)))
    fo.close()
    bin_size = os.path.getsize(binary_file)
    IDF.log_performance("advanced_https_ota_bin_size", "{}KB".format(bin_size // 1024))
    IDF.check_performance("advanced_https_ota_bin_size", bin_size // 1024)
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, server_port) is False):
        thread1 = Thread(target=start_https_server, args=(dut1.app.binary_path, host_ip, server_port))
        thread1.daemon = True
        thread1.start()
    dut1.start_app()
    dut1.expect("Loaded app from partition at offset", timeout=30)
    try:
        ip_address = dut1.expect(re.compile(r" sta ip: ([^,]+),"), timeout=30)
        print("Connected to AP with IP: {}".format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
    dut1.expect("Connected to WiFi network! Attempting to connect to server...", timeout=30)

    print("writing to device: {}".format("https://" + host_ip + ":" + str(server_port) + "/" + random_bin_name))
    dut1.write("https://" + host_ip + ":" + str(server_port) + "/" + random_bin_name)
    dut1.expect("esp_ota_ops: OTA image has invalid magic byte", timeout=10)
    os.remove(binary_file)


@IDF.idf_example_test(env_tag="Example_WIFI")
def test_examples_protocol_advanced_https_ota_example_chunked(env, extra_data):
    """
    This is a positive test case, which downloads complete binary file multiple number of times.
    Number of iterations can be specified in variable iterations.
    steps: |
      1. join AP
      2. Fetch OTA image over HTTPS
      3. Reboot with the new OTA image
    """
    dut1 = env.get_dut("advanced_https_ota_example", "examples/system/ota/advanced_https_ota")
    # File to be downloaded. This file is generated after compilation
    bin_name = "advanced_https_ota.bin"
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, bin_name)
    bin_size = os.path.getsize(binary_file)
    IDF.log_performance("advanced_https_ota_bin_size", "{}KB".format(bin_size // 1024))
    IDF.check_performance("advanced_https_ota_bin_size", bin_size // 1024)
    # start test
    host_ip = get_my_ip()
    chunked_server = start_chunked_server(dut1.app.binary_path, 8070)
    dut1.start_app()
    dut1.expect("Loaded app from partition at offset", timeout=30)
    try:
        ip_address = dut1.expect(re.compile(r" sta ip: ([^,]+),"), timeout=30)
        print("Connected to AP with IP: {}".format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
    dut1.expect("Connected to WiFi network! Attempting to connect to server...", timeout=30)

    print("writing to device: {}".format("https://" + host_ip + ":8070/" + bin_name))
    dut1.write("https://" + host_ip + ":8070/" + bin_name)
    dut1.expect("Loaded app from partition at offset", timeout=60)
    dut1.expect("Connected to WiFi network! Attempting to connect to server...", timeout=30)
    chunked_server.kill()
    os.remove(os.path.join(dut1.app.binary_path, "server_cert.pem"))
    os.remove(os.path.join(dut1.app.binary_path, "server_key.pem"))


@IDF.idf_example_test(env_tag="Example_WIFI")
def test_examples_protocol_advanced_https_ota_example_redirect_url(env, extra_data):
    """
    This is a positive test case, which starts a server and a redirection server.
    Redirection server redirects http_request to different port
    steps: |
      1. join AP
      2. Fetch OTA image over HTTPS
      3. Reboot with the new OTA image
    """
    dut1 = env.get_dut("advanced_https_ota_example", "examples/system/ota/advanced_https_ota")
    server_port = 8001
    # Port to which the request should be redirecetd
    redirection_server_port = 8081
    # File to be downloaded. This file is generated after compilation
    bin_name = "advanced_https_ota.bin"
    # check and log bin size
    binary_file = os.path.join(dut1.app.binary_path, bin_name)
    bin_size = os.path.getsize(binary_file)
    IDF.log_performance("advanced_https_ota_bin_size", "{}KB".format(bin_size // 1024))
    IDF.check_performance("advanced_https_ota_bin_size", bin_size // 1024)
    # start test
    host_ip = get_my_ip()
    if (get_server_status(host_ip, server_port) is False):
        thread1 = Thread(target=start_https_server, args=(dut1.app.binary_path, host_ip, server_port))
        thread1.daemon = True
        thread1.start()
    thread2 = Thread(target=start_redirect_server, args=(dut1.app.binary_path, host_ip, redirection_server_port, server_port))
    thread2.daemon = True
    thread2.start()
    dut1.start_app()
    dut1.expect("Loaded app from partition at offset", timeout=30)
    try:
        ip_address = dut1.expect(re.compile(r" sta ip: ([^,]+),"), timeout=30)
        print("Connected to AP with IP: {}".format(ip_address))
    except DUT.ExpectTimeout:
        raise ValueError('ENV_TEST_FAILURE: Cannot connect to AP')
        thread1.close()
        thread2.close()
    dut1.expect("Connected to WiFi network! Attempting to connect to server...", timeout=30)

    print("writing to device: {}".format("https://" + host_ip + ":" + str(redirection_server_port) + "/" + bin_name))
    dut1.write("https://" + host_ip + ":" + str(redirection_server_port) + "/" + bin_name)
    dut1.expect("Loaded app from partition at offset", timeout=60)
    dut1.expect("Connected to WiFi network! Attempting to connect to server...", timeout=30)
    dut1.reset()


if __name__ == '__main__':
    test_examples_protocol_advanced_https_ota_example()
    test_examples_protocol_advanced_https_ota_example_chunked()
    test_examples_protocol_advanced_https_ota_example_redirect_url()
    test_examples_protocol_advanced_https_ota_example_truncated_bin()
    test_examples_protocol_advanced_https_ota_example_truncated_header()
    test_examples_protocol_advanced_https_ota_example_random()
