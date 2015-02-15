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

        if self.handle_if_check(user_id):
            return
        if course_owner and self.handle_if_report(is_admin, user.get_courses_offered()):
            return

        self.log_error("no handlers found")
        # only AJAX requests responded to
        self.send_error()

    def handle_if_check(self, user_id):
        mode = self.get_argument('mode', None)
        if (mode is None) or ((mode != "check") and (mode != "submit")):
            return False
        self.log_error("handling check")
        course = self.get_argument('course', None)
        problemset = self.get_argument('problemset', None)
        question = self.get_argument('question', None)
        answer = self.get_argument('answer', None)

        record = (mode == "submit")

        status = JBoxCourseHomework.check_answer(course, problemset, question, user_id, answer, record)
        response = {'code': 0, 'data': status}
        self.write(response)
        return True

    def handle_if_report(self, is_admin, courses_offered):
        mode = self.get_argument('mode', None)
        if (mode is None) or (mode != "report"):
            return False
        self.log_error("handling report")
        course_id = self.get_argument('course', None)
        problemset_id = self.get_argument('problemset', None)

        if (not is_admin) and (course_id not in courses_offered):
            return False

        course = JBoxDynConfig.get_course(CloudHost.INSTALL_ID, course_id)
        if problemset_id not in course['problemsets']:
            return False

        report = JBoxCourseHomework.get_report(course_id, problemset_id)
        response = {'code': 0, 'data': report}
        self.write(response)
        return True