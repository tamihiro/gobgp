# Copyright (C) 2015 Nippon Telegraph and Telephone Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from fabric.api import local
from lib import base
from lib.gobgp import *
from lib.quagga import *
import sys
import os
import time
import nose
from noseplugin import OptionParser, parser_option
from itertools import chain

class GoBGPTestBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        gobgp_ctn_image_name = parser_option.gobgp_image
        base.TEST_PREFIX = parser_option.test_prefix

        g1 = GoBGPContainer(name='g1', asn=65000, router_id='192.168.0.1',
                            ctn_image_name=gobgp_ctn_image_name,
                            log_level=parser_option.gobgp_log_level,
                            zebra=True)
        q1 = QuaggaBGPContainer(name='q1', asn=65001, router_id='192.168.0.2', zebra=True)
        o1 = QuaggaBGPContainer(name='o1', asn=65002, router_id='192.168.0.3')
        o2 = QuaggaBGPContainer(name='o2', asn=65002, router_id='192.168.0.4')

        # preparing the bridge of ipv4
        br01v4 = Bridge(name='br01', subnet='192.168.10.0/24')
        br02v4 = Bridge(name='br02', subnet='192.168.20.0/24')
        br03v4 = Bridge(name='br03', subnet='192.168.30.0/24')

        # preparing the bridge of ipv6
        br01v6 = Bridge(name='br01', subnet='2001:10::/32')
        br02v6 = Bridge(name='br02', subnet='2001:20::/32')
        br03v6 = Bridge(name='br03', subnet='2001:30::/32')

        cls.ctns = [g1, q1, o1, o2]
        cls.gobgps = {'g1': g1}
        cls.quaggas = {'q1': q1}
        cls.others = {'o1': o1, 'o2': o2}
        cls.bridges = {'ipv4': {'br01': br01v4, 'br02': br02v4, 'br03': br03v4},
                       'ipv6': {'br01': br01v6, 'br02': br02v6, 'br03': br03v6}}

    """
      No.1 start up ipv4 containers and check state
           each neighbor is established in ipv4 environment
    """
    def test_01_check_neighbor_established(self):
        g1 = self.gobgps['g1']
        q1 = self.quaggas['q1']
        o1 = self.others['o1']
        o2 = self.others['o2']

        # start up containers of ipv4 environment
        initial_wait_time = max(ctn.run() for ctn in self.ctns)
        time.sleep(initial_wait_time)

        # make ipv4 bridge and set ip to each container
        [self.bridges['ipv4']['br01'].addif(ctn) for ctn in [o1, g1]]
        [self.bridges['ipv4']['br02'].addif(ctn) for ctn in [g1, q1]]
        [self.bridges['ipv4']['br03'].addif(ctn) for ctn in [q1, o2]]

        for _, q in self.quaggas.items():
            g1.add_peer(q)
            q.add_peer(g1)

        g1.wait_for(expected_state=BGP_FSM_ESTABLISHED, peer=q1)

    """
      No.2 check whether the ping is reachable in container
           that have previously beyond the gobpg in ipv4 environment
    """
    def test_02_check_reachablily_beyond_gobgp_from_quagga(self):
        g1 = self.gobgps['g1']
        q1 = self.quaggas['q1']
        o1 = self.others['o1']

        next_hop = g1.ip_addrs[1][1].split('/')[0]
        o1.add_static_route(self.bridges['ipv4']['br01'].subnet, next_hop)
        q1.get_reachablily('192.168.30.2')

    """
      No.3 check whether the ping is reachable in container
           that have previously beyond the quagga in ipv4 environment
    """
    def test_03_check_reachablily_beyond_quagga_from_gobgp(self):
        g1 = self.gobgps['g1']
        q1 = self.quaggas['q1']
        o2 = self.others['o2']

        next_hop = q1.ip_addrs[0][1].split('/')[0]
        o2.add_static_route(self.bridges['ipv4']['br03'].subnet, next_hop)
        g1.get_reachablily('192.168.10.2')

    """
      No.4 start up ipv4 containers and check state
           each neighbor is established in ipv6 environment
    """
    def test_04_check_neighbor_established_v6(self):
        g1 = self.gobgps['g1']
        q1 = self.quaggas['q1']
        o1 = self.others['o1']
        o2 = self.others['o2']

        # stop containers of ipv4 environment
        # and start up containers of ipv6 environment
        [ctn.stop() for ctn in self.ctns]
        initial_wait_time = max(ctn.run() for ctn in self.ctns)
        time.sleep(initial_wait_time)

        # make ipv4 bridge and set ip to each container
        [self.bridges['ipv6']['br01'].addif(ctn) for ctn in [o1, g1]]
        [self.bridges['ipv6']['br02'].addif(ctn) for ctn in [g1, q1]]
        [self.bridges['ipv6']['br03'].addif(ctn) for ctn in [q1, o2]]

        for _, q in self.quaggas.items():
            g1.add_peer(q)
            q.add_peer(g1)

        g1.wait_for(expected_state=BGP_FSM_ESTABLISHED, peer=q1)

    """
      No.5 check whether the ping is reachable in container
           that have previously beyond the gobpg in ipv6 environment
    """
    def test_05_check_reachablily_beyond_gobgp_from_quagga(self):
        g1 = self.gobgps['g1']
        q1 = self.quaggas['q1']
        o1 = self.others['o1']

        next_hop = g1.ip_addrs[1][1].split('/')[0]
        o1.add_static_route(self.bridges['ipv6']['br01'].subnet, next_hop)
        q1.get_reachablily('2001:30::2')

    """
      No.6 check whether the ping is reachable in container
           that have previously beyond the quagga in ipv6 environment
    """
    def test_06_check_reachablily_beyond_quagga_from_gobgp(self):
        g1 = self.gobgps['g1']
        q1 = self.quaggas['q1']
        o2 = self.others['o2']

        next_hop = q1.ip_addrs[0][1].split('/')[0]
        o2.add_static_route(self.bridges['ipv6']['br03'].subnet, next_hop)
        g1.get_reachablily('2001:10::2')


if __name__ == '__main__':
    if os.geteuid() is not 0:
        print "you are not root."
        sys.exit(1)
    output = local("which docker 2>&1 > /dev/null ; echo $?", capture=True)
    if int(output) is not 0:
        print "docker not found"
        sys.exit(1)

    nose.main(argv=sys.argv, addplugins=[OptionParser()],
              defaultTest=sys.argv[0])