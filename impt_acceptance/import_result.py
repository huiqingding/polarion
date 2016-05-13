#!/usr/bin/env python

import logging
import sys
import datetime
import time
import base64
import os
import re
import ssl

from collections import OrderedDict
from xml.etree import ElementTree

from pylarion.document import Document
from pylarion.work_item import TestCase
from pylarion.test_run import TestRun

# generate a dictionary of autocase and polarion case
# case_id_dic{'autocase_id','polarioncase_id}
def gen_case_id_dic(dic_file_name):
    case_id_dic = OrderedDict()
    case_id_file = open(dic_file_name)

    for line in case_id_file.readlines():
        line = line.split('\n')[0]
        autocase_id = line.split('=')[0]
        polarioncase_id = line.split('=')[1]
        case_id_dic[autocase_id] = polarioncase_id
    return case_id_dic


# parse the junit xml result file
# get the result after auto cases executed
# for each auto test, get the detailed information:
# autocase name, autocase_id, execution time, error information
# based on the dictionary of autocase and polarion case, get the polarion case id of autocase
def get_junit_test_cases(junit_result_file,case_id_dic):
    root = ElementTree.parse(junit_result_file).getroot()
    testsuites = root.findall('testsuite')

    all_cases = []
    num = 1
    for testsuite in testsuites:
        suite_name = testsuite.get('name')
        testcases = testsuite.findall('testcase')
        for testcase in testcases:
            case = {}
            case['time'] = testcase.get('time')
            case['full_name'] = testcase.get('name')
            case['autocase_id'] = case['full_name'].split('github-autotest-qemu.')[1]
            case['polarioncase_id'] = case_id_dic[case['autocase_id']]
            error_info = testcase.find('error')
            case['result'] = 'passed'
            case['error_info'] = ''
            if error_info is not None:
                case['result'] = 'failed'
                case['error_info'] = error_info.get('message')
            failure_info = testcase.find('failure')
            if failure_info is not None:
                case['result'] = 'failed'
                case['error_info'] = failure_info.get('message')
            all_cases.append(case)

    return all_cases


#create a test run
#for each autocase, create a test record and add this record to the test run
#in the comment of each test record, add the full name of each autocase
def update_test_run(all_cases):
    project_name_name = 'RedHatEnterpriseLinux7'
#    template_name = 'virtkvmqe-x86-acceptance-rhev-auto'
    template_name = 'Empty'
    ISOTIMEFORMAT = '%Y-%m-%d %H-%M-%S'
    testrun_name = 'virtkvmqe-x86-acceptance ' + time.strftime( ISOTIMEFORMAT, time.gmtime( time.time() ) )
    
    # create a test run
    tr = TestRun.create("RedHatEnterpriseLinux7",testrun_name,template_name)
    session = TestCase.session
    session.tx_begin()
    client = session.test_management_client
    for case in all_cases:
       # for each autocase, create a test record
       testcase_record = client.factory.create('tns3:TestRecord')
       testcase_record.testCaseURI = ("subterra:data-service:objects:/default/""RedHatEnterpriseLinux7${WorkItem}%s"%case['polarioncase_id'])
       testcase_record.duration = case['time']
       testcase_record.executed = datetime.datetime.now()
       testcase_result = client.factory.create('tns4:EnumOptionId')
       testcase_result.id = case['result']
       testcase_record.result = testcase_result
       # create a comment for each autocase
       comment_obj = client.factory.create('tns2:Text')
       comment_obj.type = "text/html"
       # add the fullname of a autocase
       content = case['full_name'] + '\n'
       content = content + case['error_info']
       comment_obj.content = '<pre>%s</pre>' % content
       comment_obj.contentLossy = False
       testcase_record.comment = comment_obj
       client.service.addTestRecordToTestRun(tr.uri, testcase_record)
    # update the test run
    session.tx_commit()

# python import_result.py CI_XML_RESULT_FILE MAP_FILE
if __name__ == '__main__':
   
    case_id_dic = gen_case_id_dic(sys.argv[2])
    all_cases = get_junit_test_cases(sys.argv[1],case_id_dic)
    update_test_run(all_cases)
 
