# data_packages.py

# === Harga & Nama Tampilan Paket Kustom ===
CUSTOM_PACKAGE_PRICES = {
    "XL_XC1PLUS1DISC_EWALLET": {"price_bot": 5000, "display_name": "XC 1+1GB DANA"},
    "XLUNLITURBOTIKTOK_DANA": {"price_bot": 200, "display_name": "ADD ON TIKTOK (DANA)"}, 
    "XLUNLITURBOVIU_DANA": {"price_bot": 200, "display_name": "ADD ON VIU (DANA)"}, 
    "XLUNLITURBOJOOXXC": {"price_bot": 200, "display_name": "ADD ON JOOX (DANA)"}, 
    "XLUNLITURBONETFLIXXC": {"price_bot": 200, "display_name": "ADD ON NETFLIX (DANA)"}, 
    "XLUNLITURBOHPREMIUM7H": {"price_bot": 200, "display_name": "PREMIUM 7H (DANA)"}, 
    "XLUNLITURBOHSUPER7H": {"price_bot": 200, "display_name": "SUPER 7H (DANA)"}, 
    "XLUNLITURBOHBASIC7H": {"price_bot": 200, "display_name": "BASIC 7H (DANA)"}, 
    "XLUNLITURBOHSTANDARD7H": {"price_bot": 200, "display_name": "STANDAR 7H (DANA)"}, 
    "XLUNLITURBOPREMIUMXC": {"price_bot": 200, "display_name": "ADD ON PREMIUM (DANA)"}, 
    "XLUNLITURBOSUPERXC": {"price_bot": 200, "display_name": "ADD ON SUPER (DANA)"}, 
    "XLUNLITURBOBASICXC": {"price_bot": 200, "display_name": "ADD ON BASIC (DANA)"}, 
    "XLUNLITURBOSTANDARDXC": {"price_bot": 200, "display_name": "ADD ON STANDAR (DANA)"}, 
    "WjNMaVEyR0NoNG5SdUhHYWFLbU9RUQ": {"price_bot": 200, "display_name": "BYPAS BASIC"}, 
    "aCtmMVl2YldLZDcvRzhJNlQraTNZdw": {"price_bot": 200, "display_name": "BYPAS STANDARD"}, 
    "eUxzZE9Wa0dmdTdDT1RDeVFyOWJyZw": {"price_bot": 200, "display_name": "BYPAS SUPER"}, 
    "UzhmQk5zam53SUZReWJ3c0poZ0xaQQ": {"price_bot": 200, "display_name": "BYPAS PREMIUM"}, 
    "VlNxbzdGbDRtVnZHUmdwb284R2wzdw": {"price_bot": 200, "display_name": "BYPAS JOOX"}, 
    "SDNuUmJBbWEvMnZSVFRCcEtzQlBFZw": {"price_bot": 200, "display_name": "BYPAS YOUTUBE"}, 
    "MnFpMjJHaXhpU2pweUZ2WWRRM0tYZw": {"price_bot": 200, "display_name": "BYPAS NETFLIX"}, 
    "dlZJSi9kRC85U2tuc3ZaQkVmc1lkQQ": {"price_bot": 200, "display_name": "BYPAS TIKTOK"}, 
    "Tm8vcWtGQ01Kc3h1dlFFdGZqQ3FzUQ": {"price_bot": 200, "display_name": "BYPAS VIU"}, 
    "bStlR1JhcUkrZzlhYmdURWRMNUlaQQ": {"price_bot": 200, "display_name": "BYPAS BASIC 7H"}, 
    "VWM1ZWF0Nk1GQW9MRTEyajJnWFcrdw": {"price_bot": 200, "display_name": "BYPAS STANDARD 7H"}, 
    "N3IvV0NHUEtNUzV6ZlNYR0l0MTNuUQ": {"price_bot": 200, "display_name": "BYPAS PREMIUM 7H"}, 
    "c03be70fb3523ac2ac440966d3a5920e": {"price_bot": 5000, "display_name": "XCP 8GB DANA"}, 
    "bdb392a7aa12b21851960b7e7d54af2c": {"price_bot": 5000, "display_name": "XCP 8GB PULSA"}, 
    "XL_XC1PLUS1DISC_PULSA": {"price_bot": 5000, "display_name": "XC 1+1GB PULSA"}, 
    "XL_XC1PLUS1DISC_QRIS": {"price_bot": 5000, "display_name": "XC 1+1GB QRIS"}, 
    "c03be70fb3523ac2ac440966d3a5920e_QRIS": {"price_bot": 5000, "display_name": "XCP 8GB QRIS"}, 
    "XLUNLITURBOPREMIUMXC_PULSA": {"price_bot": 200, "display_name": "ADD ON PREMIUM (PULSA)"}, 
    "XLUNLITURBOSUPERXC_PULSA": {"price_bot": 200, "display_name": "ADD ON SUPER (PULSA)"}, 
    "XLUNLITURBOBASICXC_PULSA": {"price_bot": 200, "display_name": "ADD ON BASIC (PULSA)"}, 
    "XLUNLITURBOSTANDARDXC_PULSA": {"price_bot": 200, "display_name": "ADD ON STANDAR (PULSA)"}, 
    "XLUNLITURBOVIU_PULSA": {"price_bot": 200, "display_name": "ADD ON VIU (PULSA)"}, 
    "XLUNLITURBOTIKTOK_PULSA": {"price_bot": 200, "display_name": "ADD ON TIKTOK (PULSA)"}, 
    "XLUNLITURBONETFLIXXC_PULSA": {"price_bot": 200, "display_name": "ADD ON NETFLIX (PULSA)"}, 
    "XLUNLITURBOYOUTUBEXC_PULSA": {"price_bot": 200, "display_name": "ADD ON YOUTUBE (PULSA)"}, 
    "XLUNLITURBOJOOXXC_PULSA": {"price_bot": 200, "display_name": "ADD ON JOOX (PULSA)"}, 
    "XLUNLITURBOHPREMIUM7H_P": {"price_bot": 200, "display_name": "PREMIUM 7H (PULSA)"}, 
    "XLUNLITURBOHSUPER7H_P": {"price_bot": 200, "display_name": "SUPER 7H (PULSA)"}, 
    "XLUNLITURBOHBASIC7H_P": {"price_bot": 200, "display_name": "BASIC 7H (PULSA)"}, 
    "XLUNLITURBOHSTANDARD7H_P": {"price_bot": 200, "display_name": "STANDAR 7H (PULSA)"}, 
    "XLUNLITURBOVIDIO_PULSA": {"price_bot": 3000, "display_name": "VIDIO XL (PULSA)"}, 
    "XLUNLITURBOVIDIO_QRIS": {"price_bot": 3000, "display_name": "VIDIO XL (QRIS)"}, 
    "XLUNLITURBOVIDIO_DANA": {"price_bot": 3000, "display_name": "VIDIO XL (DANA)"}, 
    "XLUNLITURBOIFLIXXC_DANA": {"price_bot": 3000, "display_name": "IFLIX XL (DANA)"}, 
    "XLUNLITURBOIFLIXXC_PULSA": {"price_bot": 3000, "display_name": "IFLIX XL (PULSA)"}, 
    "XLUNLITURBOIFLIXXC_QRIS": {"price_bot": 3000, "display_name": "IFLIX XL (QRIS)"},
}

