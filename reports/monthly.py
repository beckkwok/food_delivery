from __future__ import annotations

from datetime import datetime

from sheets.client import SheetsClient


def generate_monthly_report(year: int, month: int) -> str:
    sheets = SheetsClient()
    data = sheets.get_monthly_data(year, month)

    lines = [
        f"📊 **Monthly Report — {year}-{month:02d}**",
        f"━━━━━━━━━━━━━━━━━━━━━",
        f"Total Orders: {data['total_orders']}",
        f"Total Revenue: £{data['total_revenue']:.2f}",
        f"Average Order: £{data['average_order']:.2f}",
        f"",
        f"**Orders:**",
    ]

    for o in data["orders"]:
        lines.append(
            f"  {o['OrderID']} — £{o.get('Total', 0)} — {o.get('Status')} "
            f"({o.get('CreatedAt', '?')[:10]})"
        )

    ratings = [int(f.get("Rating", 0)) for f in data["feedback"] if f.get("Rating")]
    if ratings:
        avg_rating = sum(ratings) / len(ratings)
        lines.append(f"\n**Customer Feedback:**")
        lines.append(f"  Avg Rating: {avg_rating:.1f}/5 ({len(ratings)} reviews)")
        for f in data["feedback"]:
            lines.append(f"  - Order {f['OrderID']}: {f.get('Rating', '?')}/5 — \"{f.get('Comment', '')}\"")
    else:
        lines.append(f"\nNo feedback this month.")

    return "\n".join(lines)


def export_report_csv(year: int, month: int) -> str:
    import csv
    import io

    sheets = SheetsClient()
    data = sheets.get_monthly_data(year, month)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["OrderID", "Customer", "Items", "Total", "Status", "Date"])
    for o in data["orders"]:
        writer.writerow([
            o["OrderID"], o.get("CustomerName", ""), o.get("Items", ""),
            o.get("Total", 0), o.get("Status"), o.get("CreatedAt", ""),
        ])
    return output.getvalue()


if __name__ == "__main__":
    now = datetime.now()
    report = generate_monthly_report(now.year, now.month)
    print(report)
