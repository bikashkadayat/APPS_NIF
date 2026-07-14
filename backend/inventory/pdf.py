"""Take-Out Gate Pass PDF — reuses the shared NIF letterhead (common_context +
base_pdf.html: larger logo, org contact block, QR verification)."""
from config.nepali_dates import to_bs
from documents.pdf import common_context, render_pdf


def render_gate_pass(req):
    ctx = common_context(req.reference)
    ctx.update({
        "reference": req.reference,
        "item_code": req.item_code,
        "item_name": req.item_name,
        "holder": req.requested_by_name,
        "department": req.department.name if req.department else "—",
        "purpose": req.get_purpose_display(),
        "reason": req.reason or "—",
        "out_ad": str(req.expected_out_date), "out_bs": to_bs(req.expected_out_date) or "—",
        "return_ad": str(req.expected_return_date), "return_bs": to_bs(req.expected_return_date) or "—",
        "approver": req.approver_name or "—",
        "approver_remarks": req.approver_remarks or "",
        "status_label": req.get_status_display(),
        "action_ad": req.action_date.date().isoformat() if req.action_date else "—",
        "action_bs": to_bs(req.action_date.date()) if req.action_date else "—",
    })
    return render_pdf("pdf/gate_pass.html", ctx)


def render_assignment_receipt(item, assignment):
    """Asset handover / assignment receipt on the shared NIF letterhead."""
    ctx = common_context(item.asset_code)
    specs = []
    for label, val in [
        ("Brand", item.brand), ("Model", item.model), ("CPU", item.cpu), ("RAM", item.ram),
        ("Storage", " ".join(x for x in [item.storage_size, item.storage_type] if x)),
        ("GPU", item.gpu), ("Screen", item.screen_size), ("OS", item.os),
        ("Serial No.", item.serial_number), ("MAC", item.mac_address),
    ]:
        if val:
            specs.append({"label": label, "value": val})
    ctx.update({
        "asset_code": item.asset_code, "item_name": item.name,
        "asset_type": item.get_asset_type_display(),
        "category": item.category.name if item.category else "—",
        "specs": specs, "accessories": assignment.accessories or item.accessories or "—",
        "holder": assignment.assigned_to_name,
        "assigned_by": assignment.assigned_by_name or "—",
        "condition": assignment.get_handover_condition_display() if assignment.handover_condition else "—",
        "assigned_ad": str(assignment.assigned_date) if assignment.assigned_date else "—",
        "assigned_bs": to_bs(assignment.assigned_date) if assignment.assigned_date else "—",
        "is_handover": assignment.is_handover,
        "remarks": assignment.note or "",
    })
    return render_pdf("pdf/assignment_receipt.html", ctx)
