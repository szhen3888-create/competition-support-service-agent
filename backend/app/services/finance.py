"""预算 / 借款 / 报销：结构化计算 + 规则校验（金额不由 LLM 编造）。"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


FinanceKind = Literal["budget", "loan", "reimbursement"]


@dataclass
class BudgetItem:
    name: str
    quantity: float
    unit_price: float
    amount: float
    note: str = ""


@dataclass
class BudgetDraft:
    competition_name: str
    people: int
    location: str
    items: list[BudgetItem] = field(default_factory=list)
    total: float = 0.0
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "competition_name": self.competition_name,
            "people": self.people,
            "location": self.location,
            "items": [asdict(i) for i in self.items],
            "total": self.total,
            "assumptions": self.assumptions,
        }


@dataclass
class ReimbursementCheck:
    required: list[str]
    provided: list[str]
    missing: list[str]
    ok: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_budget(
    *,
    competition_name: str,
    people: int,
    location: str,
    registration_fee: float = 0.0,
    transport_per_person: float = 0.0,
    lodging_per_person_night: float = 0.0,
    nights: int = 0,
    local_transport: float = 0.0,
    other: float = 0.0,
    other_note: str = "",
) -> BudgetDraft:
    """
    仅使用调用方提供的单价/数量计算。
    不从模型臆造学校补贴标准。
    """
    people = max(int(people or 0), 0)
    nights = max(int(nights or 0), 0)
    assumptions = [
        "金额按用户填写或台账字段计入，系统只做乘法汇总",
        "正式提交前需按学院经费管理办法审核",
    ]
    items: list[BudgetItem] = []

    if registration_fee:
        items.append(
            BudgetItem(
                name="报名费",
                quantity=people if people else 1,
                unit_price=float(registration_fee),
                amount=round(float(registration_fee) * (people if people else 1), 2),
                note="按人计" if people else "按队/项计",
            )
        )
    if transport_per_person and people:
        items.append(
            BudgetItem(
                name="往返交通费",
                quantity=people,
                unit_price=float(transport_per_person),
                amount=round(people * float(transport_per_person), 2),
            )
        )
    if lodging_per_person_night and people and nights:
        items.append(
            BudgetItem(
                name="住宿费",
                quantity=people * nights,
                unit_price=float(lodging_per_person_night),
                amount=round(people * nights * float(lodging_per_person_night), 2),
                note=f"{people}人 × {nights}晚",
            )
        )
    if local_transport:
        items.append(
            BudgetItem(
                name="市内交通",
                quantity=1,
                unit_price=float(local_transport),
                amount=round(float(local_transport), 2),
            )
        )
    if other:
        items.append(
            BudgetItem(
                name="其他",
                quantity=1,
                unit_price=float(other),
                amount=round(float(other), 2),
                note=other_note or "需说明用途",
            )
        )

    total = round(sum(i.amount for i in items), 2)
    return BudgetDraft(
        competition_name=competition_name or "（未指定竞赛）",
        people=people,
        location=location or "（未指定地点）",
        items=items,
        total=total,
        assumptions=assumptions,
    )


def build_loan_text(budget: BudgetDraft, *, approved_total: float | None = None, budget_ref: str = "") -> str:
    amount = approved_total if approved_total is not None else budget.total
    lines = [
        "【借款申请说明（系统草稿）】",
        f"一、事由：参加「{budget.competition_name}」，地点：{budget.location}，人数：{budget.people}。",
        f"二、借款金额：{amount:.2f} 元" + (f"（批准预算文号/编号：{budget_ref}）" if budget_ref else "（请填写批准预算文号）") + "。",
        "三、预算明细：",
    ]
    for i in budget.items:
        lines.append(f"  - {i.name}：{i.amount:.2f} 元（{i.quantity} × {i.unit_price:.2f}）{('；' + i.note) if i.note else ''}")
    lines.append(f"四、合计：{budget.total:.2f} 元。")
    lines.append("五、承诺：赛后按时报账，多退少补；票据规范、材料齐全。")
    return "\n".join(lines)


REQUIRED_REIMBURSEMENT = [
    "发票原件",
    "行程单据",
    "参赛证明（通知/参赛证）",
    "批准预算表",
]


def check_reimbursement_materials(provided: list[str] | None = None) -> ReimbursementCheck:
    provided = [p.strip() for p in (provided or []) if p and p.strip()]
    missing = [r for r in REQUIRED_REIMBURSEMENT if not any(r in p or p in r for p in provided)]
    return ReimbursementCheck(
        required=list(REQUIRED_REIMBURSEMENT),
        provided=provided,
        missing=missing,
        ok=len(missing) == 0,
    )


def detect_finance_kind(text: str) -> FinanceKind:
    if any(k in text for k in ("报销", "发票", "报账")):
        return "reimbursement"
    if any(k in text for k in ("借款", "借支", "预借")):
        return "loan"
    return "budget"
