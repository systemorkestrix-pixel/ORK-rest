import os
import re
from pathlib import Path
from datetime import datetime

root = Path(".")
labels_path = Path("docs/architecture/_labels_ar.json")


def load_labels(path: Path) -> dict[str, str]:
    labels: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line in {"{", "}"}:
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().strip('"')
        value = value.strip().strip(",").strip('"')
        labels[key] = value
    return labels


labels = load_labels(labels_path)

excluded_dirnames = {
    ".git",
    "node_modules",
    "dist",
    ".wheelhouse",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    ".idea",
}


def is_excluded(path: Path) -> bool:
    for part in path.parts:
        if part in excluded_dirnames:
            return True
    return False


def humanize_name(name: str) -> str:
    name = name.replace("_", " ")
    name = name.replace("-", " ")
    return name.strip()


VERB_MAP = {
    "create": "إنشاء",
    "update": "تحديث",
    "delete": "حذف",
    "list": "عرض قائمة",
    "get": "جلب",
    "approve": "اعتماد",
    "reject": "رفض",
    "archive": "أرشفة",
    "restore": "استعادة",
    "refresh": "تجديد",
    "revoke": "إلغاء",
    "settle": "تسوية",
    "close": "إغلاق",
    "start": "بدء",
    "mark": "تعيين",
    "notify": "إشعار",
    "assign": "تعيين",
    "complete": "إكمال",
    "fail": "فشل",
    "upload": "رفع",
    "collect": "تحصيل",
    "refund": "استرجاع",
    "run": "تشغيل",
}


def describe_path(path: Path) -> dict[str, str]:
    rel = path.as_posix()
    info = {
        "what": "",
        "does": "",
        "how": "",
        "flow": "",
        "goal": "",
        "status": labels.get("status_closed", "مغلق"),
    }

    if path.is_dir():
        info["what"] = "مجلد"
        info["does"] = f"تجميع وحدات {humanize_name(path.name)}"
        info["how"] = "يجمع ملفات ضمن نفس المجال/الطبقة"
        info["flow"] = "من/إلى: تنظيم داخلي"
        info["goal"] = "تنظيم البنية"
        return info

    info["what"] = f"ملف {path.suffix or 'بدون امتداد'}"
    name = path.stem

    if rel.startswith("backend/application") and "/use_cases/" in rel:
        parts = name.split("_")
        verb = VERB_MAP.get(parts[0], "تنفيذ")
        subject = humanize_name("_".join(parts[1:])) or humanize_name(name)
        info["does"] = f"Use Case: {verb} {subject}"
        info["how"] = "ينفذ حالة استخدام ويستدعي Repository داخل transaction_scope"
        info["flow"] = "من/إلى: Router -> Use Case -> Repository -> DB"
        info["goal"] = "عزل منطق الأعمال"
    elif rel.startswith("backend/application") and "/event_handlers/" in rel:
        info["does"] = "Event Handler: معالجة حدث وربط Side Effects"
        info["how"] = "يُستدعى عبر Event Bus ويطبق منطق idempotent"
        info["flow"] = "من/إلى: Event Bus -> Handler -> DB/Services"
        info["goal"] = "تشغيل ردود الفعل على الأحداث"
    elif rel.startswith("backend/infrastructure/repositories"):
        info["does"] = "Repository: عزل الوصول لقاعدة البيانات"
        info["how"] = "يوفر عمليات CRUD ويستدعي services أو ORM"
        info["flow"] = "من/إلى: Use Case -> Repository -> DB"
        info["goal"] = "فصل المنطق عن التخزين"
    elif rel.startswith("backend/app/routers"):
        info["does"] = "Router: تعريف مسارات API"
        info["how"] = "يستقبل الطلب ويستدعي Use Case عبر Factory"
        info["flow"] = "من/إلى: HTTP -> Router -> Use Case"
        info["goal"] = "ثبات العقود"
    elif rel == "backend/main.py":
        info["does"] = "نقطة تشغيل الـ API"
        info["how"] = "تهيئة FastAPI + middleware + routers + event bus"
        info["flow"] = "من/إلى: Boot -> Routers"
        info["goal"] = "تشغيل النظام"
    elif rel.startswith("backend/core/events"):
        info["does"] = "منظومة الأحداث الداخلية"
        info["how"] = "EventBus publish/subscribe"
        info["flow"] = "من/إلى: Use Cases -> Handlers"
        info["goal"] = "فصل المحركات"
    elif rel.startswith("backend/app/models") or rel.endswith("models.py"):
        info["does"] = "نماذج ORM"
        info["how"] = "تعريف الجداول والعلاقات"
        info["flow"] = "من/إلى: Repository <-> DB"
        info["goal"] = "تمثيل البيانات"
    elif rel.startswith("backend/app/services"):
        info["does"] = "Legacy Services"
        info["how"] = "منطق أعمال قديم"
        info["flow"] = "من/إلى: Repositories/Use Cases"
        info["goal"] = "تشغيل الوظائف الحالية"
    elif rel.startswith("backend/app/schemas"):
        info["does"] = "Pydantic Schemas"
        info["how"] = "تعريف عقود إدخال/إخراج"
        info["flow"] = "من/إلى: Router <-> Client"
        info["goal"] = "ثبات الاستجابات"
    elif rel.startswith("src/"):
        info["does"] = "واجهة أمامية"
        info["how"] = "مكونات React/Vite"
        info["flow"] = "من/إلى: UI -> API"
        info["goal"] = "تجربة المستخدم"
    elif rel.startswith("docs/"):
        info["does"] = "توثيق"
        info["how"] = "ملفات مرجعية وخطط"
        info["flow"] = "من/إلى: فريق التطوير"
        info["goal"] = "حفظ المعرفة"
    elif rel.startswith("tests/"):
        info["does"] = "اختبارات"
        info["how"] = "تنفيذ فحوصات عقود وسلوك"
        info["flow"] = "من/إلى: CI/QA"
        info["goal"] = "منع الانكسار"
    elif path.suffix in {".ts", ".tsx", ".js"}:
        info["does"] = "ملف برمجي للواجهة"
        info["how"] = "تعريف منطق/مكونات"
        info["flow"] = "من/إلى: UI"
        info["goal"] = "وظائف الواجهة"
    elif path.suffix in {".json", ".yaml", ".yml", ".toml"}:
        info["does"] = "ملف إعدادات"
        info["how"] = "يُحمّل وقت التشغيل"
        info["flow"] = "من/إلى: التطبيق"
        info["goal"] = "التهيئة"
    else:
        info["does"] = f"ملف ضمن {humanize_name(path.parent.name)}"
        info["how"] = "يُستخدم حسب سياق المجلد"
        info["flow"] = "من/إلى: داخلي"
        info["goal"] = "دعم البنية"

    try:
        if path.suffix in {".py", ".md", ".ts", ".tsx", ".js"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"\bTODO\b|\bFIXME\b|NotImplemented|pass\b", text):
                info["status"] = labels.get("status_open", "غير مغلق")
    except Exception:
        pass

    if "/_templates/" in rel or rel.startswith("backend/presentation/_templates"):
        info["status"] = labels.get("status_closed", "مغلق")
        info["does"] = info["does"] + " (قالب)"
        info["goal"] = "قالب للتوليد (مستثنى من الإغلاق التشغيلي)"

    return info


