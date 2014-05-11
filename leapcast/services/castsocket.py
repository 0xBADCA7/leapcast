# -*- coding: utf8 -*-

import logging
import SocketServer
import ssl
import threading
import socket
import struct
import json
import requests

from google.protobuf.message import DecodeError

from leapcast.cast_proto import cast_channel_pb2
from leapcast.environment import Environment

class ApplicationDatabase(object):

    available = []
    cached_info = {}

    @classmethod
    def refresh(cls):
        url = 'https://clients3.google.com/cast/chromecast/device/baseconfig'
        resp = requests.get(url=url)

        logging.info('Parsing baseconfig')
        data = json.loads(resp.content.replace(")]}'", ""))

        for app in data['applications']:
            cls.available.append(app['app_id'])
            cls.cached_info[app['app_id']] = app
        for app_id in data['enabled_app_ids']:
            cls.available.append(app_id)

        return

    @classmethod
    def is_available(cls, app_id):
        return app_id in cls.available

    @classmethod
    def info(cls, app_id):
        if app_id not in cls.available:
            logging.info('App not avialable: %s' % (app_id, ))
            return
        if app_id in cls.cached_info.keys():
            return cls.cached_info[app_id]

        url = 'https://clients3.google.com/cast/chromecast/device/app?a=%s' % (app_id, )
        resp = requests.get(url=url)

        logging.info('Parsing information for %s' % (app_id, ))
        data = json.loads(resp.content.replace(")]}'", ""))

        cls.cached_info[app_id] = data
        
        return

class CastSocketHandler(SocketServer.BaseRequestHandler):

    def read_length(self, length):
        data =''

        while len(data) < length:
            s = self.request.read(length - len(data))
            if s == '':
                return ''
            data += s

        return data

    def read_message(self):
        """ hacky loop because messages seem to be sent in several tcp packets. """
        s_length = self.read_length(4)
        if s_length == '':
            return

        length, = struct.unpack('>I', s_length)
        data = self.read_length(length)
        if data == '':
            return

        try:
            msg = cast_channel_pb2.CastMessage()
            msg.ParseFromString(data)
            #print str(msg)
            return msg
        except DecodeError as e:
            print 'decode failed...'
            return

        return

    def write_message(self, msg):
        s_msg = msg.SerializeToString()
        s_length = struct.pack('>I', len(s_msg))
        self.request.write(s_length)
        self.request.write(s_msg)
        return

    def handle(self):

        #sock = socket.create_connection(('192.168.1.118', 8009))
        #ssl_sock = ssl.wrap_socket(sock, do_handshake_on_connect=True, cert_reqs=ssl.CERT_NONE)

        while True:
            msg = self.read_message()
            if not msg:
                print 'client disconnect'
                break

            if msg.namespace == 'urn:x-cast:com.google.cast.tp.deviceauth':
                print 'deviceauth :('
                #self.device_auth(msg)
                break
            elif msg.namespace == 'urn:x-cast:com.google.cast.tp.connection':
                self.tp_connection(msg)
            elif msg.namespace == 'urn:x-cast:com.google.cast.receiver':
                self.receiver(msg)
            else:
                print 'from', repr(self.client_address)
                print str(msg)
                print 'unknown namespace'

        #ssl_sock.close()

        return

    def build_response_base(self, msg):
        resp = cast_channel_pb2.CastMessage()
        resp.protocol_version = msg.protocol_version
        resp.source_id, resp.destination_id = msg.destination_id, msg.source_id
        resp.namespace = msg.namespace
        resp.payload_type = msg.payload_type
        return resp

    def device_auth(self, msg):
        logging.info('device_auth')
        return

    def tp_connection(self, msg):
        """
        protocol_version: CASTV2_1_0
        source_id: "gms_cast_mrp-194"
        destination_id: "receiver-0"
        namespace: "urn:x-cast:com.google.cast.tp.connection"
        payload_type: STRING
        payload_utf8: "{\"origin\":{},\"package\":\"gms_cast_mrp\",\"type\":\"CONNECT\"}"
        """
        #print repr(msg.SerializeToString())
        print 'client connected', msg.payload_utf8

        return

    def receiver(self, msg):
        """
        protocol_version: CASTV2_1_0
        source_id: "gms_cast_mrp-194"
        destination_id: "receiver-0"
        namespace: "urn:x-cast:com.google.cast.receiver"
        payload_type: STRING
        payload_utf8: "{\"type\":\"GET_APP_AVAILABILITY\",\"requestId\":1,\"appId\":[\"E31BF116\"]}"
        """
        print repr(msg.SerializeToString())

        cmd = json.loads(msg.payload_utf8)

        if cmd['type'] == 'GET_APP_AVAILABILITY':
            availability_string = {
                True: 'APP_AVAILABLE',
                False: 'APP_UNAVAILABLE'
            }
            response = {
                'responseType': cmd['type'],
                'requestId': cmd['requestId'],
                'availability': {appId: availability_string[ApplicationDatabase.is_available(appId)] for appId in cmd['appId']}
            }

            resp = self.build_response_base(msg)
            resp.payload_utf8 = json.dumps(response)
            self.write_message(resp)

        return

class CastSocketServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

    allow_reuse_address = True

    def __init__(self):
        SocketServer.TCPServer.__init__(self, ('0.0.0.0', 8009), CastSocketHandler)
        ApplicationDatabase.refresh()
        return

    def get_request(self):
        (socket, addr) = SocketServer.TCPServer.get_request(self)
        logging.info('CastSocket connecion: %s' % repr(addr))
        wrapper = ssl.wrap_socket(socket, server_side=True, do_handshake_on_connect=True, certfile='cacert.pem')
        return wrapper, addr


    def start(self):
        logging.info('Starting CastSocket server')

        # Exit the server thread when the main thread terminates
        self.thread = threading.Thread(target=self.serve_forever)
        self.thread.daemon = True
        self.thread.start()

        return

    def shutdown(self):
        logging.info('Stopping CastSocket server')
        SocketServer.TCPServer.shutdown(self)
        return

