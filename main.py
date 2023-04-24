import datetime
import json
import mimetypes
import pathlib
import socket
import logging
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote_plus


FRONT_DIR = 'front-init/'
HOST = '0.0.0.0'
HTTP_PORT = 3000
SOCKET_PORT = 5000


class MyHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        url = urlparse(self.path)

        match url.path:
            case '/':
                self.render_template('index.html')
            case '/message.html' | '/message':
                self.render_template('message.html')
            case _:
                file = pathlib.Path(FRONT_DIR + url.path)
                if file.exists():
                    self.send_static(file)
                else:
                    self.render_template('error.html', 404)

    def do_POST(self):

        raw_data = self.rfile.read(int(self.headers['Content-Length']))
        self.send_data_to_socket_server(raw_data)

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        logging.info('Data has been sent')

    def render_template(self, html_page, status_code=200):

        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        path = pathlib.Path(FRONT_DIR + html_page)
        with open(path, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self, file_path, status_code=200):

        self.send_response(status_code)
        mime_type, *rest = mimetypes.guess_type(file_path)

        if mime_type:
            self.send_header('Content-type', mime_type)
        else:
            self.send_header('Content-type', 'text/plain')

        self.end_headers()

        with open(file_path, 'rb') as file:
            self.wfile.write(file.read())

    @staticmethod
    def send_data_to_socket_server(data):
        socket_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socket_client.sendto(data, (HOST, SOCKET_PORT))
        socket_client.close()


def run_socket_server(ip=HOST, port=SOCKET_PORT):
    logging.info('Socket server started!')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((ip, port))
    server_socket.recvfrom(1024)

    try:
        while True:
            data = server_socket.recv(1024)
            save_data(data)
    except KeyboardInterrupt:
        logging.info('Socket server stopped!')
    finally:
        server_socket.close()


def save_data(raw_data):
    new_data = unquote_plus(raw_data.decode())
    new_data = {str(datetime.datetime.now()): parse_params(new_data)}
    try:
        path = pathlib.Path(FRONT_DIR + 'storage/data.json')
        if path.exists():
            with open(path, 'r') as file:
                existing_data = json.load(file)
        else:
            existing_data = {}

        existing_data.update(new_data)
        with open(path, 'w') as file:
            json.dump(existing_data, file, indent=2)

    except OSError as err:
        logging.error(f'Failed write data {new_data} with error {err}')
    except ValueError as err:
        logging.error(f'Failed parse data {new_data} with error {err}')

    logging.info('Data obtained!')


def parse_params(params):
    raw_params = params.split('&')
    params = {key: value for key, value in [param.split('=') for param in raw_params]}

    return params


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(threadName)s %(message)s")

    server_http = HTTPServer((HOST, HTTP_PORT), MyHandler)
    thread_http_server = Thread(target=server_http.serve_forever)
    thread_http_server.start()
    logging.info('Socket server started!')

    thread_socket_server = Thread(target=run_socket_server)
    thread_socket_server.start()
