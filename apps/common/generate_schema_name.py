import string
import random
import uuid


class Schema:
    """
    This class defines the Schema class which has a method
    to generate random schema names.
    """

    def generate_schema_name(self):
        # initializing size of string
        N = 7
        # generating random strings
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=N))

    def generate_uuid(self):
        return uuid.uuid4()
