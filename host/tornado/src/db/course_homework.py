from boto.dynamodb2.fields import HashKey, RangeKey
from boto.dynamodb2.types import STRING

import datetime
import pytz

import boto.dynamodb2.exceptions

from db.db_base import JBoxDB


class JBoxCourseHomework(JBoxDB):
    NAME = 'jbox_coursehomework'

    SCHEMA = [
        HashKey('question_gid', data_type=STRING),
        RangeKey('student_id', data_type=STRING)
    ]

    INDEXES = None

    TABLE = None

    SEP = '|'
    ANSWER_KEY = '-'

    STATE_CORRECT = 1
    STATE_INCORRECT = -1
    STATE_PENDING = 0

    def __init__(self, course_id, problemset_id, question_id, student_id, answer=None, state=None, create=False):
        if self.table() is None:
            return

        self.item = None
        if create:
            if (answer is None) or (state is None) or (not JBoxCourseHomework.valid_state(state)) or\
                    (student_id is None) or (course_id is None) or (problemset_id is None) or (question_id is None):
                raise AssertionError
            if (student_id == JBoxCourseHomework.ANSWER_KEY) and (state != JBoxCourseHomework.STATE_CORRECT):
                raise AssertionError

        question_gid = JBoxCourseHomework.question_gid(course_id, problemset_id, question_id)

        if create:
            dt = datetime.datetime.now(pytz.utc)
            data = {
                'question_gid': question_gid,
                'course_id': course_id,
                'problemset_id': problemset_id,
                'question_id': question_id,
                'student_id': student_id,
                'answer': answer,
                'state': state,
                'create_time': JBoxCourseHomework.datetime_to_epoch_secs(dt)
            }
            self.create(data)

        self.item = self.table().get_item(question_gid=question_gid, student_id=student_id)
        self.is_new = create

    @staticmethod
    def question_gid(course_id, problemset_id, question_id):
        return '|'.join([course_id, problemset_id, question_id])

    @staticmethod
    def valid_state(correct):
        return correct in (JBoxCourseHomework.STATE_CORRECT,
                           JBoxCourseHomework.STATE_INCORRECT,
                           JBoxCourseHomework.STATE_PENDING)

    def set_answer(self, answer, state):
        self.set_attrib('answer', answer)
        self.set_attrib('state', state)

    def increment_attempts(self):
        self.set_attrib('attempts', int(self.get_attrib('attempts', 0))+1)

    def set_score(self, score):
        self.set_attrib('score', score)

    @staticmethod
    def get_answer(course_id, problemset_id, question_id, student_id=ANSWER_KEY):
        try:
            rec = JBoxCourseHomework(course_id, problemset_id, question_id, student_id)
            return rec.get_attrib('answer', None), int(rec.get_attrib('score', 0)), int(rec.get_attrib('attempts', 0))
        except:
            JBoxCourseHomework.log_exception("exception while getting answer")
            return None, int(0), int(0)

    @staticmethod
    def check_answer(course_id, problemset_id, question_id, student_id, answer, record=True):
        ans, score, attempts = JBoxCourseHomework.get_answer(course_id, problemset_id, question_id)
        max_score = score
        JBoxCourseHomework.log_debug("comparing [%r] with answer [%r] for course[%s], pset[%s], q[%s], student[%s]",
                                     answer, ans, course_id, problemset_id, question_id, student_id)
        correct = (ans == answer)
        state = JBoxCourseHomework.STATE_CORRECT if correct else JBoxCourseHomework.STATE_INCORRECT
        if state != JBoxCourseHomework.STATE_CORRECT:
            score = 0

        used_attempts = 1
        if record:
            try:
                rec = JBoxCourseHomework(course_id, problemset_id, question_id, student_id)
                used_attempts = rec.get_attrib('attempts', 0)
                max_attempts = used_attempts >= attempts > 0
                # if correct answer not provided yet, record the latest answer
                if (rec.get_attrib('state') != JBoxCourseHomework.STATE_CORRECT) and not max_attempts:
                    rec.set_answer(answer, state)
                else:
                    score = rec.get_attrib('score', 0)
            except boto.dynamodb2.exceptions.ItemNotFound:
                rec = JBoxCourseHomework(course_id, problemset_id, question_id, student_id,
                                         answer=answer, state=state, create=True)
            if state == JBoxCourseHomework.STATE_INCORRECT:
                rec.increment_attempts()
            rec.set_score(score)
            rec.save()

        return state, score, used_attempts, max_score, attempts

    @staticmethod
    def get_report(course_id, problemset_id, question_ids, student_id=None):
        questions = []
        for question_id in question_ids:
            students = []
            question_gid = JBoxCourseHomework.question_gid(course_id, problemset_id, question_id)
            if student_id is None:
                records = JBoxCourseHomework.table().query_2(question_gid__eq=question_gid,
                                                             student_id__gt=' ')
            else:
                records = JBoxCourseHomework.table().query_2(question_gid__eq=question_gid,
                                                             student_id__eq=student_id)

            for rec in records:
                if rec['student_id'] == JBoxCourseHomework.ANSWER_KEY:
                    continue
                score = rec['score'] if 'score' in rec else 0
                attempts = rec['attempts'] if 'attempts' in rec else 0
                students.append({
                    'id': rec['student_id'],
                    'evaluation': int(rec['state']),
                    'score': int(score),
                    'attempts': int(attempts)
                })

            questions.append({
                'id': question_id,
                'students': students
            })
        return {
            'course_id': course_id,
            'problemset_id': problemset_id,
            'questions': questions
        }

    @staticmethod
    def get_answers(course_id, problemset_id, question_ids):
        answers = []
        for question_id in question_ids:
            question_gid = JBoxCourseHomework.question_gid(course_id, problemset_id, question_id)
            records = JBoxCourseHomework.table().query_2(question_gid__eq=question_gid,
                                                         student_id__eq=JBoxCourseHomework.ANSWER_KEY)

            for rec in records:
                answers.append(rec['answer'])
        return answers
