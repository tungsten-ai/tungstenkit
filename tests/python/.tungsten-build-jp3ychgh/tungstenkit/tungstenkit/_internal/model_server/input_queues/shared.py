from typing import List

import attrs


@attrs.frozen
class Batch:
    input_ids: List[str]
    data: List[dict]
    is_demo: bool
