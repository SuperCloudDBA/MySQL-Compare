# -*- coding: utf-8 -*-
'''
此工具用于对比两个索引导出文件（csv格式）
可以得出两个导出文件的差别
查询主键索引的SQL：
SELECT
table_schema 库名, table_name 表名, index_name 索引名称, index_type 索引类型,NON_UNIQUE 是否唯一,
GROUP_CONCAT(column_name order by SEQ_IN_INDEX) 索引使用的列
FROM
information_schema.STATISTICS
where index_name = 'PRIMARY'  and table_schema not in ('mysql','information_schema')
GROUP BY table_schema , table_name , index_type, index_name,NON_UNIQUE;
查询普通索引的SQL：
SELECT
table_schema 库名, table_name 表名, index_name 索引名称, index_type 索引类型,NON_UNIQUE 是否唯一,
GROUP_CONCAT(column_name order by SEQ_IN_INDEX) 索引使用的列
FROM
information_schema.STATISTICS
where index_name != 'PRIMARY' and table_schema not in ('mysql','information_schema')
GROUP BY table_schema , table_name , index_type, index_name,NON_UNIQUE;

对比小程序优化目标：
1.解决索引对比时区分大小写的问题
2.增加视图结构的对比
3.增加视图、表（information_schema.tables）的对象级别对比
4.生成添加索引的SQL，索引字段部分有问题
5.消除入参文件字符集问题
6.主键索引修改 SQL优化 --格式-ALTER TABLE XXX DROP PRIMARY KEY , ADD PRIMARY KEY (XX,XXX,XXX)
7.输出细化，表、视图的异同、哪些索引需要修改，哪些索引时因为表的异同导致的异同
'''

import argparse
#import datetime
#import jinja2

class ReadFiles:
    def __init__(self):
        pass

    def readftl(self, fa, fb, fl='1'):
        #定义2个空列表用于存储临时数据
        l01 = []
        l02 = []
        #print(fa,fb)
        #打开两个文件
        f01 = open(fa, 'r', True, 'utf-8')
        f02 = open(fb, 'r', True, 'utf-8')
        #过掉第一行（表头）
        if fl == '1':
            print('Pass the first line in the file!')
            f01.readline()
            f02.readline()
        # 填充列表
        while True:
            l01.append(f01.readline()[:-1])
            if not l01[-1]:
                del l01[-1]
                break

        while True:
            l02.append(f02.readline()[:-1])
            if not l02[-1]:
                del l02[-1]
                break

        f01.close()
        f02.close()
        #print(l01)
        #print(l02)
        return {'L01': l01, 'L02': l02}

class FormateRes:
    def __init__(self):
        pass

    def tv_formate(self, ltv):
        dtv = {'TABLE': [], 'VIEW': []} # {'TABLE': ['table_schema.table_name'....], 'VIEW': ['table_schema.table_name'....]}
        for tv in ltv:
            ltv_new = tv.replace('"', '').split(',')
            #print(ltv_new, ltv_new[-1])
            if ltv_new[-1] == 'BASE TABLE':
                #print(ltv_new[-1], ltv_new[0:2])
                dtv['TABLE'].append('.'.join(ltv_new[0:2]))
            elif ltv_new[-1] == 'VIEW':
                #print(ltv_new[-1], ltv_new[0:2])
                dtv['VIEW'].append('.'.join(ltv_new[0:2]))
            else:
                continue
        return dtv

    def tc_formate(self, ltc):
        dtc = {}    #{'schema_name':{'table_name':[col1_info,col2_info....]}}
        for tc in ltc:
            ltc_new = tc.replace('"', '').split(',')
            #print(ltc_new)
            if ltc_new[0] not in dtc.keys():
                dtc[ltc_new[0]] = {}
                dtc[ltc_new[0]][ltc_new[1]] = [':'.join(ltc_new[2:])]  # num:col_name:data_type:null_able:default:extra
            elif ltc_new[1] not in dtc[ltc_new[0]].keys():
                dtc[ltc_new[0]][ltc_new[1]] = [':'.join(ltc_new[2:])]
            else:
                dtc[ltc_new[0]][ltc_new[1]].append(':'.join(ltc_new[2:]))
        return dtc

    def vd_formate(self, lvd):
        dvd = {}    #{'schema_name':{'view_name':'view_definition'}}
        for vd in lvd:
            lvd_new = vd.replace('"', '').split(',')
            #print(lvd_new)
            if lvd_new[0] not in dvd.keys():
                dvd[lvd_new[0]] = {}
                dvd[lvd_new[0]][lvd_new[1]] = lvd_new[2]
            elif lvd_new[1] not in dvd[lvd_new[0]].keys():
                dvd[lvd_new[0]][lvd_new[1]] = lvd_new[2]
        return dvd

    def td_formate(self, ltd):
        dtd = {} #{'schema_name':{'table_name':{'index_name':['type','unique','columns']}}}
        for td in ltd:
            ltd_new = td.replace('"', '').split(',')
            #print(ltd_new)
            if ltd_new[0] not in dtd.keys():
                dtd[ltd_new[0]] = {}
                dtd[ltd_new[0]][ltd_new[1]] = {}
                dtd[ltd_new[0]][ltd_new[1]][ltd_new[2]] = ltd_new[3:]
            elif ltd_new[1] not in dtd[ltd_new[0]].keys():
                dtd[ltd_new[0]][ltd_new[1]] = {}
                dtd[ltd_new[0]][ltd_new[1]][ltd_new[2]] = ltd_new[3:]
            elif ltd_new[2] not in dtd[ltd_new[0]][ltd_new[1]].keys():
                dtd[ltd_new[0]][ltd_new[1]][ltd_new[2]] = ltd_new[3:]
        return dtd

