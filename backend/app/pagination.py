"""列表分页统一约定。

所有返回分页结构的列表端点共用同一套参数：page 从 1 开始，
page_size 默认 20、上限 100，响应补充 total 与 pages。
裸数组端点（如 /medical/hospitals、/bookings/）受前端契约限制，
不能改成 {items: ...} 外层结构，因此不适用本依赖。
"""

import math
from dataclasses import dataclass

from fastapi import Query

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def pages(self, total: int) -> int:
        return math.ceil(total / self.page_size) if total else 0


def pagination(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"每页条数，上限 {MAX_PAGE_SIZE}",
    ),
) -> PageParams:
    return PageParams(page=page, page_size=page_size)
