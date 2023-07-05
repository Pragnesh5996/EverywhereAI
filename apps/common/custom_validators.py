class RequiredParameterValidator:
    """
    This is the RequiredParameterValidator class, which is used to validate that required
    parameters are present in a Django API request. It includes an init method that sets the
    request and required_parameters attributes, and a validate method that iterates through
    the required_parameters and checks if each one is present in the request data.
    If any required parameters are missing, the validate method returns False and a list of missing
    parameters. If all required parameters are present, it returns True and None.
    """

    def __init__(self, request, required_parameters):
        self.request = request
        self.required_parameters = required_parameters

    def validate(self):
        missing_parameters = []
        for parameter in self.required_parameters:
            if parameter not in self.request.data:
                missing_parameters.append(parameter)
            else :
                if self.request.data.get(parameter) == "" or self.request.data.get(parameter) == []:
                   missing_parameters.append(parameter)

        if len(missing_parameters) > 0:
            return False, missing_parameters
        return True, None
