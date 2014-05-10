# -*- coding: utf-8 -*-
from webtest.debugapp import debug_app
from webtest import http
from unittest import TestCase
import asyncio
import aiowsgi
import socket


class Transport(object):

    _sock = socket.socket()

    def __init__(self):
        self.data = b''
        self.closed = False

    def get_extra_info(self, *args):
        return ('1.1.1.1', 5678)

    def write(self, data):
        self.data += data

    def close(self):
        self.closed = True


class TestHttp(TestCase):

    loop = asyncio.get_event_loop()

    def callFTU(self, **kw):
        kw['host'], kw['port'] = http.get_free_port()
        s = aiowsgi.create_server(asyncio.coroutine(debug_app.__call__),
                                  threads=1, **kw).proto()
        s.connection_made(Transport())
        return s

    def test_get(self):
        p = self.callFTU()
        t = p.transport
        p.data_received(b'GET / HTTP/1.1\r\n\r\n')
        self.loop.run_until_complete(asyncio.sleep(.1))
        self.assertFalse(p.request)
        self.assertIn(b'REQUEST_METHOD: GET', t.data)

    def test_post(self):
        p = self.callFTU()
        t = p.transport
        p.data_received(
            b'POST / HTTP/1.1\r\nContent-Length: 1\r\n\r\nX')
        self.loop.run_until_complete(asyncio.sleep(.1))
        self.assertFalse(p.request)
        self.assertIn(b'REQUEST_METHOD: POST', t.data)
        self.assertIn(b'CONTENT_LENGTH: 1', t.data)

    def test_post_error(self):
        p = self.callFTU(max_request_body_size=1)
        p.data_received(
            b'POST / HTTP/1.1\r\nContent-Length: 1025\r\n\r\nB')
        self.loop.run_until_complete(asyncio.sleep(.1))
        self.assertFalse(p.request)


class Loop(asyncio.AbstractEventLoop):

    def get_debug(self):
        return True

    @asyncio.coroutine
    def create_server(self, *args, **kwargs):
        pass

    @asyncio.coroutine
    def create_unix_server(self, *args, **kwargs):
        pass

    def call_soon(self, callback, *args):
        callback(*args)

    def run_forever(self):
        pass


class TestServe(TestCase):

    def setUp(self):
        loop = asyncio.get_event_loop()
        self.addCleanup(asyncio.set_event_loop, loop)
        asyncio.set_event_loop(Loop())

    def test_serve(self):
        aiowsgi.serve(debug_app)

    def test_serve_unix(self):
        aiowsgi.serve(debug_app, unix_socket='/tmp/sock')

    def test_serve_paste(self):
        aiowsgi.serve_paste(debug_app, {})

    def test_run(self):
        aiowsgi.run(['', 'tests.apps:aioapp'])
