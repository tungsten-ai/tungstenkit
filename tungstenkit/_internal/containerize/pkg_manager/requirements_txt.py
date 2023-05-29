import typing as t

import attrs

from .pip_requirement import PipRequirement


@attrs.define
class RequirementsTxt:
    _pkg_requirements: t.List[str] = attrs.field(factory=list, init=False)
    _extra_index_urls: t.Set[str] = attrs.field(factory=set, init=False)

    @property
    def is_empty(self):
        return len(self._pkg_requirements) == 0

    def add_requirement(self, requirement: PipRequirement):
        self._pkg_requirements.append(requirement.to_str(index=False))
        if requirement.pip_extra_index_url:
            self._extra_index_urls.add(requirement.pip_extra_index_url)

    def build(self):
        requirements_txt = ""
        for extra_index_url in self._extra_index_urls:
            requirements_txt += f"--extra-index-url {extra_index_url}\n"
        for pkg_requirements in self._pkg_requirements:
            requirements_txt += f"{pkg_requirements}\n"
        return requirements_txt
