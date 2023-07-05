from rest_framework import pagination


class PageNumberPagination10(pagination.PageNumberPagination):
    """
    Custom pagination class to specify the number of results per page.
    This class specifies 10 results per page.
    """

    page_size = 10


class PageNumberPagination7(pagination.PageNumberPagination):
    """
    Custom pagination class to specify the number of results per page.
    This class specifies 7 results per page.
    """

    page_size = 7

class PageNumberPagination(pagination.PageNumberPagination):
    """
    Custom pagination class to specify the number of results per page.
    This class specifies 5 results per page.
    """
    page_size = 5