from rest_framework.response import Response
from rest_framework import status
from apps.common.custom_exception import handle_error
from apps.common.custom_validators import RequiredParameterValidator
import sys
import traceback


def track_error(validate_api_parameters=None):
    """
    This decorator tracks errors and validates API parameters before allowing access to the decorated view function.
    It can be used by adding @track_error1(validate_api_parameters=["param1", "param2"]) above a view function.
    The decorator takes an optional argument, validate_api_parameters, which is a list of required API parameters.
    """

    def decorator(view_func):
        def wrapper(self, request, *args, **kwargs):
            api_class_name = self.__class__.__name__
            ad_platform = self.request.data.get("ad_platform")
            try:
                if validate_api_parameters:
                    validator = RequiredParameterValidator(
                        request, validate_api_parameters
                    )
                    is_valid, missing_parameters = validator.validate()
                    if not is_valid:
                        return Response(
                            data={
                                "error": True,
                                "data": [],
                                "message": f"Missing parameters: {', '.join(missing_parameters)}",
                            },
                            status=status.HTTP_406_NOT_ACCEPTABLE,
                        )
                return view_func(self, request, *args, **kwargs)

            except Exception as e:
                if ad_platform:
                    handle_error(
                        f"{ad_platform} {api_class_name} returned with an exception with data: {self.request.data}.",
                        str(e),
                    )
                tb = traceback.extract_tb(sys.exc_info()[2])
                error_file, error_line, function_name, text = tb[-1]
                error_message = "An error occurred in file '{}' at line {}: '{}' in function '{}'".format(
                    error_file, error_line, str(e), function_name
                )
                if "/query.py" in error_message:
                    error_message = traceback.format_exc()

                return Response(
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                    data={
                        "error": True,
                        "data": [],
                        "message": str(e),
                        "exc_message": error_message,
                    },
                )

        return wrapper

    return decorator
