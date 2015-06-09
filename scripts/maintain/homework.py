#! /usr/bin/env python

# Answers are compared as strings now. In future we could have regex or other mechanisms.
# Sample course specification:
# {
#    'admins': ['admin@juliabox.org'],
#    'id': 'course id (string)',
#    'problemsets': [
#        {
#            'id': 'problem set id (string)',
#            'questions': [
#               {
#                   'id': 1,
#                   'ans': 'answer',
#                   'score': 1,
#                   #'nscore': 0,
#                   #'precision': 0.001
#               }
#            ]
#        }
#    ]
#}
#

import sys
import json
import csv

from cloud.aws import CloudHost
from jbox_util import read_config, LoggerMixin
from db import JBoxCourseHomework
from juliabox import db
from juliabox.handlers import HomeworkHandler


def report_as_csv(wfile, perq):
    repwriter = csv.writer(wfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    repwriter.writerow(["student", "question", "answer", "evaluation", "score", "attempts"])
    questions = perq['questions']
    for question in questions:
        question_id = question['id']
        students = question['students']
        for student in students:
            repwriter.writerow([student['id'], question_id, student['answer'], student['evaluation'],
                               student['score'], student['attempts']])

    repwriter.writerow([])
    repwriter.writerow(["student", "score"])
    scores = perq['scores']
    for (student_id, score) in scores.iteritems():
        repwriter.writerow([student_id, score])


def get_report(course, ascsv=False):
    course_id = course['id']

    for problemset in course['problemsets']:
        problemset_id = problemset['id']
        question_set = problemset['questions']
        questions = [q['id'] for q in question_set]
        report = JBoxCourseHomework.get_report(course_id, problemset_id, questions)
        report_file = '_'.join([course_id, problemset_id, 'report'])
        with open(report_file, 'w') as f:
            if ascsv:
                report_as_csv(f, report)
            else:
                f.write(json.dumps(report, indent=4))
        print("\treport file %s created" % (report_file,))


def get_answers(course):
    course_id = course['id']

    for problemset in course['problemsets']:
        problemset_id = problemset['id']
        question_set = problemset['questions']
        questions = [q['id'] for q in question_set]
        answers = JBoxCourseHomework.get_problemset_metadata(course_id, problemset_id, questions, True)
        answers_file = '_'.join([course_id, problemset_id, 'answers'])
        with open(answers_file, 'w') as f:
            f.write(json.dumps(answers, indent=4))
        print("\tanswer file %s created" % (answers_file,))


def print_usage():
    print("Usage:")
    print("\t%s upload <course.cfg>" % (sys.argv[0],))
    print("\t%s report <course.cfg> <as_csv>" % (sys.argv[0],))
    print("\t%s answers <course.cfg>" % (sys.argv[0],))


def process_commands(argv):
    with open(argv[2]) as f:
        uplcourse = eval(f.read())

    cfg = read_config()
    cloud_cfg = cfg['cloud_host']

    LoggerMixin.setup_logger(level=cfg['root_log_level'])
    LoggerMixin.DEFAULT_LEVEL = cfg['jbox_log_level']

    db.configure_db(cfg)

    CloudHost.configure(has_s3=cloud_cfg['s3'],
                        has_dynamodb=cloud_cfg['dynamodb'],
                        has_cloudwatch=cloud_cfg['cloudwatch'],
                        has_autoscale=cloud_cfg['autoscale'],
                        has_route53=cloud_cfg['route53'],
                        has_ebs=cloud_cfg['ebs'],
                        has_ses=cloud_cfg['ses'],
                        scale_up_at_load=cloud_cfg['scale_up_at_load'],
                        scale_up_policy=cloud_cfg['scale_up_policy'],
                        autoscale_group=cloud_cfg['autoscale_group'],
                        route53_domain=cloud_cfg['route53_domain'],
                        region=cloud_cfg['region'],
                        install_id=cloud_cfg['install_id'])

    cmd = argv[1]
    if cmd == "upload":
        HomeworkHandler.upload_course(None, uplcourse)
    elif cmd == "report":
        as_csv = (argv[3] == "csv") if len(argv) > 3 else False
        get_report(uplcourse, as_csv)
    elif cmd == "answers":
        get_answers(uplcourse)
    else:
        print("Unknown option %s" % (cmd,))

    print("DONE!")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        exit(1)
    process_commands(sys.argv)