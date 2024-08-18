import logging

class ProcessLogRecord(logging.LogRecord):
    def __init__(self, *args, **kwargs):
        # Custom attributes
        self.virtual_time = kwargs.pop('virtual_time', '')
        self.patient_id = kwargs.pop('patient_id', '')
        self.patient_type = kwargs.pop('patient_type', '')
        self.event_type = kwargs.pop('event_type', '')
        self.status = kwargs.pop('status', '')
        
        # Initialize the parent class with remaining arguments
        super().__init__(*args, **kwargs)
        

def process_log_record_factory(*args, **kwargs):
    return ProcessLogRecord(*args, **kwargs)

# Configure the logging module
def setup_logging(log_file_name):
    logging.setLogRecordFactory(process_log_record_factory)
    logging.basicConfig(
        level=logging.INFO,
        # format='%(asctime)s - %(virtual_time)s - %(process_instance_id)s - %(patient_id)s - %(patient_type)s - %(event_type)s - %(status)s - %(message)s',
        # datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[logging.FileHandler(log_file_name), logging.StreamHandler()]
    )

# Create a custom logger
logger = logging.getLogger('process_logger')

# def log_event(virtual_time=None, process_instance_id=None, patient_id=None, patient_type=None, event_type=None, status=None, message=None):
#     logger.info(
#         message,
#         extra={
#             'virtual_time': virtual_time,
#             'process_instance_id': process_instance_id,
#             'patient_id': patient_id,
#             'patient_type': patient_type,
#             'event_type': event_type,
#             'status': status
#         }
#     )

def log_event(virtual_time=None, process_instance_id=None, patient_id=None, patient_type=None, event_type=None, status=None, message=None):
    # Assuming fixed widths for each field
    time_str = str(round(virtual_time, 4)).ljust(6)
    patient_id_str = str(patient_id).ljust(5)
    patient_type_str = str(patient_type).ljust(15)
    event_type_str = str(event_type).ljust(26)
    status_str = str(status).ljust(7)
    
    # Updated logging statement with fixed widths
    logger.info(f"{time_str} - {patient_id_str} - {patient_type_str} - {event_type_str} - {status_str} - {message}")
    # logger.info(f"{round(virtual_time,4)} - {patient_id} - {patient_type} - {event_type} - {status} - {message}"
    # )
    