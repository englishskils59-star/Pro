# classification_engine.py
# WDI Visit Analytics Engine
# Rule-based keyword scoring classification — NO AI, NO ML, fully offline.

import pandas as pd
import numpy as np
from datetime import datetime
import re
from utils import normalize_arabic, safe_str, days_since

# ═══════════════════════════════════════════════════════════════════
# KEYWORD SCORING TABLES
# ═══════════════════════════════════════════════════════════════════

KEYWORD_RULES: list[dict] = [
    # ── CURRENT CUSTOMER  (+100) ──────────────────────────────────
    {"keyword": "تم الطلب",            "status": "current",      "score": 100},
    {"keyword": "تم السحب",            "status": "current",      "score": 100},
    {"keyword": "شغال الوادي",         "status": "current",      "score": 100},
    {"keyword": "شراء",                "status": "current",      "score": 100},
    {"keyword": "استلام",              "status": "current",      "score": 100},
    {"keyword": "طلب كمية",            "status": "current",      "score": 100},
    {"keyword": "طلب طن",              "status": "current",      "score": 100},
    {"keyword": "فاتورة",              "status": "current",      "score": 100},
    {"keyword": "عميل حالي",           "status": "current",      "score": 100},
    {"keyword": "يعمل معنا",           "status": "current",      "score": 100},
    {"keyword": "طلب جديد",            "status": "current",      "score": 100},
    {"keyword": "متابعة توريد",        "status": "current",      "score": 100},
    {"keyword": "تم التواصل تليفونيا لطلب اوردر",   "status": "current",      "score": 100},
    {"keyword": "تمت زيارته بغرض زيادة السحب",        "status": "current",      "score": 100},
    {"keyword": "اشترى",               "status": "current",      "score": 100},
    {"keyword": "طلب علف",             "status": "current",      "score": 100},
    {"keyword": "طلب شكاير",           "status": "current",      "score": 100},
    {"keyword": "تم التوريد",          "status": "current",      "score": 100},
    {"keyword": "استلم",               "status": "current",      "score": 100},
    {"keyword": "دفع",                 "status": "current",      "score": 100},
    {"keyword": "بيشتري منا",          "status": "current",      "score": 100},
    {"keyword": "عميل فعلي",           "status": "current",      "score": 100},
    {"keyword": "متابعة",              "status": "current",      "score": 100},
    {"keyword": "تم تحميل",              "status": "current",      "score": 100},
    {"keyword": "تم تنزيل",              "status": "current",      "score": 100},
    {"keyword": "تم الاتفاق على طلبية",              "status": "current",      "score": 100},
    {"keyword": "طلب نقلة",              "status": "current",      "score": 100},
    {"keyword": "طلب بضاعة",              "status": "current",      "score": 100},
    {"keyword": "زيادة استخدام علف الوادي",              "status": "current",      "score": 100},
    {"keyword": "شغال علف بريمو الوادي",              "status": "current",      "score": 100},
    {"keyword": "سيتم تحميل بضاعة",              "status": "current",      "score": 100},
    {"keyword": "التنسيق لسحب نقلة",              "status": "current",      "score": 100},
    {"keyword": "تم طلب",              "status": "current",      "score": 100},
    {"keyword": "تم مراجعه المخازن",                 "status": "current",      "score": 100},
    {"keyword": "تظبيط الشغل",                 "status": "current",      "score": 100},
    {"keyword": "تم سحب",                 "status": "current",      "score": 100},
    {"keyword": "تم توريد",                 "status": "current",      "score": 100},
    {"keyword": "تم الاتفاق على طلب",                 "status": "current",      "score": 100},
    {"keyword": "الضغط لطلب بضاعه",                 "status": "current",      "score": 100},
    {"keyword": "بيسحب الوادي",                 "status": "current",      "score": 100},
    {"keyword": "طلب وش",                 "status": "current",      "score": 100},
    {"keyword": "يتعامل مع علف الوادى",              "status": "current",      "score": 100},
    {"keyword": "سحب كميه",              "status": "current",      "score": 100},
    {"keyword": "بيوكل الوادي",              "status": "current",      "score": 100},
    {"keyword":"اوردر","status":"current","score":100},
    {"keyword":"طلبيه","status":"current","score":100},
    {"keyword":"تم الاتفاق على تنزيل","status":"current","score":100},
    {"keyword":"تحميل نقله","status":"current","score":100},
    {"keyword":"تجهيز الاوردر","status":"current","score":100},
    {"keyword":"زياده الكميه","status":"current","score":100},
    {"keyword":"تم الاتفاق على الكميه","status":"current","score":100},
    {"keyword":"سحب اوردر","status":"current","score":100},
    {"keyword":"تشغيل الوادي","status":"current","score":100},
    {"keyword": "موجود لديه",                "status": "current", "score": 80},
    {"keyword": "متبقي عنده",                "status": "current", "score": 80},
    {"keyword": "خلص عنده",                  "status": "current", "score": 80},
    {"keyword": "بالمخزن",                   "status": "current", "score": 70},
    {"keyword": "لديه بالمخزن",              "status": "current", "score": 80},
    {"keyword": "طلب طن",                    "status": "current", "score": 100},
    {"keyword": "طلب جامبو",                 "status": "current", "score": 100},
    {"keyword": "طلب نقله",                  "status": "current", "score": 100},
    {"keyword": "طلب حموله",                 "status": "current", "score": 100},
    {"keyword": "تجهيز حموله",               "status": "current", "score": 100},
    {"keyword": "هيطلب",                     "status": "current", "score": 80},
    {"keyword": "هينزل",                     "status": "current", "score": 80},
    {"keyword": "باع الدورة",                "status": "current", "score": 80},
    {"keyword": "خلص الدوره",                "status": "current", "score": 80},
    {"keyword": "هيطهر وينزل",               "status": "current", "score": 90},
    {"keyword": "تحويل المبلغ",              "status": "current", "score": 100},
    {"keyword": "وتم تحويل المبلغ",          "status": "current", "score": 100},
    {"keyword": "جارى الاتفاق مع جامبو",     "status": "current", "score": 100},
    {"keyword": "زياده المسحوبات",            "status": "current", "score": 90},
    {"keyword": "زيادة المسحوبات",            "status": "current", "score": 90},
    {"keyword": "زياده السحب",               "status": "current", "score": 90},
    {"keyword": "زيادة السحب",               "status": "current", "score": 90},
    {"keyword": "التنسيق لزيادة الكميات",    "status": "current", "score": 90},
    {"keyword": "التنسيق لزيادة المسحوبات",  "status": "current", "score": 90},
    {"keyword": "تم الضغط على التاجر",       "status": "current", "score": 80},
    {"keyword": "متابعه المخزن",             "status": "current", "score": 80},
    {"keyword": "متابعت العميل و المخزن",    "status": "current", "score": 80},
    {"keyword": "تم التواصل مع العميل",      "status": "current", "score": 70},
    {"keyword": "تم بدء العمل من الوكيل",   "status": "current", "score": 100},
    {"keyword": "بدء العمل من الوكيل",      "status": "current", "score": 100},
    {"keyword": "تم الاتفاق على عمل نقله",   "status": "current", "score": 100},
    {"keyword": "طلبات التكويد",             "status": "current", "score": 100},
    {"keyword": "هيبعت طلبات التكويد",       "status": "current", "score": 100},
    {"keyword": "تفريده",                    "status": "current", "score": 90},
    {"keyword": "ترتيب التفريده",            "status": "current", "score": 100},
 
    # ── POTENTIAL CUSTOMER  (+60) ─────────────────────────────────
    {"keyword": "مهتم",                "status": "potential",    "score": 60},
    {"keyword": "يفكر",                "status": "potential",    "score": 60},
    {"keyword": "تجربة",               "status": "potential",    "score": 60},
    {"keyword": "موعد",                "status": "potential",    "score": 60},
    {"keyword": "يرغب",                "status": "potential",    "score": 60},
    {"keyword": "طلب عرض سعر",         "status": "potential",    "score": 60},
    {"keyword": "يريد تجربة",          "status": "potential",    "score": 60},
    {"keyword": "مقابلة قادمة",        "status": "potential",    "score": 60},
    {"keyword": "زيارة ثانية",         "status": "potential",    "score": 60},
    {"keyword": "محتمل",               "status": "potential",    "score": 60},
    {"keyword": "محتاج خصم أعلى",      "status": "potential",        "score": 60},
    {"keyword": "تظبيط الخصومات",      "status": "potential",        "score": 60},
    {"keyword": "اقتنع",               "status": "potential",    "score": 60},
    {"keyword": "مقتنع",               "status": "potential",    "score": 60},
    {"keyword": "اقتنع بالمنتج",       "status": "potential",    "score": 60},
    {"keyword": "اقتنع بالعلف",        "status": "potential",    "score": 60},
    {"keyword": "عايز يجرب",           "status": "potential",    "score": 60},
    {"keyword": "هيفكر",               "status": "potential",    "score": 60},
    {"keyword": "مش رافض",             "status": "potential",    "score": 60},
    {"keyword": "شكاير",               "status": "potential",    "score": 40},
    {"keyword": "عرض سعر",             "status": "potential",    "score": 60},
    {"keyword": "اعتراض على السعر",    "status": "potential",    "score": 40},
    {"keyword": "اعتراض على الكاش",    "status": "potential",    "score": 40},
    {"keyword": "مشكلة الكاش",         "status": "potential",    "score": 40},
    {"keyword": "بيشتغل اجل",          "status": "potential",    "score": 40},
    {"keyword": "نظام الاجل",          "status": "potential",    "score": 40},
    {"keyword": "يشتغل كاش",           "status": "potential",    "score": 30},
    {"keyword": "متحمس للعمل",                "status": "potential",    "score": 60},
    {"keyword": "موافقة مبدئية",                "status": "potential",    "score": 60},
    {"keyword": "سيتم البدء",                "status": "potential",    "score": 60},
    {"keyword": "ممكن يبدأ",                "status": "potential",    "score": 60},
    {"keyword": "هيبدأ معنا",                "status": "potential",    "score": 60},
    {"keyword": "ينوى العمل معنا",                "status": "potential",    "score": 60},
    {"keyword": "يريد العمل",                "status": "potential",    "score": 60},
    {"keyword": "طلب تجربة",                "status": "potential",    "score": 60},
    {"keyword": "يجرب معنا",                "status": "potential",    "score": 60},
    {"keyword": "سيتم التواصل",                "status": "potential",    "score": 60},
    {"keyword": "سيتم تكرار الزيارة",                "status": "potential",    "score": 60},
    {"keyword": "التفكير في العرض",                "status": "potential",    "score": 60},
    {"keyword": "يريد خصم أكبر",                "status": "potential",    "score": 60},
    {"keyword": "عند انتهاء الدورة",                "status": "potential",    "score": 60},
    {"keyword": "إن شاء الله ندخل الوادى",               "status": "potential",    "score": 60},
    {"keyword": "ان شاء الله ندخل الوادى",               "status": "potential",    "score": 60},
    {"keyword": "اتفقنا",               "status": "potential",    "score": 60},
    {"keyword": "تم الاتفاق معه",               "status": "potential",    "score": 60},
    {"keyword": "الاتفاق على بداية العمل",               "status": "potential",    "score": 60},
    {"keyword": "جاهز للعمل",               "status": "potential",    "score": 60},
    {"keyword": "سيبدأ معنا",               "status": "potential",    "score": 60},
    {"keyword": "الاتفاق على بداية شغل في الوادي",               "status": "potential",    "score": 40},
    {"keyword": "متحمس للعمل",               "status": "potential",    "score": 40},
    {"keyword": "منتظر تحسن",               "status": "potential",    "score": 40},
    {"keyword": "ليس لديه مانع",               "status": "potential",    "score": 40},
    {"keyword": "لا يمانع",               "status": "potential",    "score": 40},
    {"keyword": "وعد بتوفير",               "status": "potential",    "score": 40},
    {"keyword": "منفتح على العمل",                "status": "potential",    "score": 60},
    {"keyword": "هيجربتم الاتفاق على",                "status": "potential",    "score": 60},
    {"keyword": "سيبدأ معنا",                "status": "potential",    "score": 60},
    {"keyword":"مستني انتهاء الدوره","status":"potential","score":60},
    {"keyword":"بعد انتهاء الدوره","status":"potential","score":60},
    {"keyword":"سيجرب","status":"potential","score":60},
    {"keyword":"سيتم التجربه","status":"potential","score":60},
    {"keyword":"هيبدأ بعد","status":"potential","score":60},
    {"keyword":"في حال نجاح التجربه","status":"potential","score":60},
    {"keyword":"طلب التواصل لاحقا","status":"potential","score":60},
    {"keyword":"وعد بالتجربه","status":"potential","score":60},
    {"keyword":"موافق على التجربه","status":"potential","score":60},
    {"keyword":"مهتم بالسعر","status":"potential","score":60},
    {"keyword":"منتظر انتهاء العنبر","status":"potential","score":60},
    {"keyword":"بعد بيع الدوره","status":"potential","score":60},
    {"keyword": "سيتم التنسيق",              "status": "potential", "score": 60},
    {"keyword": "تم التفاوض",                "status": "potential", "score": 60},
    {"keyword": "تم ترتيب ميعاد",            "status": "potential", "score": 60},
    {"keyword": "ترتيب ميعاد",               "status": "potential", "score": 60},
    {"keyword": "سيتم متابعته",              "status": "potential", "score": 50},
    {"keyword": "هيتم التواصل",              "status": "potential", "score": 50},
    {"keyword": "هيتم البدء",                "status": "potential", "score": 60},
    {"keyword": "هيتم التنفيذ",              "status": "potential", "score": 60},
    {"keyword": "في الفتره القادمه",          "status": "potential", "score": 50},
    {"keyword": "الفترة القادمة",             "status": "potential", "score": 50},
    {"keyword": "خلال ايام",                 "status": "potential", "score": 60},
    {"keyword": "خلال اسبوع",               "status": "potential", "score": 60},
    {"keyword": "الاسبوع القادم",            "status": "potential", "score": 60},
    {"keyword": "الشهر القادم",              "status": "potential", "score": 50},
    {"keyword": "باذن الله",                 "status": "potential", "score": 40},
    {"keyword": "بأذن الله",                 "status": "potential", "score": 40},
    {"keyword": "ان شاء الله",              "status": "potential", "score": 40},
    {"keyword": "إن شاء الله",              "status": "potential", "score": 40},
    {"keyword": "مستعد للبدء",               "status": "potential", "score": 60},
    {"keyword": "مستعد للتعامل",             "status": "potential", "score": 60},
    {"keyword": "مستعد يوفر",               "status": "potential", "score": 60},
    {"keyword": "وعد بالبدء",               "status": "potential", "score": 60},
    {"keyword": "وعد بالتعامل",             "status": "potential", "score": 60},
    {"keyword": "وعد أيضاً",               "status": "potential", "score": 50},
    {"keyword": "قرب جدا ياخد قرار",        "status": "potential", "score": 60},
    {"keyword": "سيتم البدء بعد",           "status": "potential", "score": 60},
    {"keyword": "هيبدا بعد",                "status": "potential", "score": 60},
    {"keyword": "هيبدا يدخل",               "status": "potential", "score": 60},
    {"keyword": "ممكن يسحب",               "status": "potential", "score": 60},
    {"keyword": "ممكن يشتغل",              "status": "potential", "score": 60},
    {"keyword": "ممكن يجرب",              "status": "potential", "score": 60},
    {"keyword": "ممكن يبدأ",              "status": "potential", "score": 60},
    {"keyword": "هيجرب في عنبر",           "status": "potential", "score": 60},
    {"keyword": "يجرب العلف",             "status": "potential", "score": 60},
    {"keyword": "اقناع العميل بالبدء",     "status": "potential", "score": 60},
    {"keyword": "تم اقناعه بالمنتج",       "status": "potential", "score": 60},
    {"keyword": "تم إقناعه بالعلف",        "status": "potential", "score": 60},
    {"keyword": "اقناع العميل بالعمل",     "status": "potential", "score": 60},
    {"keyword": "تم اقناع العميل",         "status": "potential", "score": 60},
    {"keyword": "تم إقناع العميل",         "status": "potential", "score": 60},
    {"keyword": "ابدى ترحيب",              "status": "potential", "score": 60},
    {"keyword": "ابدي نية",               "status": "potential", "score": 50},
    {"keyword": "يبدي نية",               "status": "potential", "score": 50},
    {"keyword": "نية في إدخال المنتج",    "status": "potential", "score": 50},
 
    # ينتظر ظروف السوق / نهاية الدورة
    {"keyword": "مع تحرك السوق",           "status": "potential", "score": 50},
    {"keyword": "بعد استقرار السوق",       "status": "potential", "score": 50},
    {"keyword": "مع استقرار الاسعار",      "status": "potential", "score": 50},
    {"keyword": "بعد ثبات الاسعار",       "status": "potential", "score": 50},
    {"keyword": "بعد خروج الدوره",        "status": "potential", "score": 50},
    {"keyword": "بعد انتهاء الدوره",      "status": "potential", "score": 50},
    {"keyword": "مستني انتهاء الدوره",    "status": "potential", "score": 50},
    {"keyword": "منتظر نزول الكتكوت",     "status": "potential", "score": 50},
    {"keyword": "منتظر سعر الكتكوت",      "status": "potential", "score": 50},
    {"keyword": "مع نزول سعر الكتكوت",    "status": "potential", "score": 50},
 
    # اعتراض على خصم / سعر = محتمل وليس رافضاً
    {"keyword": "معترض ع الخصم",          "status": "potential", "score": 40},
    {"keyword": "اعترض علي الخصم",        "status": "potential", "score": 40},
    {"keyword": "محتاج خصم",              "status": "potential", "score": 40},
    {"keyword": "تظبيط الخصم",            "status": "potential", "score": 40},
    {"keyword": "لو تم تظبيط الخصم",      "status": "potential", "score": 50},
    {"keyword": "يقارن الاسعار",          "status": "potential", "score": 40},
    {"keyword": "هيقارن الاسعار",         "status": "potential", "score": 40},
    {"keyword": "دراسة الفرق",            "status": "potential", "score": 40},
    {"keyword": "مدة سداد",              "status": "potential", "score": 40},
    {"keyword": "فتح مدة سداد",          "status": "potential", "score": 40},
    {"keyword": "لو في امكانية",          "status": "potential", "score": 40},
    {"keyword": "لو وجد التمويل",         "status": "potential", "score": 40},
    {"keyword": "ليس لديه سيوله",         "status": "potential", "score": 40},
    {"keyword": "ليس لديه سيولة",         "status": "potential", "score": 40},
    {"keyword": "ليس لديه مشاكل",         "status": "potential", "score": 50},
 
    # زيارة تمهيدية مع نتيجة ايجابية
    {"keyword": "تم الحديث عن علف الوادي","status": "potential", "score": 50},
    {"keyword": "تكلمنا عن توفير علف",    "status": "potential", "score": 50},
    {"keyword": "تم التركيز معه",         "status": "potential", "score": 40},
    {"keyword": "تم توضيح الفرق",         "status": "potential", "score": 40},
    {"keyword": "محاوله اقناع",           "status": "potential", "score": 40},
    {"keyword": "محاولة اقناع",           "status": "potential", "score": 40},
    {"keyword": "محاولة إقناع",           "status": "potential", "score": 40},
    {"keyword": "عجبته الاسعار",          "status": "potential", "score": 50},
    {"keyword": "عجبته الأسعار",          "status": "potential", "score": 50},
    {"keyword": "متخوف من نزول",          "status": "potential", "score": 40},
    {"keyword": "خائف من نزول",           "status": "potential", "score": 40},
    # ── TARGET CUSTOMER  (+40) ────────────────────────────────────
    {"keyword": "شغال نيوهوب",         "status": "target",       "score": 40},
    {"keyword": "شغال هرمان",          "status": "target",       "score": 40},
    {"keyword": "شغال الإيمان",        "status": "target",       "score": 40},
    {"keyword": "شغال منافس",          "status": "target",       "score": 40},
    {"keyword": "شغال شركة أخرى",      "status": "target",       "score": 40},
    {"keyword": "يتعامل مع شركة أخرى", "status": "target",       "score": 40},
    {"keyword": "لديه مورد حالي",      "status": "target",       "score": 40},
    {"keyword": "تعارف",               "status": "target",        "score": 40},
    {"keyword": "بيعمل بعلف الإيمان",  "status": "target",       "score": 40},
    {"keyword": "شغال الإيمان",         "status": "target",       "score": 40},
    {"keyword": "بيعمل بعلف السلام",   "status": "target",       "score": 40},
    {"keyword": "شغال السلام",          "status": "target",       "score": 40},
    {"keyword": "بيعمل بعلف المجد",    "status": "target",       "score": 40},
    {"keyword": "شغال المجد",           "status": "target",       "score": 40},
    {"keyword": "فيدميكس",             "status": "target",       "score": 40},
    {"keyword": "بيعمل بعلف",          "status": "target",       "score": 40},
    {"keyword": "يتعامل بعلف",         "status": "target",       "score": 40},
    {"keyword": "مورد تاني",           "status": "target",       "score": 40},
    {"keyword": "شغال نيوهوب",         "status": "target",       "score": 40},
    {"keyword": "يتعامل مع علف",          "status": "target",       "score": 40},
    {"keyword": "شغال علف",          "status": "target",       "score": 40},
    {"keyword": "يستخدم علف",          "status": "target",       "score": 40},
    {"keyword": "يعمل بعلف",          "status": "target",       "score": 40},
    {"keyword": "شركة أخرى",          "status": "target",       "score": 40},
    {"keyword": "مورد حالي",          "status": "target",       "score": 40},
    {"keyword": "شغال BT",          "status": "target",       "score": 40},
    {"keyword": "شغال مكة",          "status": "target",       "score": 40},
    {"keyword": "شغال الفجر",          "status": "target",       "score": 40},
    {"keyword": "زيارة تسويقية",               "status": "target",        "score": 40},
    {"keyword": "عرض المنتج",               "status": "target",        "score": 40},
    {"keyword": "شرح المنتج",               "status": "target",        "score": 40},
    {"keyword": "التعريف بالشركة",               "status": "target",        "score": 40},
    {"keyword": "أول زيارة",               "status": "target",        "score": 40},
    {"keyword": "التعرف على",               "status": "target",        "score": 40},
    {"keyword": "ليس لديه مانع ولكن",               "status": "target",        "score": 40},
    {"keyword": "لا يمانع",                 "status": "target","score": 40},
    {"keyword": "بيوكل الايمان",             "status": "target",       "score": 40},
    {"keyword": "بيوكل الفجر",             "status": "target",       "score": 40},
    {"keyword": "بيوكل نيوهوب",             "status": "target",       "score": 40},
    {"keyword": "بيوكل بي تي",             "status": "target",       "score": 40},
    {"keyword": "بيوكل علف",             "status": "target",       "score": 40},
    {"keyword": "شغال هيرمان",             "status": "target",       "score": 40},
    {"keyword": "شغال نماء",             "status": "target",       "score": 40},
    {"keyword": "شغال هايدا",             "status": "target",       "score": 40},
    {"keyword": "شغال الصلاح",             "status": "target",       "score": 40},
    {"keyword": "شغال العبور",             "status": "target",       "score": 40},
    {"keyword": "شغال القائد",             "status": "target",       "score": 40},
    {"keyword": "شغال فيدمكس",             "status": "target",       "score": 40},
    {"keyword": "شغال وادي النيل",             "status": "target",       "score": 40},
    {"keyword": "عنبر، بريمو، تم الاتفاق معه",               "status": "target",        "score": 40},
    {"keyword": "مربى، بريمو، تم الاتفاق معه",               "status": "target",        "score": 40},
    {"keyword":"شغال هايدا","status":"target","score":40},
    {"keyword":"شغال بي تي","status":"target","score":40},
    {"keyword":"شغال مكه","status":"target","score":40},
    {"keyword":"شغال الوادي للنيل","status":"target","score":40},
    {"keyword": "علف الاهرام",            "status": "target", "score": 40},
    {"keyword": "علف ابو هاشم",          "status": "target", "score": 40},
    {"keyword": "علف الزعيم",             "status": "target", "score": 40},
    {"keyword": "علف الامانة",            "status": "target", "score": 40},
    {"keyword": "علف الأمانة",            "status": "target", "score": 40},
    {"keyword": "علف البركة",             "status": "target", "score": 40},
    {"keyword": "علف الشروق",             "status": "target", "score": 40},
    {"keyword": "الزعيم",                 "status": "target", "score": 35},
    {"keyword": "افريكانز",               "status": "target", "score": 40},
    {"keyword": "افريكان",                "status": "target", "score": 40},
    {"keyword": "كايرو ثرى",              "status": "target", "score": 40},
    {"keyword": "كايرو تري",              "status": "target", "score": 40},
    {"keyword": "يعمل بعلف المجد",        "status": "target", "score": 40},
    {"keyword": "يعمل بعلف الايمان",      "status": "target", "score": 40},
    {"keyword": "يعمل مع هايدا",          "status": "target", "score": 40},
    {"keyword": "يعمل مع bt",             "status": "target", "score": 40},
    {"keyword": "شغال مع bt",             "status": "target", "score": 40},
    {"keyword": "موزع معتمد لعلف",       "status": "target", "score": 40},
    {"keyword": "وكيل علف نماء",          "status": "target", "score": 40},
    {"keyword": "وكيل علف فيد مكس",      "status": "target", "score": 40},
    {"keyword": "تابع لمندوب شركة",      "status": "target", "score": 35},
    {"keyword": "يتعامل مع الشروق",      "status": "target", "score": 40},
    {"keyword": "يتعامل مع شركات",       "status": "target", "score": 35},
    {"keyword": "التي يعمل معها",         "status": "target", "score": 30},
    {"keyword": "بيوكل مزارع نيوهوب",    "status": "target", "score": 40},
    {"keyword": "سمسار دواجن",            "status": "target", "score": 30},
    {"keyword": "موزع كتاكيت",            "status": "target", "score": 30},
    {"keyword": "لاقرار",             "status": "target",       "score": 40},

    # ── NO MEETING (العميل غير متواجد — لا تغيّر موقف العميل) ─────
    {"keyword": "غير موجود",       "status": "no_meeting", "score": 100},
    {"keyword": "لم يكن متواجد",   "status": "no_meeting", "score": 100},
    {"keyword": "مسافر",           "status": "no_meeting", "score": 100},
    {"keyword": "العميل غائب",     "status": "no_meeting", "score": 100},
    {"keyword": "لم تتم المقابلة", "status": "no_meeting", "score": 100},
    {"keyword": "لم تتم مقابلته",  "status": "no_meeting", "score": 100},

    # ── NEW CUSTOMER  (+80) ───────────────────────────────────────
    {"keyword": "أول زيارة",           "status": "new",          "score": 80},
    {"keyword": "عميل جديد",           "status": "new",          "score": 80},
    {"keyword": "بدأ العمل",           "status": "new",          "score": 80},
    {"keyword": "بداية العمل في الوادي",           "status": "new",          "score": 80},

    # ── FORMER CUSTOMER  (+20) ────────────────────────────────────
    {"keyword": "كان يعمل معنا",       "status": "former",       "score": 20},
    {"keyword": "توقف",                "status": "former",       "score": 20},
    {"keyword": "سابق",                "status": "former",       "score": 20},
    {"keyword": "انقطع",               "status": "former",       "score": 20},
    {"keyword": "لا يطلب حاليا",       "status": "former",       "score": 20},
    {"keyword": "كان يسحب",               "status": "former",       "score": 20},
    {"keyword": "موقف شغل",               "status": "former",       "score": 20},
    {"keyword": "مبطل",               "status": "former",       "score": 20},
    {"keyword": "ارجاعه للعمل",               "status": "former",       "score": 20},
    {"keyword": "عوده للوادى",               "status": "former",       "score": 20},
    {"keyword": "كان يعمل بالوادى",               "status": "former",       "score": 20},
    {"keyword": "كان شغال مع الوادي",               "status": "former",       "score": 20},
    {"keyword": "كان بيوكل الوادي",               "status": "former",       "score": 20},
    {"keyword": "كان من عشاق الوادى",               "status": "former",       "score": 20},
    {"keyword":"كان يتعامل معنا","status":"former","score":20},
    {"keyword":"كان عميل","status":"former","score":20},
    {"keyword":"توقف عن السحب","status":"former","score":20},
    {"keyword":"انقطع عن التعامل","status":"former","score":20},
    {"keyword":"تم فقد العميل","status":"former","score":20},
    {"keyword":"كان يسحب الوادي","status":"former","score":20},
    {"keyword": "اغلق المزرعه نهائى",     "status": "former", "score": 40},
    {"keyword": "أغلق المزرعة",           "status": "former", "score": 40},
    {"keyword": "موقفين حاليا",           "status": "former", "score": 30},
    {"keyword": "وقفوا حاليا",            "status": "former", "score": 30},
    {"keyword": "توقف عن الشغل",          "status": "former", "score": 30},
    {"keyword": "عميل سابق للوادى",       "status": "former", "score": 60},
    {"keyword": "عميل ساابق للوادى",      "status": "former", "score": 60},
    {"keyword": "كان بيشتغل مع الوادي",   "status": "former", "score": 60},
    {"keyword": "كان من عملاء الوادي",    "status": "former", "score": 60},
    {"keyword": "تم فقد العميل",           "status": "former", "score": 50},
    # ── NOT INTERESTED  (-100) ────────────────────────────────────
    {"keyword": "رفض",                 "status": "not_interested","score": -100},
    {"keyword": "غير مهتم",            "status": "not_interested","score": -100},
    {"keyword": "مكتفي",               "status": "not_interested","score": -100},
    {"keyword": "لا يرغب",             "status": "not_interested","score": -100},
    {"keyword": "غير مقتنع",           "status": "not_interested","score": -100},
    {"keyword": "أغلق الموضوع",        "status": "not_interested","score": -100},
    {"keyword": "يتعامل مع علف دش من مدشة تابع له",    "status": "not_interested","score": -100},
    {"keyword": "يريد أجل",        "status": "not_interested","score": -100},
    {"keyword": "ليس لديه نية",                 "status": "not_interested","score": -100},
    {"keyword": "ليس لديه رغبة",                 "status": "not_interested","score": -100},
    {"keyword": "غير منفتح على إدخال منتج جديد",                 "status": "not_interested","score": -100},
    {"keyword": "المقابلة بدون جدوى",                 "status": "not_interested","score": -100},
    {"keyword": "أغلق الموضوع",                 "status": "not_interested","score": -100},
    {"keyword": "عاوز أجل",               "status": "not_interested","score": -100},
    {"keyword": "رافض",                 "status": "not_interested","score": -100},
    {"keyword": "قفل نهائيا",                 "status": "not_interested","score": -100},
    {"keyword": "لا يريد",                 "status": "not_interested","score": -100},
    {"keyword": "لا يريد التعامل كاش",                 "status": "not_interested","score": -100},
    {"keyword": "لا يريد العمل كاش",                 "status": "not_interested","score": -100},
    {"keyword": "لا يستطيع العمل كاش",                 "status": "not_interested","score": -100},
    {"keyword": "لا يستطيع ادخال",                 "status": "not_interested","score": -100},
    {"keyword": "التاجر غير منفتح",                 "status": "not_interested","score": -100},
    {"keyword":"علف خاص","status":"not_interested","score":-100},
    {"keyword":"يصنع علفه بنفسه","status":"not_interested","score":-100},
    {"keyword":"مدشه خاصه","status":"not_interested","score":-100},
    {"keyword":"يصنع الخلطه بنفسه","status":"not_interested","score":-100},
    {"keyword":"يعتمد على خلطته","status":"not_interested","score":-100},
    {"keyword":"رفض نهائيا","status":"not_interested","score":-100},
    {"keyword":"غير مقتنع بالسعر","status":"not_interested","score":-100},
    {"keyword":"لا يفكر في التغيير","status":"not_interested","score":-100},
    {"keyword":"متمسك بالمورد الحالي","status":"not_interested","score":-100},
    {"keyword":"لا توجد فرصه حاليا","status":"not_interested","score":-100},
    {"keyword":"لن يجرب","status":"not_interested","score":-100},
    {"keyword": "رفض نهائي",              "status": "not_interested", "score": -100},
    {"keyword": "اعترض نهائي",            "status": "not_interested", "score": -100},
    {"keyword": "لا يبدي نية",            "status": "not_interested", "score": -80},
    {"keyword": "لا يبدي نيه",            "status": "not_interested", "score": -80},
    {"keyword": "ليس لديه لإدخال منتج جديد", "status": "not_interested", "score": -80},
    {"keyword": "ليس للديه نية",          "status": "not_interested", "score": -80},
    {"keyword": "لا ينوي إدخال",          "status": "not_interested", "score": -80},
    {"keyword": "لا ينوي ادخال",          "status": "not_interested", "score": -80},
    {"keyword": "لا يريد إدخال",          "status": "not_interested", "score": -80},
    {"keyword": "لا يفكر في إدخال",       "status": "not_interested", "score": -80},
    {"keyword": "لن يجرب",               "status": "not_interested", "score": -100},
    {"keyword": "قافل ع المصانع",         "status": "not_interested", "score": -80},
    {"keyword": "لا يستطيع البدء مع اى مصنع", "status": "not_interested", "score": -80},
    {"keyword": "يعمل بمنتج واحد فقط ولا ينوي", "status": "not_interested", "score": -80},
    {"keyword": "متمسك بالمورد",          "status": "not_interested", "score": -80},
    {"keyword": "ملتزم بكميات",           "status": "not_interested", "score": -70},
    {"keyword": "التزامه بكميات",         "status": "not_interested", "score": -70},
    {"keyword": "مستقر مع",              "status": "not_interested", "score": -60},
    {"keyword": "لا توجد فرصة حاليا",    "status": "not_interested", "score": -60},
    {"keyword": "لا توجد فرصه حاليا",    "status": "not_interested", "score": -60},
 
    # علف خاص / مدشة داخلية
    {"keyword": "لديهم علفهم الخاص",     "status": "not_interested", "score": -100},
    {"keyword": "لها علفها الخاص",       "status": "not_interested", "score": -100},
    {"keyword": "له علفه الخاص",         "status": "not_interested", "score": -100},
    {"keyword": "علفهم الخاص",           "status": "not_interested", "score": -100},
    {"keyword": "علفها الخاص",           "status": "not_interested", "score": -100},
    {"keyword": "علفه الخاص",            "status": "not_interested", "score": -100},
    {"keyword": "مدشة داخل مزرعة",       "status": "not_interested", "score": -100},
    {"keyword": "مدشة داخل",             "status": "not_interested", "score": -100},
    {"keyword": "يصنع علفه",             "status": "not_interested", "score": -100},
    {"keyword": "يصنع الخلطه",           "status": "not_interested", "score": -100},
    {"keyword": "يصنع خلطته",            "status": "not_interested", "score": -100},
    {"keyword": "يعتمد على خلطته",       "status": "not_interested", "score": -100},
    {"keyword": "خلطته الخاصة",          "status": "not_interested", "score": -100},
]

