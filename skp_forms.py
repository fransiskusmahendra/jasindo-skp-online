from __future__ import annotations
from typing import Any
import pandas as pd
import streamlit as st
from skp_core import default_occ_index, is_single_rate, occ_label, tariff_range, validation_status


CLASS_LABELS = {
    "Kelas 1": "Kelas 1 - konstruksi utama tidak mudah terbakar",
    "Kelas 2": "Kelas 2 - sebagian material mudah terbakar sesuai ketentuan",
    "Kelas 3": "Kelas 3 - selain Kelas 1 dan 2",
}


def construction_for_occ(prefix: str, master: pd.DataFrame, occ_idx: int, label: str = "Kelas konstruksi") -> str:
    row = master.loc[occ_idx]
    if is_single_rate(row):
        st.caption("Tarif khusus OJK - tidak dibedakan menurut kelas konstruksi.")
        return "Khusus"
    return st.selectbox(label, list(CLASS_LABELS), format_func=lambda x: CLASS_LABELS[x], key=f"{prefix}_class")


def occupation_select(prefix: str, master: pd.DataFrame, label: str = "Okupasi", default_code: str = "2976") -> int:
    ids = list(master.index)
    labels = {i: occ_label(master.loc[i]) for i in ids}
    default_id = default_occ_index(master, default_code)
    return st.selectbox(
        label,
        ids,
        index=ids.index(default_id) if default_id in ids else 0,
        format_func=lambda i: labels[i],
        key=f"{prefix}_occ",
        help="Ketik sebagian nama atau kode: rumah, toko, hotel, gudang, laundry, 2976, dll.",
    )


def rate_editor(*, prefix: str, master: pd.DataFrame, occ_idx: int, cls: str, label: str = "Tarif yang dipakai (‰)", old_policy: bool = False) -> dict[str, Any]:
    row = master.loc[occ_idx]
    low, high = tariff_range(row, cls)
    rate = st.number_input(label, min_value=0.0, value=float(low), step=0.001, format="%.3f", key=f"{prefix}_rate")
    status = validation_status(rate, low, high)
    basis = "Range khusus OJK" if is_single_rate(row) else f"Range OJK {cls}"
    if status == "ok":
        st.caption(f"✓ {basis}: {low:.3f}‰ - {high:.3f}‰")
        reason, approved = "", True
    elif old_policy:
        direction = "di bawah" if status == "below" else "di atas"
        st.caption(f"Tarif polis lama {direction} range master saat ini ({low:.3f}‰ - {high:.3f}‰). Tetap gunakan angka yang tercantum di polis lama.")
        reason, approved = "Tarif aktual polis lama", True
    else:
        direction = "di bawah batas bawah" if status == "below" else "di atas batas atas"
        st.warning(f"Tarif {direction} OJK ({low:.3f}‰ - {high:.3f}‰).")
        reason = st.text_input("Dasar/nomor approval underwriting", key=f"{prefix}_reason")
        approved = st.checkbox("Approval underwriting sudah diperoleh", key=f"{prefix}_approved")
    return {"rate": float(rate), "low": low, "high": high, "status": status, "reason": reason, "approved": bool(approved)}


def common_header(prefix: str, idx: int) -> tuple[str, str]:
    st.markdown(f"#### Obyek {idx}")
    c1, c2 = st.columns([1, 1.4])
    name = c1.text_input("Nama obyek", key=f"{prefix}_name", placeholder="Contoh: Ruko Cabang Ende")
    address = c2.text_input("Alamat obyek", key=f"{prefix}_address", placeholder="Alamat lokasi pertanggungan")
    return name, address


def new_condition(prefix: str, master: pd.DataFrame, *, si_label: str, default_code: str = "2976") -> dict[str, Any]:
    c1, c2, c3 = st.columns([1.5, 1, 1.1])
    with c1:
        occ = occupation_select(prefix, master, default_code=default_code)
    with c2:
        cls = construction_for_occ(prefix, master, occ)
    with c3:
        si = st.number_input(si_label, min_value=0.0, step=1_000_000.0, format="%.0f", key=f"{prefix}_si")
    with st.expander("Tarif & validasi OJK", expanded=False):
        row = master.loc[occ]
        st.caption(f"{row['name']} | Kode OJK {row['code']}")
        info = rate_editor(prefix=f"{prefix}_rate", master=master, occ_idx=occ, cls=cls)
    return {"si": float(si), "occ_idx": occ, "class": cls, **info}


