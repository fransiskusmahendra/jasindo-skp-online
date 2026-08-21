from __future__ import annotations
from datetime import date
from pathlib import Path
import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta
from skp_core import calculate, invalid_approvals, load_master, roman_month, rupiah
from skp_exports import build_docx, build_pdf
from skp_forms import endorsement_object_form, new_object_form

BASE_DIR=Path(__file__).parent
st.set_page_config(page_title="SKP Online - Surat Konfirmasi Premi",page_icon="📄",layout="wide")
st.markdown("""<style>.block-container{padding-top:1.4rem;padding-bottom:2rem;max-width:1180px}[data-testid="stMetricValue"]{font-size:1.45rem}</style>""",unsafe_allow_html=True)

@st.cache_data
def get_master(): return load_master(BASE_DIR)

def settings_panel():
    with st.sidebar:
        st.markdown("### SKP Online"); st.caption("Property/FLEXAS & endorsement")
        with st.expander("⚙️ Pengaturan Internal / PKS",expanded=False):
            admin=st.number_input("Biaya polis / endorsement",min_value=0.0,value=20_000.0,step=5_000.0,format="%.0f")
            stamp=st.number_input("Nilai meterai / dokumen",min_value=0.0,value=10_000.0,step=1_000.0,format="%.0f")
            threshold=st.number_input("Threshold meterai tambahan",min_value=0.0,value=5_000_000.0,step=500_000.0,format="%.0f")
            fee=st.number_input("Fee bank (%)",min_value=0.0,max_value=100.0,value=15.0,step=.5)
            vat=st.number_input("PPN efektif atas fee (%)",min_value=0.0,max_value=100.0,value=11.0,step=.5)
            deduct=st.checkbox("Potong biaya admin & meterai dari refund",value=False)
            st.caption("Parameter ini mengikuti SOP/PKS internal, bukan rate okupasi OJK.")
    return {"admin_fee":admin,"stamp_each":stamp,"stamp_threshold":threshold,"fee_pct":fee,"vat_pct":vat,"deduct_refund_costs":deduct}

def letter_fields(prefix):
    today=date.today(); c1,c2,c3=st.columns([1.2,.7,1.2])
    number=c1.text_input("Nomor SKP",value=f"001/SKP/{roman_month(today.month)}/{today.year}",key=f"{prefix}_number")
    letter_date=c2.date_input("Tanggal surat",value=today,key=f"{prefix}_date")
    to=c3.text_input("Kepada",key=f"{prefix}_to",placeholder="Bank / mitra / tertanggung")
    c4,c5=st.columns([1,1.5]); insured=c4.text_input("Nama tertanggung",key=f"{prefix}_insured"); address=c5.text_input("Alamat tertanggung",key=f"{prefix}_address")
    signer=st.text_input("Nama penandatangan",value="",placeholder="Nama pejabat",key=f"{prefix}_signer")
    return {"number":number,"letter_date":letter_date,"to":to,"insured":insured,"insured_address":address,"signer":signer}