# Status display labels
STATUS_DISPLAY = {
    "current":       "Current Customer",
    "potential":     "Potential Customer",
    "target":        "Target Customer",
    "new":           "New Customer",
    "former":        "Former Customer",
    "not_interested":"Not Interested",
    "no_meeting":    "No Meeting",
    "unclassified":  "Unclassified",
}

# Priority order for tie-breaking (highest priority first)
STATUS_PRIORITY = ["current", "potential", "new", "target", "former", "not_interested", "no_meeting", "unclassified"]

# Visit statuses that don't represent a real customer position
NON_STATUS = {"No Meeting", "Unclassified"}


def _prepare_rules(rules: list[dict]) -> list[dict]:
    """
    Normalize keywords and remove duplicates.

    - Scores are stored as positive magnitudes: the winner is always the
      status with the highest total, so 'not_interested' competes fairly
      instead of always losing with a negative score.
    - If the same normalized keyword appears twice with the same status,
      only the highest score is kept (no double counting).
    - If it appears under two different statuses (e.g. "أول زيارة" as both
      new and target), the status earlier in STATUS_PRIORITY wins.
    """
    best: dict[str, dict] = {}
    for r in rules:
        norm = normalize_arabic(r["keyword"])
        if not norm:
            continue
        cand = {"keyword": r["keyword"], "status": r["status"],
                "score": abs(r["score"]), "_norm": norm}
        cur = best.get(norm)
        if cur is None:
            best[norm] = cand
        elif cand["status"] == cur["status"]:
            if cand["score"] > cur["score"]:
                best[norm] = cand
        elif STATUS_PRIORITY.index(cand["status"]) < STATUS_PRIORITY.index(cur["status"]):
            best[norm] = cand
    return list(best.values())