class GetSQL:
    def __init__(self):
        pass

    # def getdelsql (self, delinfo):
    #     l_delsql = []
    #     for l in delinfo:
    #         delsql = 'alter table `%s`.`%s` drop index `%s`;' % (l[0], l[1], l[2])
    #         l_delsql.append(delsql)
    #     return l_delsql
    #
    # def getaddsql (self, crtinfo):
    #     l_crtsql = []
    #     for l in crtinfo:
    #         if l[4] == '0':
    #             crtsql = 'alter table `%s`.`%s` add unique index `%s` (`%s`) using %s;' % \
    #                      (l[0], l[1], l[2], l[5], l[3])
    #         elif l[4] == '1':
    #             crtsql = 'alter table `%s`.`%s` add index `%s` (`%s`) using %s;' % \
    #                      (l[0], l[1], l[2], l[5], l[3])
    #         l_crtsql.append(crtsql)
    #     return l_crtsql

    def get_obj_info(self, l_obj, info_type):
        #将获得的对象名按照schema进行分类
        obj_info = {}
        for obj_fname in l_obj:
            obj_schema, obj_name = obj_fname.split('.')
            if obj_schema not in obj_info.keys():
                obj_info[obj_schema] = [obj_name]
            else:
                obj_info[obj_schema].append(obj_name)
        sqls = []
        for schema_name in obj_info.keys():
            obj_names = "',\n'".join(obj_info[schema_name])
            where_text = f"(table_schema='{schema_name}' and table_name in ('{obj_names}'))\n"
            sqls.append(where_text)
        if info_type == 'col':
            sql_text = f"select table_schema, table_name, ordinal_position, column_name, column_type, is_nullable, \n" \
                       f"IFNULL(column_default,'NULL'),extra from information_schema.columns \n" \
                       f"where {' or '.join(sqls)}"
        elif info_type == 'view':
            sql_text = f"select table_schema,table_name,view_definition from information_schema.views \n" \
                       f"where {' or '.join(sqls)}"
        elif info_type == 'index':
            sql_text = f"SELECT table_schema, table_name, index_name, index_type,NON_UNIQUE, \n" \
                       f"GROUP_CONCAT(column_name order by SEQ_IN_INDEX) FROM information_schema.STATISTICS \n" \
                       f"where {' or '.join(sqls)} " \
                       f"GROUP BY table_schema , table_name , index_type, index_name,NON_UNIQUE"
        return sql_text

