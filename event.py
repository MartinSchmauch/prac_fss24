from enum import Enum, auto

class EventType(Enum):
    CREATION = auto()
    ADMISSION = auto()
    ENTER_QUEUE = auto()
    REQUEST_RESOURCE = auto()
    RELEASE_RESOURCE = auto()
    RELEASE_PATIENT = auto()
    REPLAN_PATIENT = auto()

class Event:
    def __init__(self, event_type, event_start, event_end=None, event_resource=None, event_callback_url=None, event_callback_content=None, patient_id=None, patient_type=None):
        self.event_type = event_type
        self.event_start = event_start
        self.event_end = event_end
        self.event_resource = event_resource
        self.event_callback_url = event_callback_url
        self.event_callback_content = event_callback_content
        self.patient_id = patient_id
        self.patient_type = patient_type