# Derived from os-vif/vif_plug_ovs/ovs.py
#
# Copyright (C) 2017 Netronome Systems, Inc.
# Copyright (C) 2011 Midokura KK
# Copyright (C) 2011 Nicira, Inc
# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from os_vif import objects as obj

from vif_plug_ovs import exception
from vif_plug_ovs import linux_net
from oslo_log import log as logging
from vif_plug_linkvirt_ovs import lv_ovs
from vif_plug_ovs import constants

LOG = logging.getLogger(__name__)


class LinkvirtOvsPlugin(lv_ovs.LV_OvsPlugin):
    """An OS-VIF plugin that extends the OVS plugin with vswitch support.

    """

    def describe(self):
        pp_ovs = obj.host_info.HostPortProfileInfo(
            profile_object_name=obj.vif.VIFPortProfileOpenVSwitch.__name__,
            min_version="1.0",
            max_version="1.0",
        )
        pp_ovs_representor = obj.host_info.HostPortProfileInfo(
            profile_object_name=obj.vif.VIFPortProfileOVSRepresentor.__name__,
            min_version="1.0",
            max_version="1.0",
        )
        return obj.host_info.HostPluginInfo(
            plugin_name='linkvirt_ovs',
            vif_info=[
                obj.host_info.HostVIFInfo(
                    vif_object_name=obj.vif.VIFVHostUser.__name__,
                    min_version="1.0",
                    max_version="1.0",
                    supported_port_profiles=[pp_ovs, pp_ovs_representor]),
            ])

    def __init__(self, config):
        super(LinkvirtOvsPlugin, self).__init__(config)

    def _plug_representor(self, vif, instance_info):
        datapath = self._get_vif_datapath_type(vif,
                                               constants.OVS_DATAPATH_NETDEV)
        self.ovsdb.ensure_ovs_bridge(vif.network.bridge, datapath)
        pci_slot = vif.port_profile.representor_address
        args = []
        kwargs = {}
        representor = linux_net.get_dpdk_representor_port_name(vif.id)
        args = [vif, representor, instance_info]
        kwargs = {'interface_type': constants.OVS_DPDK_INTERFACE_TYPE,
                  'pf_pci': pci_slot,
                  'network_type': vif.network.network_type}

        self._create_vif_port(*args, **kwargs)

    def _unplug_representor(self, vif):
        """Remove port from OVS."""
        representor = linux_net.get_dpdk_representor_port_name(vif.id)

        # The representor interface can't be deleted because it bind the
        # SR-IOV VF, therefore we just need to remove it from tnhe ovs bridge
        # and set the status to down
        self.ovsdb.delete_ovs_vif_port(
            vif.network.bridge, representor, delete_netdev=False)

    def plug(self, vif, instance_info):

        if not hasattr(vif, "port_profile"):
            raise exception.MissingPortProfile()
        if isinstance(vif, obj.vif.VIFVHostUser):
            self._plug_representor(vif, instance_info)

    def unplug(self, vif, instance_info):
        if not hasattr(vif, "port_profile"):
            raise exception.MissingPortProfile()
        if isinstance(vif, obj.vif.VIFVHostUser):
            self._unplug_representor(vif)