class CompareRes:
    def __init__(self):
        pass

    def compare_objs(self, l_obj01, l_obj02):
        # {'TABLE': ['table_schema.table_name'....], 'VIEW': ['table_schema.table_name'....]}
        s_objs01 = set(l_obj01)
        s_objs02 = set(l_obj02)
        s_same = s_objs01 & s_objs02
        s_only01 = s_objs01 - s_same
        s_only02 = s_objs02 - s_same
        return list(s_only01), list(s_same), list(s_only02)

    def compare_cols(self, d_col01, d_col02):
        # {'schema_name':{'table_name':[col1_info,col2_info....]}}
        l_res = {'SAME': [], 'DIFF': []}
        for schema_name in d_col01.keys():
            for table_name in d_col01[schema_name].keys():
                s_col01 = set(d_col01[schema_name][table_name])
                s_col02 = set(d_col02[schema_name][table_name])
                s_same = s_col01 & s_col02
                s_only01 = s_col01 - s_same
                s_only02 = s_col02 - s_same
                if len(s_only01) == 0  and len(s_only02) == 0:
                    l_res['SAME'].append(f"{schema_name}.{table_name}")
                else:
                    l_res['DIFF'].append(f"{schema_name}.{table_name}")
        return l_res

    def compare_vws(self, d_vws01, d_vws02):
        # {'schema_name':{'view_name':'view_definition'}}
        l_res = {'SAME': [], 'DIFF': []}
        for schema_name in d_vws01.keys():
            for view_name in d_vws01[schema_name].keys():
                if d_vws01[schema_name][view_name] == d_vws02[schema_name][view_name]:
                    l_res['SAME'].append(f"{schema_name}.{view_name}")
                else:
                    l_res['DIFF'].append(f"{schema_name}.{view_name}")
        return l_res

    def compare_idxs(self, d_idx01, d_idx02):
        # {'schema_name':{'table_name':{'index_name':['type','unique','columns']}}}
        l_res = {'SAME': [], 'DIFF': [], 'DB01': [], 'DB02': []}
        for schema_name in d_idx01.keys():
            for table_name in d_idx01[schema_name].keys():
                idx01 = set(d_idx01[schema_name][table_name].keys())
                idx02 = set(d_idx02[schema_name][table_name].keys())

                same_idx = idx01 & idx02
                only_idx01 = idx01 - same_idx
                only_idx02 = idx02 - same_idx

                #get diff name idx
                for idx_name in list(only_idx01):
                    l_res['DB01'].append(f"{schema_name}.{table_name}.{idx_name}")
                for idx_name in list(only_idx02):
                    l_res['DB02'].append(f"{schema_name}.{table_name}.{idx_name}")
                #compare same name idex
                for idx_name in list(same_idx):
                    if d_idx01[schema_name][table_name][idx_name] == d_idx02[schema_name][table_name][idx_name]:
                        l_res['SAME'].append(f"{schema_name}.{table_name}.{idx_name}")
                    else:
                        l_res['DIFF'].append(f"{schema_name}.{table_name}.{idx_name}")

        return l_res

