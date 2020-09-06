import os
import selectors
import socket
import sys


def simple_app(environ, start_response):
    '''a application by define a function'''

    status = '200 OK'
    headers = [('Content-type', 'text/plain; charset=utf-8')]
    start_response(status, headers)
    return ['hello,world\n'.encode('utf-8')]


class IterSimpleApp(object):
    '''iterable class'''

    def __init__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response

    def __iter__(self):
        status = '200 OK'
        response_headers = [
            ('Content-type', 'text/plain; charset=utf-8')
        ]
        self.start_response(status, response_headers)
        yield 'hello,world\n'.encode('utf-8')


class InstSimpleApp(object):
    '''callable instance'''

    def __call__(self, environ, start_response):
        status = '200 OK'
        response_headers = [
            ('Content-type', 'text/plain; charset=utf-8'),
        ]
        start_response(status, response_headers)
        yield 'hello,world\n'.encode('utf-8')


class AuthMiddleware(object):

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        auth = environ.get('wsgi.authentication', None)
        if not auth or auth != 'zosionlee':
            start_response(
                '403 Forbidden',
                [('Content-Type', 'text/plain; charset=utf-8')]
            )
            return [
                'No authentication, forbidden.\n'.encode('utf-8')
            ]
        return self.app(environ, start_response)


selector = selectors.DefaultSelector()


class CustomServer(object):

    def __init__(self, host, port, application):
        self.app = application
        self.host = host
        self.port = port
        self.headers = []
        self.headers_sent = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.start()

    def start(self):
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen()

    def fileno(self):
        return self.sock.fileno()

    def serve_forever(self, interval=1):
        print(f'Server running at {self.host}:{self.port}')
        try:
            selector.register(self, selectors.EVENT_READ)
            while True:
                ready = selector.select(interval)
                if ready:
                    print('handle request...')
                    self._handle_request()
        except Exception as e:
            print(f'Serve Forever Error:{e}')
        finally:
            return

    def _handle_request(self):
        conn, addr = self.sock.accept()
        self._setup(conn)
        try:
            self._handle()
        finally:
            self._finish()

    def setup_environ(self):
        environ = {k: v for k, v in os.environ.items()}
        environ['wsgi.input'] = self.rfile
        environ['wsgi.errors'] = sys.stderr
        environ['wsgi.version'] = (1, 0)
        environ['wsgi.multithread'] = False
        environ['wsgi.multiprocess'] = True
        environ['wsgi.run_once'] = True
        environ['wsgi.url_scheme'] = 'http'
        environ['wsgi.authentication'] = 'zosionlee'
        self.environ = environ

    def start_response(self, status, response_headers, exc_info=None):
        if exc_info:
            print(f'Bad request:{exc_info}')
        self.headers[:] = [status, response_headers]
        return self.write

    def write(self, data):
        if not self.headers:
            raise AssertionError('write() before start_response()')
        elif not self.headers_sent:
            self.headers_sent = True
            status, response_headers = self.headers
            # write response line
            self.wfile.write(f'HTTP/1.0 {status}\r\n'.encode('iso-8859-1'))
            for header in response_headers:
                header = ('%s: %s\r\n' % header).encode('utf-8')
                self.wfile.write(header)
            self.wfile.write(('\r\n').encode('utf-8'))  # write response header
        self.wfile.write(data)  # write response body
        self.wfile.flush()

    def finish_response(self):
        try:
            for data in self.result:
                self.write(data)
        except Exception as e:
            print(f'finish response error:{e}')
        finally:
            self.close()

    def _read_request_line(self):
        self.requestline = self.rfile.readline(65537)
        print(f'Recv Request:{self.requestline}')
        if len(self.requestline) > 65536:
            print(f'request too long:{self.requestline}')
            return False
        requestline = str(self.requestline, 'iso-8859-1')
        requestline = requestline.rstrip('\r\n')
        words = requestline.split()  # ['HTTP/1.0' '200' 'OK']
        if len(words) < 3:
            print(f'request error:{self.requestline}')
            return False
        return True

    def _setup(self, conn):
        self.rfile = conn.makefile('rb', -1)
        self.wfile = conn.makefile('wb', 0)

    def close(self):
        try:
            if hasattr(self.result, 'close'):
                self.result.close()
        finally:  # clear environ
            self.result = self.environ = None
            self.headers = []
            self.headers_sent = False

    def _handle(self):
        try:
            if not self._read_request_line():  # request must read, otherwise connection close
                return
            self.setup_environ()
            self.result = self.app(self.environ, self.start_response)
            print('Finish response...')
            self.finish_response()
        except Exception as e:
            print(f'Error when handle request:{e}')
            self.close()

    def _finish(self):
        if not self.wfile.closed:
            try:
                self.wfile.flush()
            except socket.error:
                pass
        self.wfile.close()
        self.rfile.close()


if __name__ == '__main__':
    c = CustomServer('localhost', 8000, AuthMiddleware(simple_app))
    c.serve_forever()
