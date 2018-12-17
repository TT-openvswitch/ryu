# Copyright (C) 2016 Nippon Telegraph and Telephone Corporation.
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

import os

def load_tt_flowtable(dirpath):
    schedule_path = os.path.join(dirpath, "schedule")
    adapter_path = os.path.join(dirpath, "adapter")

    flow_schedule_tb = []
    for maindir, subdir, filenames in os.walk(schedule_path):
        for tbfile in filenames:
            port_str, etype_str = \
                os.path.splitext(tbfile)[0].split('_')
            port_num = int(port_str[4:])
            etype_num = 0 if etype_str == "send" else 1  
            tb_path = os.path.join(schedule_path, tbfile)
            with open(tb_path, 'r') as tb:
                flow_num = int(tb.readline())
                for i in range(flow_num):
                    entry = tb.readline()
                    schd_time, period, flow_id, buffer_id, \
                            flow_size = entry.split()
                    flow_schedule_tb.append([port_num, 
                                             etype_num, flow_id, 
                                             schd_time, period, 
                                             buffer_id, flow_size])
    return flow_schedule_tb


def tt_flow_generator(dirpath):
    schedule_path = os.path.join(dirpath, "schedule")
    for maindir, subdir, filenames in os.walk(schedule_path):
        for tbfile in filenames:
            port_str, etype_str = os.path.splitext(tbfile)[0].split('_')
            port_num = int(port_str[4:])
            etype_num = 0 if etype_str == "send" else 1
            tb_path = os.path.join(schedule_path, tbfile)
            with open(tb_path, 'r') as tb:
                flow_num = int(tb.readline())
                for i in range(flow_num):
                    entry = tb.readline()
                    schd_time, period, flow_id, buffer_id, \
                            flow_size = entry.split()
                    yield [port_num, etype_num, int(flow_id),
                           int(schd_time), int(period), 
                           int(buffer_id), int(flow_size)]


if __name__ == '__main__':
    table_path = "/home/mininet/workspace/flowtb/tt_test"
    # flowtb = load_tt_flowtable(table_path)
    entry_generator = tt_flow_generator(table_path)
    for entry in entry_generator:
        print entry

