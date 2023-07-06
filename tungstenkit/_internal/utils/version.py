import typing as t

from packaging.version import Version

from tungstenkit.exceptions import NoCompatibleVersion

MIN_VER = Version("0.0.0")


class NotRequired:
    pass


def version_converter(ver_str: str) -> Version:
    return Version(ver_str)


def optional_version_converter(ver_str: t.Optional[str]) -> t.Optional[Version]:
    return version_converter(ver_str) if ver_str else None


def order_optional_version(optional_version: t.Optional[Version]):
    if optional_version is None:
        return MIN_VER
    return optional_version


def check_version_matching_clause_loosely(
    ver: t.Optional[Version], constraint: t.Optional[Version]
):
    """
    Check a version satisfies a constraint.
    For example, if constraint is ``1.1``, version ``1.2``, ``1`` is not passed.
    """
    if constraint is None:
        return True

    if ver is None and constraint is not None:
        return False

    is_compatible = True
    num_release_in_constraint = len(constraint.release)
    if num_release_in_constraint > 0:
        is_compatible &= ver.major == constraint.major
    if num_release_in_constraint > 1:
        is_compatible &= ver.minor == constraint.minor
    if num_release_in_constraint > 2:
        is_compatible &= ver.micro == constraint.micro
    if constraint.pre is not None:
        is_compatible &= ver.pre == constraint.pre
    if constraint.post is not None:
        is_compatible &= ver.post == constraint.post
    if constraint.dev is not None:
        is_compatible &= ver.dev == constraint.dev
    if constraint.local is not None:
        is_compatible &= ver.local == constraint.local
    return is_compatible


def check_if_two_versions_compatible(v1: t.Optional[Version], v2: t.Optional[Version]) -> bool:
    """
    Return ``True`` only if the version segments specified in both versions are the same.
    """
    is_compatible = True
    if v2 is None or v1 is None:
        return is_compatible

    num_release_in_v2 = len(v2.release)
    num_release_in_v1 = len(v1.release)
    if num_release_in_v1 > 0 and num_release_in_v2 > 0:
        is_compatible &= v1.major == v2.major
    if num_release_in_v1 > 1 and num_release_in_v2 > 1:
        is_compatible &= v1.minor == v2.minor
    if num_release_in_v1 > 2 and num_release_in_v2 > 2:
        is_compatible &= v1.micro == v2.micro
    if v1.pre is not None and v2.pre is not None:
        is_compatible &= v1.pre == v2.pre
    if v1.post is not None and v2.post is not None:
        is_compatible &= v1.post == v2.post
    if v1.dev is not None and v2.dev is not None:
        is_compatible &= v1.dev == v2.dev
    if v1.local is not None and v2.local is not None:
        is_compatible &= v1.local == v2.local
    return is_compatible


def order_optional_int_ver(optional_int_ver: t.Optional[int]) -> int:
    return optional_int_ver if optional_int_ver else -1


def intersect_release_segment_sets(
    list_release_segment_sets: t.Sequence[t.Set[t.Optional[int]]],
) -> t.Set[t.Optional[int]]:
    """
    Interset while treating a set containing None (any version) as the union of all non-none values
    """
    assert len(list_release_segment_sets) > 0

    if len(list_release_segment_sets) == 1:
        return list_release_segment_sets[0]

    if any(len(ver_set) == 0 for ver_set in list_release_segment_sets):
        return set()

    # [{None}, {None}, ...]
    if all(len(ver_set) == 1 and None in ver_set for ver_set in list_release_segment_sets):
        return list_release_segment_sets[0]

    union = list_release_segment_sets[0].union(*list_release_segment_sets[1:])
    intersected = (
        union if None in list_release_segment_sets[0] else set(list_release_segment_sets[0])
    )
    for ver_set in list_release_segment_sets:
        if None not in ver_set:
            intersected = intersected.intersection(ver_set)

    return intersected


def find_latest_compatible_version(
    list_version_sets: t.Sequence[t.Union[t.Set[Version], t.Set[t.Optional[Version]]]],
) -> t.Optional[Version]:
    # NOTE Works on None (any version) or versions containing only release segments,
    # i.e. None or Verison("<major_num>.<minor_num>.<micro_num>").

    if len(list_version_sets) == 0:
        return None
    elif len(list_version_sets) == 1:
        if len(list_version_sets[0]) == 0:
            raise NoCompatibleVersion

        return max(list_version_sets[0], key=order_optional_version)

    # Determine major version
    major_sets = [
        set(ver.major if ver else None for ver in ver_set) for ver_set in list_version_sets
    ]
    major_intersected = intersect_release_segment_sets(major_sets)

    for major in sorted(major_intersected, reverse=True, key=order_optional_int_ver):
        if major is None:
            return None

        # Determine minor version
        major_filtered = [
            [ver for ver in ver_set if ver is None or ver.major == major]
            for ver_set in list_version_sets
        ]
        minor_sets = [
            set(ver.minor if ver is not None and len(ver.release) > 1 else None for ver in ver_set)
            for ver_set in major_filtered
        ]
        minor_intersected = intersect_release_segment_sets(minor_sets)

        for minor in sorted(minor_intersected, reverse=True, key=order_optional_int_ver):
            if minor is None:
                return Version(f"{major}")

            # Determine micro version
            minor_filtered = [
                [
                    ver
                    for ver in ver_set
                    if ver is None or len(ver.release) < 2 or ver.minor == minor
                ]
                for ver_set in major_filtered
            ]
            micro_sets = [
                set(
                    ver.micro if ver is not None and len(ver.release) > 2 else None
                    for ver in ver_set
                )
                for ver_set in minor_filtered
            ]
            micro_intersected = intersect_release_segment_sets(micro_sets)
            if len(micro_intersected) == 0:
                continue

            micro = max(micro_intersected, key=order_optional_int_ver)
            return (
                Version(f"{major}.{minor}.{micro}")
                if micro is not None
                else Version(f"{major}.{minor}")
            )

    raise NoCompatibleVersion
