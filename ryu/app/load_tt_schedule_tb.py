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
    schedule_path = os.path.join(dirpath, "tables")
    # adapter_path = os.path.join(dirpath, "adapter")
    all_tables = []
    for _, subdir, _ in os.walk(schedule_path):
        for switch in subdir:
            flow_tb = []
            switch_path = os.path.join(schedule_path, switch)
            for _, _, filenames in os.walk(switch_path):
                for tbfile in filenames:
                    port_str, etype_str = os.path.splitext(tbfile)[0].split('_')
                    port_num = int(port_str[4:]) + 1
                    etype_num = 0 if etype_str == "send" else 1  
                    tb_path = os.path.join(switch_path, tbfile)
                    with open(tb_path, 'r') as tb:
                        flow_num = int(tb.readline())
                        for i in range(flow_num):
                            entry = tb.readline()
                            schd_time, period, flow_id, buffer_id, \
                                    flow_size = entry.split()
                            flow_tb.append([port_num, 
                                            etype_num, int(flow_id), 
                                            int(schd_time), int(period), 
                                            int(buffer_id), int(flow_size)])
            all_tables.append(flow_tb)
    print(all_tables)
    return all_tables


def tt_table_generator(dirpath):
    schedule_path = os.path.join(dirpath, "tables")
    for _, subdir, _ in os.walk(schedule_path):
        for switch in subdir:
            flow_tb = []
            switch_path = os.path.join(schedule_path, switch)
            for _, _, filenames in os.walk(switch_path):
                for tbfile in filenames:
                    port_str, etype_str = os.path.splitext(tbfile)[0].split('_')
                    port_num = int(port_str[4:]) + 1
                    etype_num = 0 if etype_str == "send" else 1
                    tb_path = os.path.join(switch_path, tbfile)
                    with open(tb_path, 'r') as tb:
                        flow_num = int(tb.readline())
                        for i in range(flow_num):
                            entry = tb.readline()
                            schd_time, period, flow_id, buffer_id, \
                                    flow_size = entry.split()
                            flow_tb.append([port_num, etype_num, int(flow_id),
                                            int(schd_time), int(period), 
                                            int(buffer_id), int(flow_size)])
            yield flow_tb


if __name__ == '__main__':
    table_path = "/home/chenwh/Workspace/data/minimal"
    # all_tables = load_tt_flowtable(table_path)
    all_tables = tt_flow_generator(table_path)
    for table in all_tables:
        print table