class CompareStep:
    def __init__(self):
        pass

    def compare_objs(self, in_param):
        rf = ReadFiles()
        formatelist = FormateRes()
        compare = CompareRes()
        getsql = GetSQL()
        # Read Objs Files
        if in_param['PFL'] == '0':
            all_objs = rf.readftl(in_param['DB01'], in_param['DB02'], fl='0')
        else:
            all_objs = rf.readftl(in_param['DB01'], in_param['DB02'], fl='1')

        # Formate objects list
        l_objs01 = formatelist.tv_formate(all_objs['L01'])
        l_objs02 = formatelist.tv_formate(all_objs['L02'])

        # start compare
        # {'schema_name':{'view_name':'view_definition'}}
        DB01_only_tbl, same_tbl, DB02_only_tbl = compare.compare_objs(l_objs01['TABLE'], l_objs02['TABLE'])
        DB01_only_vw, same_vw, DB02_only_vw = compare.compare_objs(l_objs01['VIEW'], l_objs02['VIEW'])
        # print(DB01_only_tbl, DB02_only_tbl)
        # print(DB01_only_vw, DB02_only_vw)

        # Get Next SQL
        # COL/VIEW info SQL
        get_col_sql = getsql.get_obj_info(same_tbl, 'col')
        get_vw_sql = getsql.get_obj_info(same_vw, 'view')
        return {'RTABLE': [DB01_only_tbl, same_tbl, DB02_only_tbl], 'RVIEW': [DB01_only_vw, same_vw, DB02_only_vw],
                'RNTSQL': [get_col_sql, get_vw_sql]}

    def compare_view(self, in_param):
        rf = ReadFiles()
        formatelist = FormateRes()
        compare = CompareRes()
        #getsql = GetSQL()
        # Read view denfine Files
        if in_param['PFL'] == '0':
            all_vws = rf.readftl(in_param['DB01'], in_param['DB02'], fl='0')
        else:
            all_vws = rf.readftl(in_param['DB01'], in_param['DB02'], fl='1')

        # Formate objects list
        d_vws01 = formatelist.vd_formate(all_vws['L01'])
        d_vws02 = formatelist.vd_formate(all_vws['L02'])

        # start compare
        # {'schema_name':{'view_name':'view_definition'}}
        compare_res = compare.compare_vws(d_vws01, d_vws02)
        # print(compare_res['DIFF'])

        return {'SVIEW': compare_res['SAME'], 'DVIEW': compare_res['DIFF']}

    def compare_tbl(self, in_param):
        rf = ReadFiles()
        formatelist = FormateRes()
        compare = CompareRes()
        getsql = GetSQL()
        # Read col Files
        if in_param['PFL'] == '0':
            all_cols = rf.readftl(in_param['DB01'], in_param['DB02'], fl='0')
        else:
            all_cols = rf.readftl(in_param['DB01'], in_param['DB02'], fl='1')

        # Formate objects list
        d_cols01 = formatelist.tc_formate(all_cols['L01'])
        d_cols02 = formatelist.tc_formate(all_cols['L02'])

        # start compare
        # {'schema_name':{'table_name':[col1_info,col2_info....]}}
        compare_res = compare.compare_cols(d_cols01, d_cols02)
        # print(compare_res['DIFF'])

        # reget index info sql
        get_idx_sql = getsql.get_obj_info(compare_res['SAME'], 'index')

        return {'STABLE': compare_res['SAME'], 'DTABLE': compare_res['DIFF'],
                'IDXSQL': get_idx_sql}

    def compare_idx(self, in_param):
        rf = ReadFiles()
        formatelist = FormateRes()
        compare = CompareRes()
        getsql = GetSQL()
        # Read col Files
        if in_param['PFL'] == '0':
            all_idxs = rf.readftl(in_param['DB01'], in_param['DB02'], fl='0')
        else:
            all_idxs = rf.readftl(in_param['DB01'], in_param['DB02'], fl='1')

        # Formate objects list
        d_idxs01 = formatelist.td_formate(all_idxs['L01'])
        d_idxs02 = formatelist.td_formate(all_idxs['L02'])
        #print(d_idxs01)
        # start compare
        # {'schema_name':{'table_name':[col1_info,col2_info....]}}
        compare_res = compare.compare_idxs(d_idxs01, d_idxs02)
        # print(compare_res['DIFF'])
        return {'SIDX': compare_res['SAME'], 'DIDX': compare_res['DIFF'],
                'JST1': compare_res['DB01'], 'JST2': compare_res['DB02']}

