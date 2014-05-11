# -*- coding: utf8 -*-

import pybonjour
import logging
import netifaces
import socket

BASE_RECORDS = {
    'id': None, # device ID
    've': '02',
    'md': 'Chromecast',
    'ic': '/setup/icon.png',
    'ca': '5',
    'fn': None, # device name
    'st': '0',
}

class BonjourServer(object):

    def __init__(self):
        return

    def get_records_string(self, uuid, name):

        records = BASE_RECORDS.copy()
        records['id'] = uuid
        records['fn'] = name

        t = ''
        for k, v in records.iteritems():
            s = '%s=%s' % (k, v)
            t += '%c%s' % (len(s), s)
        return t

    def register_callback(self, sdRef, flags, errorCode, name, regtype, domain):
        print 'inside callback!!!!!1'
        if errorCode == pybonjour.kDNSServiceErr_NoError:
            logging.info('Registered service:')
            logging.info('  name    = %s' % name)
            logging.info('  regtype = %s' % regtype)
            logging.info('  domain  = %s' % domain)
        return

    def start_dns_service(self, name):

        self.dnsservice = pybonjour.DNSServiceCreateConnection()
        for iface in netifaces.interfaces():
            if iface == 'lo0':
                continue
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                for ifaddr in addrs[netifaces.AF_INET]:
                    logging.info('%s.local reacheable at address %s' % (name, ifaddr['addr']))
                    pybonjour.DNSServiceRegisterRecord(self.dnsservice, 
                        pybonjour.kDNSServiceFlagsUnique,
                        interfaceIndex=0,
                        fullname='%s.local' % name,
                        rrtype=pybonjour.kDNSServiceType_A,
                        rrclass=pybonjour.kDNSServiceClass_IN,
                        rdata=socket.inet_aton(ifaddr['addr']))
            #TODO: register IPv6 addresses...
            #if netifaces.AF_INET6 in addrs:
            #    print iface, repr(addrs[netifaces.AF_INET6])

        return

    def start(self, uuid, name):
        logging.info('Starting Bonjour server')

        records_string = self.get_records_string(uuid.replace('-', ''), name)

        self.start_dns_service(name)
        self.bonjour_server = pybonjour.DNSServiceRegister(
            name = name, host = '%s.local' % name, 
            domain='local', regtype = '_googlecast._tcp', port = 8009,
            txtRecord = records_string,
            callBack = self.register_callback)
        
        return

    def shutdown(self):
        logging.info('Stopping Bonjour server')
        self.bonjour_server.close()
        self.dnsservice.close()
        return
