from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from dateutil.relativedelta import relativedelta


def rupiah(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}Rp {abs(float(value)):,.0f}".replace(",", ".")


def roman_month(month: int) -> str:
    vals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
    return vals[month - 1]


def pro_rata(anchor: date, start: date, end: date) -> float:
    """Actual/Actual by policy anniversary for half-open interval [start, end)."""
    if end <= start:
        return 0.0
    if start < anchor:
        raise ValueError("Periode perhitungan tidak boleh sebelum awal polis.")
    anniversary = anchor
    while start >= anniversary + relativedelta(years=1):
        anniversary += relativedelta(years=1)
    factor = 0.0
    cursor = start
    while cursor < end:
        next_anniversary = anniversary + relativedelta(years=1)
        segment_end = min(end, next_anniversary)
        factor += (segment_end - cursor).days / (next_anniversary - anniversary).days
        cursor = segment_end
        if cursor >= next_anniversary:
            anniversary = next_anniversary
    return factor


def premium(si: float, rate_per_mille: float, factor: float) -> float:
    return float(si) * float(rate_per_mille) / 1000.0 * float(factor)


def load_master(base_dir: Path) -> pd.DataFrame:
    full = base_dir / "ojk_occupations_full.csv"
    if full.exists():
        files = [full]
    else:
        files = sorted(p for p in base_dir.glob("ojk_occupations_*.csv") if p.name != "ojk_occupations_full.csv")
        if not files:
            single = base_dir / "ojk_occupations.csv"
            files = [single] if single.exists() else []
    if not files:
        raise FileNotFoundError("Master okupasi OJK tidak ditemukan.")
    frames = [pd.read_csv(p, encoding="utf-8-sig", dtype={"code": str, "variant": str}) for p in files]
    df = pd.concat(frames, ignore_index=True)
    df["variant"] = df["variant"].fillna("")
    if "rate_basis" not in df.columns:
        df["rate_basis"] = "construction"
    df["rate_basis"] = df["rate_basis"].fillna("construction")
    for col in ["k1_low", "k1_high", "k2_low", "k2_high", "k3_low", "k3_high"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["k1_low", "k1_high", "k2_low", "k2_high", "k3_low", "k3_high"])
    return df.drop_duplicates(subset=["id"], keep="last").reset_index(drop=True)


def occ_label(row: pd.Series) -> str:
    alias = str(row["alias"]).strip() if pd.notna(row["alias"]) else ""
    name = str(row["name"]).strip()
    return f"{alias or name} - {str(row['code']).strip()}"


def tariff_range(row: pd.Series, cls: str) -> tuple[float, float]:
    if str(row.get("rate_basis", "construction")) == "single":
        return float(row["k1_low"]), float(row["k1_high"])
    n = cls[-1]
    return float(row[f"k{n}_low"]), float(row[f"k{n}_high"])


def is_single_rate(row: pd.Series) -> bool:
    return str(row.get("rate_basis", "construction")) == "single"


def default_occ_index(df: pd.DataFrame, code: str = "2976") -> int:
    hits = df.index[df["code"].astype(str) == code].tolist()
    return hits[0] if hits else int(df.index[0])


def validation_status(rate: float, low: float, high: float) -> str:
    if rate < low - 1e-9:
        return "below"
    if rate > high + 1e-9:
        return "above"
    return "ok"


def occ_details(master: pd.DataFrame, idx: int | None) -> tuple[str, str, str]:
    if idx is None:
        return "-", "-", "-"
    row = master.loc[idx]
    return str(row["code"]), str(row["alias"]), str(row["name"])


def invalid_approvals(objects: list[dict[str, Any]]) -> list[str]:
    messages: list[str] = []
    for idx, ob in enumerate(objects, 1):
        # Tarif kondisi baru yang berada di luar range master harus punya dasar UW.
        # Tarif polis lama tetap boleh diinput sesuai dokumen polis agar endorsement tidak
        # menghitung ulang sejarah polis menggunakan master saat ini.
        if ob["new_status"] != "ok":
            if not ob["new_approved"] or not str(ob["new_reason"]).strip():
                messages.append(f"Obyek {idx}: tarif baru di luar range OJK belum dilengkapi approval/dasar underwriting.")
    return messages


