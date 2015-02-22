import datetime
import pytz
import json
from cloud.aws import CloudHost
from jbox_util import unquote
from handlers.handler_base import JBoxHandler
from jbox_container import JBoxContainer
from db import JBoxUserV2, JBoxCourseHomework, JBoxDynConfig


class HomeworkHandler(JBoxHandler):
    def get(self):
        self.log_debug("Homework handler got GET request")
        return self.post()

    def post(self):
        self.log_debug("Homework handler got POST request")
        sessname = unquote(self.get_cookie("sessname"))
        jbox_cookie = self.get_session_cookie()

        if (None == sessname) or (len(sessname) == 0) or (None == jbox_cookie):
            self.log_info("Homework handler got invalid sessname[%r] or cookie[%r]", sessname, jbox_cookie)
            self.send_error()
            return

        user_id = jbox_cookie['u']
        user = JBoxUserV2(user_id)
        is_admin = sessname in self.config("admin_sessnames", []) or user.has_role(JBoxUserV2.ROLE_SUPER)
        course_owner = is_admin or user.has_role(JBoxUserV2.ROLE_OFFER_COURSES)
        cont = JBoxContainer.get_by_name(sessname)
        self.log_info("user_id[%r], is_admin[%r], course_owner[%r]", user_id, is_admin, course_owner)

        if cont is None:
            self.log_info("user_id[%r] container not found", user_id)
            self.send_error()
            return

        courses_offered = user.get_courses_offered()

        if self.handle_if_check(user_id):
            return
        if self.handle_create_course(user_id):
            return
        if self.handle_get_metadata(is_admin, courses_offered):
            return
        if course_owner and self.handle_if_report(user_id, is_admin, courses_offered):
            return

        self.log_error("no handlers found")
        # only AJAX requests responded to
        self.send_error()

    #
    # verify against correct answer
    # if not already answered correctly or mode is submit, update scores and store last submitted answer
    # update attempts if not already answered correctly
    # return valid/invalid, score, last correct answer
    def handle_if_check(self, user_id):
        mode = self.get_argument('mode', None)
        if (mode is None) or ((mode != "check") and (mode != "submit")):
            return False
        self.log_debug("handling check")
        params = self.get_argument('params', None)
        if params is None:
            course = self.get_argument('course', None)
            problemset = self.get_argument('problemset', None)
            question = self.get_argument('question', None)
            answer = self.get_argument('answer', None)
        else:
            params = json.loads(params)
            course = params['course']
            problemset = params['problemset']
            question = params['question']
            answer = params['answer']

        record = (mode == "submit")

        status, score, used_attempts, max_score, max_attempts = \
            JBoxCourseHomework.check_answer(course, problemset, question, user_id, answer, record)
        response = {
            'code': 0,
            'data': {
                'status': int(status),
                'score': float(score),
                'attempts': int(used_attempts),
                'max_score': float(max_score),
                'max_attempts': int(max_attempts)
            }
        }
        self.write(response)
        return True

    def handle_if_report(self, user_id, is_admin, courses_offered):
        mode = self.get_argument('mode', None)
        if (mode is None) or (mode != "report"):
            return False

        self.log_debug("handling report")
        params = self.get_argument('params', None)
        params = json.loads(params)
        course_id = params['course']
        problemset_id = params['problemset']
        question_ids = params['questions'] if 'questions' in params else None
        student_id = params['student'] if 'student' in params else None

        err = None
        if (not is_admin) and (course_id not in courses_offered):
            if student_id is None:
                student_id = user_id
            elif student_id != user_id:
                err = "Course %s not found!" % (course_id,)

        if err is None:
            course = JBoxDynConfig.get_course(CloudHost.INSTALL_ID, course_id)
            if problemset_id not in course['problemsets']:
                err = "Problem set %s not found!" % (problemset_id,)
            if question_ids is None:
                question_ids = course['questions'][problemset_id]

        if err is None:
            report = JBoxCourseHomework.get_report(course_id, problemset_id, question_ids, student_id=student_id)
            code = 0
        else:
            report = err
            code = -1

        response = {'code': code, 'data': report}
        self.write(response)
        return True

    def handle_get_metadata(self, is_admin, courses_offered):
        mode = self.get_argument('mode', None)
        if (mode is None) or (mode != "metadata"):
            return False

        self.log_debug("handling answers")
        params = self.get_argument('params', None)
        params = json.loads(params)
        course_id = params['course']
        problemset_id = params['problemset']
        question_ids = params['questions'] if 'questions' in params else None
        send_answers = True

        if (not is_admin) and (course_id not in courses_offered):
            send_answers = False

        err = None
        course = JBoxDynConfig.get_course(CloudHost.INSTALL_ID, course_id)
        self.log_debug("got course %r", course)
        if problemset_id not in course['problemsets']:
            err = "Problem set %s not found!" % (problemset_id,)
        if question_ids is None:
            question_ids = course['questions'][problemset_id]

        if err is None:
            report = JBoxCourseHomework.get_problemset_metadata(course_id, problemset_id, question_ids, send_answers)
            code = 0
        else:
            report = err
            code = -1

        response = {'code': code, 'data': report}
        self.write(response)
        return True

    @staticmethod
    def upload_course(user_id, course):
        course_id = course['id']

        if (user_id is not None) and (user_id not in course['admins']):
            course['admins'].append(user_id)

        existing_course = JBoxDynConfig.get_course(CloudHost.INSTALL_ID, course_id)
        existing_admins = existing_course['admins'] if existing_course is not None else []
        existing_psets = existing_course['problemsets'] if existing_course is not None else []

        question_list = {}
        if (existing_course is not None) and ('questions' in existing_course):
            question_list = existing_course['questions']

        if (existing_course is not None) and (user_id is not None) and (user_id not in existing_admins):
            return -1

        for pset in course['problemsets']:
            pset_id = pset['id']
            if pset_id not in existing_psets:
                existing_psets.append(pset_id)
            question_ids = [q['id'] for q in pset['questions']]
            question_list[pset_id] = question_ids

        dt = datetime.datetime.now(pytz.utc)
        JBoxDynConfig.set_course(CloudHost.INSTALL_ID, course_id, {
            'admins': course['admins'],
            'problemsets': existing_psets,
            'questions': question_list,
            'create_time': JBoxUserV2.datetime_to_yyyymmdd(dt)
        })

        for problemset in course['problemsets']:
            problemset_id = problemset['id']
            questions = problemset['questions']
            for question in questions:
                question_id = question['id']
                answer = question['ans']
                score = question['score'] if 'score' in question else 0
                attempts = question['attempts'] if 'attempts' in question else 0
                #nscore = question['nscore'] if 'nscore' in question else 0
                try:
                    ans = JBoxCourseHomework(course_id, problemset_id, question_id, JBoxCourseHomework.ANSWER_KEY,
                                             answer=answer, state=JBoxCourseHomework.STATE_CORRECT, create=True)
                except:
                    ans = JBoxCourseHomework(course_id, problemset_id, question_id, JBoxCourseHomework.ANSWER_KEY)
                    ans.set_answer(answer, JBoxCourseHomework.STATE_CORRECT)
                ans.set_score(score)
                ans.set_attempts(attempts)
                ans.save()

        for uid in course['admins']:
            user = JBoxUserV2(uid)
            courses_offered = user.get_courses_offered()
            if course['id'] not in courses_offered:
                courses_offered.append(course['id'])
            user.set_courses_offered(courses_offered)
            user.set_role(JBoxUserV2.ROLE_OFFER_COURSES)
            user.save()

        for uid in existing_admins:
            if uid in course['admins']:
                continue
            user = JBoxUserV2(uid)
            courses_offered = user.get_courses_offered()
            if course['id'] in courses_offered:
                courses_offered.remove(course['id'])
            user.set_courses_offered(courses_offered)
            user.set_role(JBoxUserV2.ROLE_OFFER_COURSES)
            user.save()

        return 0

    def handle_create_course(self, user_id):
        mode = self.get_argument('mode', None)
        if (mode is None) or (mode != 'create'):
            return False

        self.log_debug("handling create course")
        course = self.get_argument('params', None)
        course = json.loads(course)
        ret = HomeworkHandler.upload_course(user_id, course)
        msg = '' if ret == 0 else 'Course id already used by another user. \
            Please use a different course id or request the creator to add you as course administrator.'
        response = {
            'code': ret,
            'data': msg
        }
        self.write(response)
        return True