# Base rules are fixed in code; custom rules (from the UI) are merged on top.
_BASE_RULES = _prepare_rules(KEYWORD_RULES)
ACTIVE_RULES: list[dict] = _BASE_RULES


def set_custom_rules(custom_rules: list[dict]):
    """Merge user-defined rules (from Settings/Rules tab) over the base rules."""
    global ACTIVE_RULES
    custom_rules = custom_rules or []
    ACTIVE_RULES = _prepare_rules(KEYWORD_RULES + list(custom_rules))


# ═══════════════════════════════════════════════════════════════════
# SINGLE-NOTE CLASSIFIER
# ═══════════════════════════════════════════════════════════════════

def classify_note(note: str, is_first_appearance: bool = False) -> dict:
    """
    Classify a single visit note using keyword scoring.

    Returns:
        {
            "suggested_status": str,   # internal key
            "display_status":   str,   # human-readable label
            "confidence":       float, # 0–100
            "score":            int,   # raw total score
            "matched_keywords": list[str],
            "reason":           str,
        }
    """
    norm_note = normalize_arabic(safe_str(note))

    # Find each rule's first occurrence with its position, so a keyword that
    # is swallowed by a longer matched keyword can be suppressed —
    # e.g. "مهتم" inside "غير مهتم" or "يرغب" inside "لا يرغب".
    hits: list[tuple[int, int, dict]] = []
    for rule in ACTIVE_RULES:
        pos = norm_note.find(rule["_norm"])
        if pos != -1:
            hits.append((pos, pos + len(rule["_norm"]), rule))

    kept_rules: list[dict] = []
    for i, (s1, e1, r1) in enumerate(hits):
        swallowed = any(
            s2 <= s1 and e1 <= e2 and (e2 - s2) > (e1 - s1)
            for j, (s2, e2, _r2) in enumerate(hits) if j != i
        )
        if not swallowed:
            kept_rules.append(r1)

    # Accumulate scores per status
    score_map: dict[str, int] = {}
    matched: list[str] = []
    for rule in kept_rules:
        status = rule["status"]
        score_map[status] = score_map.get(status, 0) + rule["score"]
        matched.append(rule["keyword"])

    # First-appearance bonus for "new"
    if is_first_appearance:
        score_map["new"] = score_map.get("new", 0) + 80
        if "أول زيارة" not in matched:
            matched.append("(first appearance in database)")

    # Determine winner
    if not score_map:
        suggested = "unclassified"
        total_score = 0
    else:
        # Sort by score descending, then by priority for ties
        sorted_statuses = sorted(
            score_map.keys(),
            key=lambda s: (-score_map[s], STATUS_PRIORITY.index(s) if s in STATUS_PRIORITY else 99),
        )
        suggested = sorted_statuses[0]
        total_score = score_map[suggested]

    # Confidence: winner's score capped at 100, discounted by how strongly
    # a competing status also matched (mixed signals → lower confidence).
    if total_score <= 0:
        confidence = 0.0
    else:
        base = float(min(100, total_score))
        if len(sorted_statuses) > 1:
            runner_up = score_map[sorted_statuses[1]]
            if runner_up > 0:
                base = base * total_score / (total_score + runner_up)
        confidence = min(99.0, round(base, 1))

    # Build reason string
    if matched:
        kw_list = "، ".join(matched)
        reason = f"تطابق الكلمات المفتاحية: {kw_list}"
    elif is_first_appearance:
        reason = "أول ظهور للعميل في قاعدة البيانات"
    else:
        reason = "لا توجد كلمات مفتاحية — غير مصنف"

    return {
        "suggested_status": suggested,
        "display_status":   STATUS_DISPLAY.get(suggested, suggested),
        "confidence":       confidence,
        "score":            total_score,
        "matched_keywords": matched,
        "reason":           reason,
    }