paths: list[Path] = []
excluded: list[Path] = []
for base, dirs, files in os.walk(root):
    base_path = Path(base)
    if is_excluded(base_path):
        if base_path == root:
            continue
        dirs[:] = []
        excluded.append(base_path)
        continue
    dirs[:] = [d for d in dirs if not is_excluded(base_path / d)]
    if base_path != root:
        paths.append(base_path)
    for f in files:
        fpath = base_path / f
        if is_excluded(fpath):
            excluded.append(fpath)
            continue
        paths.append(fpath)

paths_sorted = sorted(paths, key=lambda p: (str(p).count(os.sep), p.as_posix()))

status_map: dict[Path, str] = {}
for p in paths_sorted:
    if p.is_file():
        status_map[p] = describe_path(p)["status"]

for p in reversed(paths_sorted):
    if p.is_dir():
        children = [c for c in status_map if c.is_relative_to(p)]
        status_map[p] = (
            labels.get("status_open", "غير مغلق")
            if any(status_map.get(c) == labels.get("status_open", "غير مغلق") for c in children)
            else labels.get("status_closed", "مغلق")
        )

out_path = Path("docs/architecture/22_architecture_tree_full.md")
lines: list[str] = []
lines.append(f"# {labels.get('title', '')}")
lines.append("")
lines.append(f"- {labels.get('date_label', 'التاريخ')}: {datetime.now().date().isoformat()}")
lines.append(f"- {labels.get('scope_label', 'النطاق')}: {labels.get('scope_value', '')}")
lines.append("")

if excluded:
    lines.append(f"## {labels.get('excluded_header', '')}")
    lines.append("")
    for item in sorted(set(excluded)):
        rel = item.as_posix()
        lines.append(f"### {rel}")
        lines.append(f"- {labels.get('label_what', 'ما هذا؟')} {labels.get('excluded_what', '')}")
        lines.append(f"- {labels.get('label_does', 'ما الذي يفعل؟')} {labels.get('excluded_does', '')}")
        lines.append(f"- {labels.get('label_how', 'كيف يعمل؟')} {labels.get('excluded_how', '')}")
        lines.append(f"- {labels.get('label_flow', 'من أين / إلى أين؟')} {labels.get('excluded_flow', '')}")
        lines.append(f"- {labels.get('label_goal', 'ما هدفه؟')} {labels.get('excluded_goal', '')}")
        lines.append(f"- {labels.get('label_status', 'الحالة')}: {labels.get('status_open', 'غير مغلق')}")
        lines.append("")

lines.append(f"## {labels.get('items_header', '')}")
lines.append("")

for p in paths_sorted:
    rel = p.as_posix()
    info = describe_path(p)
    if p.is_dir():
        info["status"] = status_map.get(p, info["status"])
    lines.append(f"### {rel}")
    lines.append(f"- {labels.get('label_what', 'ما هذا؟')} {info['what']}")
    lines.append(f"- {labels.get('label_does', 'ما الذي يفعل؟')} {info['does']}")
    lines.append(f"- {labels.get('label_how', 'كيف يعمل؟')} {info['how']}")
    lines.append(f"- {labels.get('label_flow', 'من أين / إلى أين؟')} {info['flow']}")
    lines.append(f"- {labels.get('label_goal', 'ما هدفه؟')} {info['goal']}")
    lines.append(f"- {labels.get('label_status', 'الحالة')}: {info['status']}")
    lines.append("")

out_path.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {out_path}")