# class GetReport:
#     def __init__(self):
#         pass
#
#     def getrepot(self, info):
#         now_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
#         outfile = '%s%s.html' % ('.\\Report_', now_time)
#         delinfo = info['DB02DEL']
#         addinfo = info['DB02ADD']
#         delsqlinfo = info['DELSQL']
#         addsqlinfo = info['ADDSQL']
#         template_data = '''
# <html lang="zh-CN">
#   <head>
#     <!-- Required meta tags -->
#     <meta charset="gb2312">
#     <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
#
#     <!-- Bootstrap CSS -->
#     <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.5.0/dist/css/bootstrap.min.css" integrity="sha384-9aIt2nRpC12Uk9gS9baDl411NQApFmC26EwAOH8WgZl5MYYxFfc+NcPb1dKGj7Sk" crossorigin="anonymous">
#     <title>My Report</title>
#   </head>
#   <body>
#   <p>
#
#   <button class="btn btn-link btn-block text-left" type="button" data-toggle="collapse" data-target="#table1" aria-expanded="false" aria-controls="table1">
#     目标库需删除的索引
#   </button>
#   </p>
#   <div class="collapse multi-collapse show" id="table1">
#     <div class="card card-body">
# 	<table class="table table-sm">
#       <thead>
#         <tr class="table-success">
#           <th scope="col">库名</th>
#           <th scope="col">表名</th>
#           <th scope="col">索引名</th>
#           <th scope="col">索引类型</th>
# 		  <th scope="col">是否唯一</th>
# 		  <th scope="col">索引列</th>
#         </tr>
#       </thead>
#       <tbody>
# 	  {% for d_idx in db02del %}
# 	    {% if db02del.index(d_idx)%2==0 %}
#         <tr>
# 		{% elif db02del.index(d_idx)%2==1 %}
# 		<tr class="table-active">
# 		{% endif %}
# 		  {% for d_data in d_idx %}
#           <td >{{d_data}}</td>
# 		  {% endfor %}
#         </tr>
#       {% endfor %}
#       </tbody>
#     </table>
#     </div>
# 	<a class="btn btn-link btn-block text-left" data-toggle="collapse" href="#SQL1" role="button" aria-expanded="false" aria-controls="SQL1">
#     点击查看需执行的SQL语句
# 	</a>
# 	<div class="collapse multi-collapse" id="SQL1">
#     <div class="card card-body">
# 	<table class="table table-sm">
# 	    {% for d_sql in delsql %}
# 		{% if delsql.index(d_sql)%2==0 %}
# 		<tr><td class="table-active" >{{d_sql}}</td></tr>
# 		{% elif delsql.index(d_sql)%2==1 %}
# 		<tr><td >{{d_sql}}</td></tr>
# 		{% endif %}
# 		{% endfor %}
# 	</table>
# 	</div>
# 	<a class="btn btn-link btn-block text-right" data-toggle="collapse" href="#SQL1" role="button" aria-expanded="false" aria-controls="SQL1">
# 	收起SQL
# 	</a>
# 	</div>
# 	<a class="btn btn-link btn-block text-right" data-toggle="collapse" href="#table1" role="button" aria-expanded="false" aria-controls="table1">
# 	收起
# 	</a>
#   </div>
# </p>
#   <button class="btn btn-link btn-block text-left" type="button" data-toggle="collapse" data-target="#table2" aria-expanded="false" aria-controls="table2">
#     目标库需增加的索引
#   </button>
#   </p>
#
#   <div class="collapse multi-collapse show" id="table2">
#     <div class="card card-body">
# 	<table class="table table-sm">
#       <thead>
#         <tr class="table-success">
#           <th scope="col">库名</th>
#           <th scope="col">表名</th>
#           <th scope="col">索引名</th>
#           <th scope="col">索引类型</th>
# 		  <th scope="col">是否唯一</th>
# 		  <th scope="col">索引列</th>
#         </tr>
#       </thead>
#       <tbody>
#         {% for a_idx in db02add %}
# 	    {% if db02add.index(a_idx)%2==0 %}
#         <tr>
# 		{% elif db02add.index(a_idx)%2==1 %}
# 		<tr class="table-active">
# 		{% endif %}
# 		  {% for a_data in a_idx %}
#           <td >{{a_data}}</td>
# 		  {% endfor %}
#         </tr>
#       {% endfor %}
#       </tbody>
#     </table>
#     </div>
# 	<a class="btn btn-link btn-block text-left" data-toggle="collapse" href="#SQL2" role="button" aria-expanded="false" aria-controls="SQL2" >
# 	点击查看需执行的SQL语句
# 	</a>
# 	<div class="collapse multi-collapse" id="SQL2">
#     <div class="card card-body">
# 	<table class="table table-sm">
# 	    {% for a_sql in addsql %}
# 		{% if addsql.index(a_sql)%2==0 %}
# 		<tr><td class="table-active" >{{a_sql}}</td></tr>
# 		{% elif addsql.index(a_sql)%2==1 %}
# 		<tr><td >{{a_sql}}</td></tr>
# 		{% endif %}
# 		{% endfor %}
# 	</table>
# 	</div>
# 	<a class="btn btn-link btn-block text-right" data-toggle="collapse" href="#SQL2" role="button" aria-expanded="false" aria-controls="SQL2">
# 	收起SQL
# 	</a>
# 	</div>
# 	<a class="btn btn-link btn-block text-right" data-toggle="collapse" href="#table2" role="button" aria-expanded="false" aria-controls="table2">
# 	收起
# 	</a>
#   </div>
# </p>
#     <!-- Optional JavaScript -->
#     <!-- jQuery first, then Popper.js, then Bootstrap JS -->
#     <script src="https://cdn.jsdelivr.net/npm/jquery@3.5.1/dist/jquery.slim.min.js" integrity="sha384-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38MVBnE+IbbVYUew+OrCXaRkfj" crossorigin="anonymous"></script>
#     <script src="https://cdn.jsdelivr.net/npm/popper.js@1.16.0/dist/umd/popper.min.js" integrity="sha384-Q6E9RHvbIyZFJoft+2mJbHaEWldlvI9IOYy5n3zV9zzTtmI3UksdQRVvoxMfooAo" crossorigin="anonymous"></script>
#     <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.0/dist/js/bootstrap.min.js" integrity="sha384-OgVRvuATP1z7JjHLkuOU7Xw704+h835Lr+6QL9UvYjZE3Ipu6Tp75j7Bh/kR0JKI" crossorigin="anonymous"></script>
#   </body>
# </html>
# '''
#         template = jinja2.Template(template_data)
#         report = template.render(db02del=delinfo,delsql=delsqlinfo,db02add=addinfo,addsql=addsqlinfo)
#         with open(outfile, 'w') as rp:
#             rp.write(report)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='''
根据提供的csv文件得出对比结果
· 提供的文件字符集需utf-8
· 第一行默认为表头，会被忽略
· 该程序会以DB01为标准生成修正DB02的SQL语句
· 暂不提供主键相关的修正SQL
示例：AIA_compare_tool.py  --DB01 E:\MyWork\AIA友邦\\20200507\RDX_IDX.csv --DB02 E:\MyWork\AIA友邦\\20200507\PDB226_IDX.csv
对象对比：
select table_schema,table_name,table_type 
from information_schema.tables 
where table_schema not in ('sys','mysql','information_schema','performance_schema');
主键：
ALTER TABLE `test2` DROP PRIMARY KEY ,ADD PRIMARY KEY ( `id` )
--批量生成删除视图语句
select concat("drop VIEW ",TABLE_SCHEMA,".",TABLE_NAME,";") from information_schema.VIEWS where table_schema in ("xx","xx2");
 
