#! /usr/bin/env python

# Answers are compared as strings now. In future we could have regex or other mechanisms.
# Sample course specification:
# {
#    'admins': ['admin@juliabox.org'],
#    'id': 'course id (string)',
#    'problemsets': [
#        {
#            'id': 'problem set id (string)',
#            'questions': ['q1', 'q2', 'q3'],
#            'answers': ['a1', 'a2', 'a3']
#        }
#    ]
#}
#

import datetime
import pytz
import sys
import docker
import json

from cloud.aws import CloudHost
from jbox_util import read_config, LoggerMixin
import db
from db import JBoxUserV2, JBoxDynConfig, JBoxCourseHomework


def upload_course(course):
    course_id = course['id']
    problemsets = []

    for problemset in course['problemsets']:
        problemset_id = problemset['id']
        problemsets.append(problemset_id)
        questions = problemset['questions']
        answers = problemset['answers']
        for idx in range(0, len(questions)):
            question_id = questions[idx]
            answer = answers[idx]
            try:
                JBoxCourseHomework(course_id, problemset_id, question_id, JBoxCourseHomework.ANSWER_KEY, answer=answer, state=JBoxCourseHomework.STATE_CORRECT, create=True)
            except:
                ans = JBoxCourseHomework(course_id, problemset_id, question_id, JBoxCourseHomework.ANSWER_KEY)
                ans.set_answer(answer, JBoxCourseHomework.STATE_CORRECT)
                ans.save()

    for uid in course['admins']:
        user = JBoxUserV2(uid)
        courses_offered = user.get_courses_offered()
        if course['id'] not in courses_offered:
            courses_offered.append(course['id'])
        user.set_courses_offered(courses_offered)
        user.set_role(JBoxUserV2.ROLE_OFFER_COURSES)
        user.save()

    dt = datetime.datetime.now(pytz.utc)
    JBoxDynConfig.set_course(CloudHost.INSTALL_ID, course_id, {
        'problemsets': problemsets,
        'create_time': JBoxUserV2.datetime_to_yyyymmdd(dt)
    })


def get_report(course):
    course_id = course['id']

    for problemset in course['problemsets']:
        problemset_id = problemset['id']
        questions = problemset['questions']
        report = JBoxCourseHomework.get_report(course_id, problemset_id, questions)
        report_file = '_'.join([course_id, problemset_id, 'report'])
        with open(report_file, 'w') as f:
            f.write(json.dumps(report, indent=4))
        print("\treport file %s created" % (report_file,))


def get_answers(course):
    course_id = course['id']

    for problemset in course['problemsets']:
        problemset_id = problemset['id']
        questions = problemset['questions']
        answers = JBoxCourseHomework.get_answers(course_id, problemset_id, questions)
        answers_file = '_'.join([course_id, problemset_id, 'answers'])
        with open(answers_file, 'w') as f:
            f.write(json.dumps(answers, indent=4))
        print("\tanswer file %s created" % (answers_file,))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("\t%s upload <course.cfg>" % (sys.argv[0],))
        print("\t%s report <course.cfg>" % (sys.argv[0],))
        print("\t%s answers <course.cfg>" % (sys.argv[0],))
        exit(1)

    with open(sys.argv[2]) as f:
        uplcourse = eval(f.read())

    dckr = docker.Client()
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

    if sys.argv[1] == "upload":
        upload_course(uplcourse)
    elif sys.argv[1] == "report":
        get_report(uplcourse)
    elif sys.argv[1] == "answers":
        get_answers(uplcourse)

    print("DONE!")