def calculate(data: dict[str, Any], settings: dict[str, Any], master: pd.DataFrame) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    mode = data["mode"]
    old_full = old_earned = old_remaining = new_remaining = 0.0

    if mode == "Endorsement":
        anchor, effective = data["old_start"], data["effective"]
        old_end, new_end = data["old_end"], data["new_end"]
        if not (anchor <= effective <= old_end):
            raise ValueError("Tanggal efektif endorsement harus berada dalam periode polis lama.")
        if new_end < effective:
            raise ValueError("Tanggal akhir polis baru tidak boleh sebelum tanggal efektif endorsement.")
        f_full = pro_rata(anchor, anchor, old_end)
        f_earned = pro_rata(anchor, anchor, effective)
        f_old_rem = pro_rata(anchor, effective, old_end)
        f_new_rem = pro_rata(anchor, effective, new_end)

        for ob in data["objects"]:
            p_full = premium(ob["old_si"], ob["old_rate"], f_full)
            p_earned = premium(ob["old_si"], ob["old_rate"], f_earned)
            p_old_rem = premium(ob["old_si"], ob["old_rate"], f_old_rem)
            p_new_rem = premium(ob["new_si"], ob["new_rate"], f_new_rem)
            old_full += p_full
            old_earned += p_earned
            old_remaining += p_old_rem
            new_remaining += p_new_rem
            old_code, old_alias, _ = occ_details(master, ob["old_occ_idx"])
            new_code, new_alias, _ = occ_details(master, ob["new_occ_idx"])
            rows.append({
                "Obyek": ob["name"] or f"Obyek {len(rows)+1}",
                "Perubahan": ob["change_type"],
                "SI Lama": ob["old_si"], "SI Baru": ob["new_si"],
                "Okupasi Lama": old_alias, "Kode Lama": old_code,
                "Kelas Lama": ob["old_class"] or "-", "Rate Lama (‰)": ob["old_rate"],
                "Okupasi Baru": new_alias, "Kode Baru": new_code,
                "Kelas Baru": ob["new_class"] or "-", "Rate Baru (‰)": ob["new_rate"],
                "Premi Sisa Lama": p_old_rem, "Premi Sisa Baru": p_new_rem,
                "Adjustment": p_new_rem - p_old_rem,
            })
        base_adjustment = new_remaining - old_remaining
        revised_total = old_earned + new_remaining
        period_days = max((new_end - effective).days, 0)
        factor_display = f_new_rem
    else:
        anchor, end = data["start"], data["end"]
        if end <= anchor:
            raise ValueError("Tanggal akhir pertanggungan harus setelah tanggal mulai.")
        factor = pro_rata(anchor, anchor, end)
        for ob in data["objects"]:
            p = premium(ob["new_si"], ob["new_rate"], factor)
            new_remaining += p
            code, alias, _ = occ_details(master, ob["new_occ_idx"])
            rows.append({
                "Obyek": ob["name"] or f"Obyek {len(rows)+1}",
                "SI": ob["new_si"], "Okupasi": alias, "Kode": code,
                "Kelas": ob["new_class"], "Rate (‰)": ob["new_rate"],
                "Range OJK": f"{ob['new_low']:.3f}-{ob['new_high']:.3f}‰",
                "Premi FLEXAS": p,
            })
        base_adjustment = new_remaining
        revised_total = new_remaining
        period_days = (end - anchor).days
        factor_display = factor

    extension_adjustment = float(data.get("extension_adjustment", 0.0))
    adjustment = base_adjustment + extension_adjustment
    if abs(adjustment) < 0.5:
        adjustment = 0.0

    admin_fee = float(settings["admin_fee"]) if adjustment != 0 else 0.0
    stamp_count = 0 if adjustment == 0 else 1
    if adjustment != 0 and abs(adjustment) + admin_fee > float(settings["stamp_threshold"]):
        stamp_count += 1
    stamp = stamp_count * float(settings["stamp_each"])

    if adjustment > 0:
        customer_settlement = adjustment + admin_fee + stamp
    elif adjustment < 0:
        refund = abs(adjustment)
        if settings["deduct_refund_costs"]:
            refund = max(refund - admin_fee - stamp, 0.0)
        customer_settlement = -refund
    else:
        customer_settlement = 0.0

    fee_gross = abs(adjustment) * float(settings["fee_pct"]) / 100.0
    vat = float(settings["vat_pct"]) / 100.0
    vat_component = fee_gross * vat / (1.0 + vat) if vat > 0 else 0.0
    fee_net = fee_gross - vat_component
    return {
        "old_full": old_full, "old_earned": old_earned, "old_remaining": old_remaining,
        "new_remaining": new_remaining, "revised_total": revised_total,
        "base_adjustment": base_adjustment, "extension_adjustment": extension_adjustment,
        "adjustment": adjustment, "rows": rows, "period_days": period_days,
        "factor": factor_display, "admin_fee": admin_fee, "stamp": stamp,
        "stamp_count": stamp_count, "customer_settlement": customer_settlement,
        "fee_gross": fee_gross, "vat_component": vat_component, "fee_net": fee_net,
    }


def table_for_export(data: dict[str, Any], calc: dict[str, Any]) -> list[tuple[str, str]]:
    if data["mode"] == "Endorsement":
        lines = [
            ("Premi polis lama (FLEXAS)", rupiah(calc["old_full"])),
            ("Premi sudah berjalan", rupiah(calc["old_earned"])),
            ("Premi sisa lama", rupiah(calc["old_remaining"])),
            ("Premi sisa kondisi baru", rupiah(calc["new_remaining"])),
            ("Adjustment premi dasar", rupiah(calc["base_adjustment"])),
        ]
    else:
        lines = [("Premi dasar FLEXAS", rupiah(calc["new_remaining"]))]
    if calc["extension_adjustment"] != 0:
        lines.append(("Tambahan/adjustment premi perluasan", rupiah(calc["extension_adjustment"])))
    lines += [
        ("Total tambahan / refund premi", rupiah(calc["adjustment"])),
        ("Biaya administrasi", rupiah(calc["admin_fee"])),
        (f"Meterai ({calc['stamp_count']} dokumen)", rupiah(calc["stamp"])),
        ("Jumlah dibayar / (refund)", rupiah(calc["customer_settlement"])),
    ]
    return lines