def render_result(data,calc,key):
    st.markdown("### Hasil Perhitungan")
    c1,c2,c3=st.columns(3)
    if data["mode"]=="Endorsement":
        label="Tambahan Premi" if calc["adjustment"]>0 else ("Refund Premi" if calc["adjustment"]<0 else "Adjustment Premi")
        c1.metric(label,rupiah(abs(calc["adjustment"]))); c2.metric("Jumlah dibayar / (refund)",rupiah(calc["customer_settlement"])); c3.metric("Sisa periode",f"{calc['period_days']} hari")
    else:
        c1.metric("Premi",rupiah(calc["adjustment"])); c2.metric("Jumlah dibayar",rupiah(calc["customer_settlement"])); c3.metric("Periode",f"{calc['period_days']} hari")
    with st.expander("Lihat rincian perhitungan",expanded=False):
        if data["mode"]=="Endorsement": st.write({"Premi polis lama":rupiah(calc["old_full"]),"Premi sudah berjalan":rupiah(calc["old_earned"]),"Premi sisa lama":rupiah(calc["old_remaining"]),"Premi sisa kondisi baru":rupiah(calc["new_remaining"]),"Adjustment premi dasar":rupiah(calc["base_adjustment"]),"Adjustment perluasan":rupiah(calc["extension_adjustment"])})
        st.dataframe(pd.DataFrame(calc["rows"]),use_container_width=True,hide_index=True)
    with st.expander("Rincian internal: biaya, meterai & fee",expanded=False):
        a,b,c,d=st.columns(4); a.metric("Biaya admin",rupiah(calc["admin_fee"])); b.metric("Meterai",rupiah(calc["stamp"])); c.metric("Fee gross",rupiah(calc["fee_gross"])); d.metric("Fee net",rupiah(calc["fee_net"])); st.caption(f"PPN dalam fee: {rupiah(calc['vat_component'])}")
    a,b=st.columns(2); a.download_button("⬇️ Download Word",build_docx(data,calc),file_name=f"SKP_{key}.docx",mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",use_container_width=True); b.download_button("⬇️ Download PDF",build_pdf(data,calc),file_name=f"SKP_{key}.pdf",mime="application/pdf",use_container_width=True)

def main():
    master=get_master(); settings=settings_panel()
    st.title("📄 SKP Online"); st.caption("Pilih okupasi, isi nilai pertanggungan, lalu hitung. Validasi OJK dan prorata berjalan otomatis di belakang layar.")
    tnew,tend,tmaster=st.tabs(["📝 SKP Baru","🔄 Endorsement","🔎 Master Okupasi"])
    with tnew:
        st.markdown("### 1. Data SKP"); base=letter_fields("new"); a,b=st.columns(2); start=a.date_input("Mulai pertanggungan",value=date.today(),key="new_start"); end=b.date_input("Akhir pertanggungan",value=date.today()+relativedelta(years=1),key="new_end")
        st.markdown("### 2. Obyek Pertanggungan"); n=st.number_input("Jumlah obyek",1,20,1,1,key="new_n"); objects=[new_object_form(f"new_ob_{i}",i,master) for i in range(1,int(n)+1)]
        with st.expander("Premi perluasan (opsional)",expanded=False): extension=st.number_input("Tambahan premi perluasan",value=0.0,step=10_000.0,format="%.0f",key="new_ext"); st.caption("Isi hanya bila premi perluasan sudah dihitung/di-approve terpisah.")
        if st.button("Hitung Premi",type="primary",use_container_width=True,key="new_calc"):
            errors=invalid_approvals(objects)
            if any(o["new_si"]<=0 for o in objects): errors.append("Nilai pertanggungan setiap obyek harus lebih dari 0.")
            if errors:
                for e in errors: st.error(e)
            else:
                try: data={"mode":"SKP Baru",**base,"start":start,"end":end,"objects":objects,"extension_adjustment":float(extension)}; st.session_state["new_result"]=(data,calculate(data,settings,master))
                except ValueError as exc: st.error(str(exc))
        if "new_result" in st.session_state: render_result(*st.session_state["new_result"],"baru")
    with tend:
        st.markdown("### 1. Data Endorsement"); base=letter_fields("end"); a,b=st.columns(2); policy=a.text_input("Nomor polis lama",key="end_policy"); effective=b.date_input("Tanggal efektif endorsement",value=date.today(),key="end_effective")
        a,b,c=st.columns(3); old_start=a.date_input("Awal polis lama",value=date.today()-relativedelta(months=6),key="end_old_start"); old_end=b.date_input("Akhir polis lama",value=date.today()+relativedelta(months=6),key="end_old_end"); new_end=c.date_input("Akhir polis setelah endorsement",value=date.today()+relativedelta(months=6),key="end_new_end")
        st.markdown("### 2. Perubahan Obyek"); st.caption("Jika hanya SI yang berubah, biarkan opsi okupasi/kelas/tarif tidak berubah tetap dicentang."); n=st.number_input("Jumlah obyek yang berubah",1,20,1,1,key="end_n"); objects=[endorsement_object_form(f"end_ob_{i}",i,master) for i in range(1,int(n)+1)]
        with st.expander("Adjustment premi perluasan (opsional)",expanded=False): extension=st.number_input("Tambahan (+) / refund (-) premi perluasan",value=0.0,step=10_000.0,format="%.0f",key="end_ext")
        if st.button("Hitung Endorsement",type="primary",use_container_width=True,key="end_calc"):
            errors=invalid_approvals(objects)
            for i,o in enumerate(objects,1):
                if o["change_type"]!="Penambahan obyek baru" and o["old_si"]<=0: errors.append(f"Obyek {i}: SI lama harus lebih dari 0.")
                if o["change_type"]!="Penghapusan obyek" and o["new_si"]<=0: errors.append(f"Obyek {i}: SI baru harus lebih dari 0.")
            if errors:
                for e in errors: st.error(e)
            else:
                try: data={"mode":"Endorsement",**base,"old_policy_no":policy,"old_start":old_start,"old_end":old_end,"effective":effective,"new_end":new_end,"objects":objects,"extension_adjustment":float(extension)}; st.session_state["end_result"]=(data,calculate(data,settings,master))
                except ValueError as exc: st.error(str(exc))
        if "end_result" in st.session_state: render_result(*st.session_state["end_result"],"endorsement")
    with tmaster:
        st.markdown("### Master Okupasi OJK")
        st.caption(f"{len(master)} baris okupasi bertarif dari SEOJK 6/SEOJK.05/2017 Lampiran I Tabel I.A. Kategori induk tanpa tarif tidak dapat dipilih.")
        q=st.text_input("Cari okupasi",placeholder="Contoh: rumah, toko, gudang, hotel, farmasi, sawmill, 2976")
        cats=["Semua"]+sorted(master["category"].dropna().unique().tolist()); cat=st.selectbox("Kategori",cats); view=master.copy()
        if q: view=view[view[["code","name","alias"]].astype(str).apply(lambda col:col.str.contains(q,case=False,na=False)).any(axis=1)]
        if cat!="Semua": view=view[view["category"]==cat]
        show=view[["code","alias","name","category","rate_basis","k1_low","k1_high","k2_low","k2_high","k3_low","k3_high"]].copy()
        show["Basis tarif"]=show["rate_basis"].map({"construction":"Kelas 1/2/3","single":"Khusus (tanpa kelas)"})
        show["Kelas 1 / Khusus"]=show.apply(lambda r:f"{r.k1_low:.3f} - {r.k1_high:.3f}‰",axis=1)
        show["Kelas 2"]=show.apply(lambda r:"-" if r.rate_basis=="single" else f"{r.k2_low:.3f} - {r.k2_high:.3f}‰",axis=1)
        show["Kelas 3"]=show.apply(lambda r:"-" if r.rate_basis=="single" else f"{r.k3_low:.3f} - {r.k3_high:.3f}‰",axis=1)
        show=show[["code","alias","name","category","Basis tarif","Kelas 1 / Khusus","Kelas 2","Kelas 3"]]
        show.columns=["Kode","Nama mudah","Nama OJK","Kategori","Basis tarif","Kelas 1 / Khusus","Kelas 2","Kelas 3"]
        st.dataframe(show,use_container_width=True,hide_index=True)
        with st.expander("Panduan kelas konstruksi",expanded=False):
            st.markdown("**Kelas 1:** struktur utama dan atap tidak mudah terbakar.\n\n**Kelas 2:** seperti Kelas 1 dengan toleransi material mudah terbakar sesuai ketentuan.\n\n**Kelas 3:** selain Kelas 1 dan Kelas 2.\n\nUntuk okupasi berlabel **Khusus**, aplikasi tidak meminta kelas konstruksi karena Tabel I.A memberikan satu range tarif.")
        st.info("Master ini untuk rate dasar Property/FLEXAS. Perluasan seperti banjir atau gempa tetap dihitung dengan dasar/zona tersendiri dan dimasukkan sebagai premi perluasan bila diperlukan.")

if __name__=="__main__": main()
