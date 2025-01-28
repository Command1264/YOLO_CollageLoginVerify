from dataclasses import dataclass
import datetime

@dataclass
class ScholarshipObject(object):
    index: int
    academic_year: int
    semester: int
    type: str
    scholarship_id: int
    scholarship_name: str
    external_link: str
    dead_line: datetime.datetime
    money: int

@dataclass
class ScholarshipApplyObject(object):
    index: int
    academic_year: int
    semester: int
    scholarship_id: int
    scholarship_name: str
    application_results: str
    money: int
    awarding_method: str
    prize_progress: str