--批量生成创建视图语句
select concat("create DEFINER=`zyadmin_dba`@`%` SQL SECURITY INVOKER VIEW ",TABLE_SCHEMA,".",TABLE_NAME," as ",VIEW_DEFINITION,";") from information_schema.VIEWS where table_schema in ("xx","xx2");
''')
    parser.add_argument("--DB01", help="第一个数据库的csv文件的路径")
    parser.add_argument("--DB02", help="第二个数据库的csv文件的路径")
    parser.add_argument("--PFL", help="Pass First Line 是否跳过csv文件的第一行, 1: 跳过, 0: 不跳过, 默认为1")
    parser.add_argument("--MODE", help="对比模式，现支持 obj: 对象名对比, vw: 视图定义对比, col: 表的列定义对比, \
                                       idx: 表中索引列对比")

args = parser.parse_args()

param = {'DB01': args.DB01,
         'DB02': args.DB02,
         'PFL': args.PFL,
         'MODE': args.MODE}

start_compare = CompareStep()

if param['MODE'].lower() == 'obj':
    # {'RTABLE': [only_tbl1, same_tbl, only_tbl2], 'RVIEW': [only_vw1, same_vw, only_vw2], 'RNTSQL': [col_sql, vw_sql]}
    # select table_schema,table_name,table_type
    # from information_schema.tables
    # where table_schema not in ('information_schema','mysql','performance_schema');
    res = start_compare.compare_objs(param)
elif param['MODE'].lower() == 'vw':
    # {'SVIEW': compare_res['SAME'], 'DVIEW': compare_res['DIFF']}
    res = start_compare.compare_view(param)
elif param['MODE'].lower() == 'col':
    # {'STABLE': compare_res['SAME'], 'DTABLE': compare_res['DIFF'], 'IDXSQL': get_idx_sql}
    res = start_compare.compare_tbl(param)
elif param['MODE'].lower() == 'idx':
    # {'SIDX': compare_res['SAME'], 'DIDX': compare_res['DIFF'],
    # 'JST1': compare_res['BD01'] , 'JST2': compare_res['BD02']}
    res = start_compare.compare_idx(param)
else:
    print('Please input the right parameter!')

print(res['DVIEW'])