# === Daftar Paket & Urutan ===
ADD_ON_SEQUENCE = [
    {"code": "XLUNLITURBOPREMIUMXC_PULSA", "name": "ADD ON PREMIUM"},
    {"code": "XLUNLITURBOSUPERXC_PULSA", "name": "ADD ON SUPER"},
    # ... (dan seterusnya, salin semua list paket Anda di sini)
]

XCP_8GB_PACKAGE = {"code": "c03be70fb3523ac2ac440966d3a5920e", "name": "XCP 8GB"}
XCP_8GB_PULSA_PACKAGE = {"code": "bdb392a7aa12b21851960b7e7d54af2c", "name": "XCP 8GB PULSA"}

HESDA_PACKAGES = [
    {"id": "WjNMaVEyR0NoNG5SdUhHYWFLbU9RUQ", "name": "BASIC", "price_bot": 200},
    {"id": "aCtmMVl2YldLZDcvRzhJNlQraTNZdw", "name": "STANDARD", "price_bot": 200},
    # ... (dan seterusnya)
]

THIRTY_H_PACKAGES = [
    {"id": "XLUNLITURBOPREMIUMXC_PULSA", "name": "PREMIUM 30H", "price_bot": 200},
    {"id": "XLUNLITURBOSUPERXC_PULSA", "name": "SUPER 30H", "price_bot": 250},
    # ... (dan seterusnya)
]

# === Kode Paket Spesifik ===
XUTS_PACKAGE_CODE = "XLUNLITURBOSUPERXC_PULSA" 
XC1PLUS1GB_PULSA_CODE = "XL_XC1PLUS1DISC_PULSA"
XC1PLUS1GB_DANA_CODE = "XL_XC1PLUS1DISC_EWALLET"
XC1PLUS1GB_QRIS_CODE = "XL_XC1PLUS1DISC_QRIS" 

XUTP_INITIAL_PACKAGE_CODE = "XLUNLITURBOPREMIUMXC_PULSA"
XCP_8GB_DANA_CODE_FOR_XUTP = "c03be70fb3523ac2ac440966d3a5920e" 
XCP_8GB_PULSA_CODE_FOR_XUTP = "bdb392a7aa12b21851960b7e7d54af2c" 
XCP_8GB_QRIS_CODE_FOR_XUTP = "c03be70fb3523ac2ac440966d3a5920e_QRIS"
