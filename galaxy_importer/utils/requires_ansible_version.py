from packaging.specifiers import SpecifierSet


def validate(requirement_string):
    """Validate requires_ansible specifier

    Args:
        requirement_string (str): The value of the 'requires_ansible' attribute in the runtime file.
    Raises:
        InvalidSpecifier: If the value of requirement_string is not a
            valid packaging.specifiers.SpecifierSet.

    Returns:
        bool: True if requirement_string is valid, otherwise should raise exception.
    """
    SpecifierSet(requirement_string)
    return True