# ═══════════════════════════════════════════════════════════════════
# BATCH CLASSIFIER  (full DataFrame)
# ═══════════════════════════════════════════════════════════════════

def classify_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify every row in the DataFrame.

    Adds columns:
        Suggested Status, Display Status, Confidence Score,
        Raw Score, Matched Keywords, Classification Reason

    Also tracks customer journey (first appearance rule).
    Optimized for 50,000+ rows.
    """
    df = df.copy()
    df = df.sort_values("Visit Date", ascending=True).reset_index(drop=True)

    # Track which customer names have been seen (for first-appearance rule)
    seen_customers: set[str] = set()

    suggested_statuses = []
    display_statuses   = []
    confidences        = []
    raw_scores         = []
    matched_keywords   = []
    reasons            = []

    notes_col    = df["Visit Notes"].tolist()    if "Visit Notes"    in df.columns else [""] * len(df)
    customer_col = df["Customer Name"].tolist()  if "Customer Name"  in df.columns else [""] * len(df)

    new_hint_norms = [normalize_arabic(kw) for kw in ["أول زيارة", "تعارف", "عميل جديد"]]

    for i in range(len(df)):
        note     = safe_str(notes_col[i])
        customer = safe_str(customer_col[i]).strip()

        norm_note = normalize_arabic(note)
        has_new_keyword = any(kw in norm_note for kw in new_hint_norms)
        is_first = bool(customer) and customer not in seen_customers
        if customer:
            seen_customers.add(customer)
        result = classify_note(note, is_first_appearance=is_first and has_new_keyword)

        suggested_statuses.append(result["suggested_status"])
        display_statuses.append(result["display_status"])
        confidences.append(result["confidence"])
        raw_scores.append(result["score"])
        matched_keywords.append(", ".join(result["matched_keywords"]))
        reasons.append(result["reason"])

    df["Suggested Status"]      = suggested_statuses
    df["Display Status"]        = display_statuses
    df["Confidence Score"]      = confidences
    df["Raw Score"]             = raw_scores
    df["Matched Keywords"]      = matched_keywords
    df["Classification Reason"] = reasons

    return df


# ═══════════════════════════════════════════════════════════════════
# CUSTOMER JOURNEY TRACKER
# ═══════════════════════════════════════════════════════════════════

def build_customer_journey(classified_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each unique customer, build a journey summary:
        Customer Name, First Visit Date, Last Visit Date,
        Visit Count, Days Since Last Visit,
        Status History (list), Latest Status, Latest Confidence
    """
    if classified_df.empty:
        return pd.DataFrame()

    today = pd.Timestamp(datetime.today().date())

    df = classified_df.copy()
    df["Visit Date"] = pd.to_datetime(df["Visit Date"], errors="coerce")
    df = df.sort_values("Visit Date", kind="stable")
    if "Display Status" not in df.columns:
        df["Display Status"] = "Unclassified"
    df["Display Status"] = df["Display Status"].fillna("Unclassified").astype(str)

    grp = df.groupby("Customer Name", sort=False)

    # ── per-customer aggregates ──
    out = pd.DataFrame({
        "First Visit Date": grp["Visit Date"].min(),
        "Last Visit Date":  grp["Visit Date"].max(),
        "Visit Count":      grp.size(),
    })

    # ── readable status history: "[date] Status → [date] Status" ──
    hist_line = ("[" + df["Visit Date"].dt.strftime("%Y-%m-%d").fillna("?") + "] "
                 + df["Display Status"])
    out["Status History"] = df.assign(_h=hist_line).groupby("Customer Name", sort=False)["_h"].agg(" → ".join)

    # ── the row that decides the customer's standing ──
    # last visit carrying a REAL status; customers with none fall back to their
    # last visit of any kind (No Meeting / Unclassified must not overwrite it)
    last_any  = grp.tail(1)
    real      = df[~df["Display Status"].isin(NON_STATUS)]
    last_real = real.groupby("Customer Name", sort=False).tail(1)
    fallback  = last_any[~last_any["Customer Name"].isin(last_real["Customer Name"])]
    decisive  = pd.concat([last_real, fallback]).set_index("Customer Name")

    out["Latest Status"] = decisive["Display Status"].str.strip()
    out["Latest Confidence"] = (decisive["Confidence Score"]
                                if "Confidence Score" in decisive.columns else 0.0)

    # ── attributes taken from the customer's most recent visit ──
    latest = last_any.set_index("Customer Name")
    for col in ["Governorate", "District", "Sales Rep Name"]:
        out[col] = (latest[col].fillna("").astype(str).str.strip()
                    if col in latest.columns else "")

    out["Days Since Last Visit"] = (today - out["Last Visit Date"]).dt.days

    out = out.reset_index().rename(columns={"index": "Customer Name"})
    return out[["Customer Name", "First Visit Date", "Last Visit Date", "Visit Count",
                "Days Since Last Visit", "Latest Status", "Latest Confidence",
                "Status History", "Governorate", "District", "Sales Rep Name"]]