def old_condition(prefix: str, master: pd.DataFrame) -> dict[str, Any]:
    c1, c2, c3 = st.columns([1.5, 1, 1.1])
    with c1:
        occ = occupation_select(prefix, master, label="Okupasi lama")
    with c2:
        cls = construction_for_occ(prefix, master, occ, label="Kelas lama")
    with c3:
        si = st.number_input("SI lama", min_value=0.0, step=1_000_000.0, format="%.0f", key=f"{prefix}_si")
    with st.expander("Tarif polis lama", expanded=False):
        st.info("Masukkan tarif yang benar-benar tercantum pada polis lama. Angka ini dipakai untuk menghitung premi sisa lama.")
        info = rate_editor(prefix=f"{prefix}_rate", master=master, occ_idx=occ, cls=cls, label="Tarif polis lama (‰)", old_policy=True)
    return {"si": float(si), "occ_idx": occ, "class": cls, **info}


def blank_condition() -> dict[str, Any]:
    return {"si": 0.0, "occ_idx": None, "class": None, "rate": 0.0, "low": 0.0, "high": 0.0, "status": "ok", "reason": "", "approved": True}


def new_object_form(prefix: str, idx: int, master: pd.DataFrame) -> dict[str, Any]:
    name, address = common_header(prefix, idx)
    new = new_condition(f"{prefix}_new", master, si_label="Nilai pertanggungan (SI)")
    old = blank_condition()
    return {
        "change_type": "new", "name": name, "address": address,
        "old_si": old["si"], "old_occ_idx": old["occ_idx"], "old_class": old["class"], "old_rate": old["rate"], "old_low": old["low"], "old_high": old["high"], "old_status": old["status"], "old_reason": old["reason"], "old_approved": old["approved"],
        "new_si": new["si"], "new_occ_idx": new["occ_idx"], "new_class": new["class"], "new_rate": new["rate"], "new_low": new["low"], "new_high": new["high"], "new_status": new["status"], "new_reason": new["reason"], "new_approved": new["approved"],
    }


def endorsement_object_form(prefix: str, idx: int, master: pd.DataFrame) -> dict[str, Any]:
    name, address = common_header(prefix, idx)
    change = st.radio("Jenis perubahan", ["Perubahan obyek eksisting", "Penambahan obyek baru", "Penghapusan obyek"], horizontal=True, key=f"{prefix}_type")
    old, new = blank_condition(), blank_condition()

    if change != "Penambahan obyek baru":
        st.markdown("**Kondisi sebelum endorsement**")
        old = old_condition(f"{prefix}_old", master)

    if change == "Penghapusan obyek":
        new = blank_condition()
    elif change == "Penambahan obyek baru":
        st.markdown("**Obyek yang ditambahkan**")
        new = new_condition(f"{prefix}_new", master, si_label="SI baru")
    else:
        same = st.checkbox(
            "Okupasi, kelas konstruksi, dan tarif tidak berubah",
            value=True,
            key=f"{prefix}_same",
            help="Biarkan dicentang jika endorsement hanya mengubah SI.",
        )
        if same:
            ns = st.number_input("SI setelah endorsement", min_value=0.0, step=1_000_000.0, format="%.0f", key=f"{prefix}_new_si")
            new = {**old, "si": float(ns)}
        else:
            st.markdown("**Kondisi setelah endorsement**")
            new = new_condition(f"{prefix}_new", master, si_label="SI setelah endorsement")

    st.divider()
    return {
        "change_type": change, "name": name, "address": address,
        "old_si": old["si"], "old_occ_idx": old["occ_idx"], "old_class": old["class"], "old_rate": old["rate"], "old_low": old["low"], "old_high": old["high"], "old_status": old["status"], "old_reason": old["reason"], "old_approved": old["approved"],
        "new_si": new["si"], "new_occ_idx": new["occ_idx"], "new_class": new["class"], "new_rate": new["rate"], "new_low": new["low"], "new_high": new["high"], "new_status": new["status"], "new_reason": new["reason"], "new_approved": new["approved"],
    }
