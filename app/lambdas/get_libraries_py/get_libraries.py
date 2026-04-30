#!/usr/bin/env python3

"""
Get the libraries from the input, check their metadata,
"""
from typing import List, cast, TypedDict, Optional, Union

from orcabus_api_tools.metadata import get_library_from_library_orcabus_id
from orcabus_api_tools.metadata.models import LibraryBase, Library


class ReadSet(TypedDict):
    orcabusId: str
    rgid: str


class LibraryWithReadsets(LibraryBase):
    readsets: Optional[ReadSet]


def get_rgid_list_from_library_object(
        library_object: Union[LibraryWithReadsets, Library],
        library_list: Optional[List[LibraryWithReadsets]] = None
) -> List[str]:
    if 'phenotype' in library_object.keys():
        if library_list is None:
            raise ValueError("Must set library_list if library_object is of type Library")
        # library object
        library_object: LibraryWithReadsets = next(filter(
            lambda library_iter_: library_iter_['libraryId'] == library_object['libraryId'],
            library_list
        ))

    return list(map(
        lambda readset_iter_: readset_iter_['rgid'],
        (
            cast(list, library_object.get('readsets'))
            if library_object.get('readsets') is not None
            else []
        )
    ))


def handler(event, context):
    """
    Get the libraries from the input, check their metadata,
    :param event:
    :param context:
    :return:
    """
    libraries: List[LibraryWithReadsets] = event.get("libraries", [])
    if not libraries:
        raise ValueError("No libraries provided in the input")

    if len(libraries) > 2:
        raise ValueError("We expect at most two libraries in the input")

    if len(libraries) == 1:
        # If only one library is provided, then we have a germline library
        return {
            "libraryId": libraries[0]['libraryId'],
            "fastqRgidList": get_rgid_list_from_library_object(libraries[0])
        }

    # Get library metadata for both libraries
    library_obj_list = list(map(
        lambda library_iter_: get_library_from_library_orcabus_id(library_iter_['orcabusId']),
        libraries
    ))

    # Check if both libraries are provided
    try:
        tumor_library_obj = next(filter(
            lambda library_iter_: library_iter_['phenotype'] == 'tumor',
            library_obj_list
        ))
    except StopIteration:
        raise ValueError("No tumor library found in the input")

    try:
        library_obj = next(filter(
            lambda library_iter_: library_iter_['phenotype'] == 'normal',
            library_obj_list
        ))
    except StopIteration:
        raise ValueError("No normal library found in the input")

    # If both libraries are provided, return their IDs
    return {
        "libraryId": library_obj['libraryId'],
        "tumorLibraryId": tumor_library_obj['libraryId'],
        "fastqRgidList": get_rgid_list_from_library_object(library_obj, libraries),
        "tumorFastqRgidList": get_rgid_list_from_library_object(tumor_library_obj, libraries)
    }