# ═══════════════════════════════════════════════════════════════════
# NOT-VISITED SEGMENTS
# ═══════════════════════════════════════════════════════════════════

def customers_not_visited(journey_df: pd.DataFrame, days: int) -> pd.DataFrame:
    """Return customers whose last visit was more than `days` days ago."""
    if journey_df.empty or "Days Since Last Visit" not in journey_df.columns:
        return pd.DataFrame()
    mask = journey_df["Days Since Last Visit"].fillna(9999) >= days
    return journey_df[mask].copy()


# ═══════════════════════════════════════════════════════════════════
# CONFIGURABLE KEYWORD EDITOR SUPPORT
# ═══════════════════════════════════════════════════════════════════

def get_rules_dataframe() -> pd.DataFrame:
    """Return the active (deduplicated base + custom) rules for display."""
    base_norms = {r["_norm"] for r in _BASE_RULES}
    rows = [
        {
            "Keyword":   r["keyword"],
            "Status":    STATUS_DISPLAY.get(r["status"], r["status"]),
            "Score":     r["score"],
            "Source":    "أساسي" if r["_norm"] in base_norms else "مخصص",
        }
        for r in ACTIVE_RULES
    ]
    return pd.DataFrame(rows)


def final_status_per_customer(classified_df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per customer = his last visit that carries a REAL status.
    Customers whose visits are all No Meeting / Unclassified fall back
    to their last visit row.
    """
    if classified_df.empty or "Display Status" not in classified_df.columns:
        return classified_df.copy()
    df = classified_df.sort_values("Visit Date", ascending=True)
    real = df[~df["Display Status"].isin(NON_STATUS)]
    only_non = df[~df["Customer Name"].isin(real["Customer Name"])]
    combined = pd.concat([real, only_non], ignore_index=True).sort_values("Visit Date")
    return combined.groupby("Customer Name", as_index=False).tail(1).reset_index(drop=True)
