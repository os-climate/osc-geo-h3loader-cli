# Copyright 2024 Broda Group Software Inc.
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
#
# Created: 2024-05-22 by davis.broda@brodagroupsoftware.com
import re

def get_point_res_col(resolution: int) -> str:
    if resolution > 15 or resolution < 0:
        raise ValueError(
            f"resolution must be between 0 and 15. resolution was: {resolution}"
        )

    return f"res{resolution}"
